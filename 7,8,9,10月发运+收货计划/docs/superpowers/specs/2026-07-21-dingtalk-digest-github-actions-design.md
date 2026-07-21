# 钉钉日报 GitHub Actions 迁移设计

## 目标

将 `dingtalk-digest` 项目迁移到 GitHub Actions，摆脱本地电脑依赖，实现定时自动推送。

## 现状

```
dingtalk-digest/
├── dingtalk_common.py           # MCP 客户端 + 机器人发送
├── dingtalk_daily_digest.py     # 早报（工作日 10:07）
├── dingtalk_calendar_briefing.py # 晚报（工作日 18:04）
├── dingtalk_task_weekly.py       # 周报（周一 10:30）
├── config.json                  # 敏感配置
└── user_map.json               # 人员 ID→姓名映射
```

三个脚本均依赖 `config.json` 中的 secrets（MCP URL、机器人 Webhook、加签密钥）。

## 目标架构

```
dingtalk-digest/
├── .github/
│   └── workflows/
│       ├── dingtalk-daily-digest.yml
│       ├── dingtalk-calendar-briefing.yml
│       └── dingtalk-task-weekly.yml
├── dingtalk_common.py
├── dingtalk_daily_digest.py
├── dingtalk_calendar_briefing.py
├── dingtalk_task_weekly.py
├── config.json                  # 本地调试用，不提交
└── user_map.json               # 不含敏感信息，可提交
```

## Secrets 注入方案

修改 `dingtalk_common.py`，改为优先读环境变量，无环境变量才读 config.json：

```python
# 优先读环境变量，兼容本地 config.json
MCP_URL = os.environ.get("DINGTALK_MCP_URL") or cfg["mcp_url"]
```

**GitHub Secrets 配置（每个 workflow 都要设置）：**

| Secret 名 | 对应字段 | 用途 |
|-----------|---------|------|
| `DINGTALK_MCP_URL` | `mcp_url` | 早报 MCP |
| `DINGTALK_CALENDAR_MCP_URL` | `calendar_mcp_url` | 晚报 MCP |
| `DINGTALK_TABLE_MCP_URL` | `table_mcp_url` | 周报 MCP |
| `DINGTALK_BASE_ID` | `base_id` | AI 表格 base ID |
| `DINGTALK_TABLE_ID` | `table_id` | AI 表格 table ID |
| `DINGTALK_ROBOT_WEBHOOK` | `robot_webhook` | 机器人 Webhook |
| `DINGTALK_ROBOT_SECRET` | `robot_secret` | 机器人加签密钥 |

## Workflow 文件设计

### 共同结构

```yaml
name: <标题>
on:
  schedule:
    - cron: <UTC时间>
  workflow_dispatch:  # 手动触发
jobs:
  send:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Run script
        env:
          DINGTALK_MCP_URL: ${{ secrets.DINGTALK_MCP_URL }}
          # ... 其他 secrets
        run: python <script>.py
```

### 定时（GitHub Actions cron，UTC）

| 脚本 | 北京时间 | UTC cron |
|------|----------|----------|
| 早报 | 10:07 | `7 2 * * 1-5` |
| 晚报 | 18:04 | `4 10 * * 1-5` |
| 周报 | 10:30 (周一) | `30 2 * * 1` |

### 环境变量传递

每个 workflow 将所需的 Secrets 作为环境变量传给 Python 脚本，脚本内通过 `os.environ.get()` 读取。

## 文件变更

### 新增
- `.github/workflows/dingtalk-daily-digest.yml`
- `.github/workflows/dingtalk-calendar-briefing.yml`
- `.github/workflows/dingtalk-task-weekly.yml`

### 修改
- `dingtalk_common.py`：增加 `CONFIG_SOURCE` 逻辑，优先读环境变量
- `dingtalk_daily_digest.py`、`dingtalk_calendar_briefing.py`、`dingtalk_task_weekly.py`：透传 config 路径参数

### .gitignore 更新
确保 `config.json` 不被提交，仅本地调试用。

## 部署步骤

1. 在 GitHub 创建私有仓库（建议命名为 `dingtalk-digest`）
2. 将项目 push 到仓库（排除 `config.json`）
3. 在仓库 Settings → Secrets 中添加 7 个 Secret
4. 手动 trigger 任一 workflow 验证是否正常
5. 确认定时触发生效

## 测试

- `workflow_dispatch` 手动触发每个 workflow
- 查看 Actions 日志确认数据拉取和消息发送成功
