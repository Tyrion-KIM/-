# 钉钉推送工具集

每日/每周自动推送三份简报到你的钉钉群：早报待办、晚报行程、周一团队任务周报。

> **重要**：每个人的 MCP 网关和机器人都是独立配置的，消息只推送到你自己的群。需要为每个使用的人单独部署一份。

## 功能概览

| 模块 | 脚本 | 推送时间 | 内容 |
|------|------|----------|------|
| 早报 | `dingtalk_daily_digest.py` | 工作日 10:07 | 今日到期 + 近7天逾期的未完成待办 |
| 晚报 | `dingtalk_calendar_briefing.py` | 工作日 18:04 | 明天日历里的所有行程 |
| 周报 | `dingtalk_task_weekly.py` | 周一 10:30 | AI表格未完成任务，按负责人分组+截止天数 |

---

## 首次配置（15分钟搞定）

### 第一步：获取钉钉凭证

需要准备以下 3 个东西：

**1. MCP 网关（3个）**

在钉钉开放平台 → 你的应用 → 应用功能 → MCP网关，分别开通并获取：

| 网关 | 用途 |
|------|------|
| 待办 MCP | 早报数据来源 |
| 日历 MCP | 晚报数据来源 |
| AI表格 MCP | 周报数据来源 |

**2. 自定义机器人 Webhook + 加签密钥**

在你想收消息的钉钉群里 → 群设置 → 智能群助手 → 添加机器人 → 自定义 → 选择"加签"模式 → 复制 Webhook 地址和密钥（SEC 开头）

**3. AI 表格 ID（仅周报需要）**

打开你的团队任务表，复制 URL：
`https://ai.dingtalk.com/aiHome#/data/app/<这里填 base_id>/table/<这里填 table_id>`

### 第二步：填写配置文件

```bash
cp config.example.json config.json
cp user_map.example.json user_map.json
```

编辑 `config.json`，替换所有尖括号内容：

```json
{
  "mcp_url": "https://mcp-gw.dingtalk.com/server/<你的待办MCP网关>?key=<key>",
  "calendar_mcp_url": "https://mcp-gw.dingtalk.com/server/<你的日历MCP网关>?key=<key>",
  "table_mcp_url": "https://mcp-gw.dingtalk.com/server/<你的AI表格MCP网关>?key=<key>",
  "base_id": "<AI表格的base_id>",
  "table_id": "<AI表格的table_id>",
  "robot_webhook": "https://oapi.dingtalk.com/robot/send?access_token=<你的机器人token>",
  "robot_secret": "SEC<你的加签密钥>"
}
```

### 第三步：补充人员姓名

运行自动发现：

```bash
python dingtalk_task_weekly.py --build-user-map
```

然后打开 `user_map.json`，把空白的姓名填上：

```json
{
  "636649773": "张三",
  "639355430": "李四",
  ...
}
```

> **关于周报**：周报里的任务数据来自 AI 表格，需要团队共用同一个 AI 表格才能看到所有人的任务。如果只看自己的任务，用早报就够了。

---

## 使用方式

### 手动运行

```bash
# 预览（不发消息，推荐先试）
python dingtalk_daily_digest.py --dry-run
python dingtalk_calendar_briefing.py --dry-run
python dingtalk_task_weekly.py --dry-run

# 正式发送
python dingtalk_daily_digest.py
python dingtalk_calendar_briefing.py
python dingtalk_task_weekly.py
```

### 定时自动运行（推荐）

#### Windows 任务计划程序（永久生效）

打开 PowerShell，运行：

```powershell
# ===== 早报 - 工作日 10:07 =====
$action1 = New-ScheduledTaskAction -Execute "python" -Argument "dingtalk_daily_digest.py" -WorkingDirectory "C:\你的路径\dingtalk-digest"
$trigger1 = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At "10:07"
Register-ScheduledTask -TaskName "钉钉早报" -Trigger $trigger1 -Action $action1 -Description "工作日10:07发送今日待办日报"

# ===== 晚报 - 工作日 18:04 =====
$action2 = New-ScheduledTaskAction -Execute "python" -Argument "dingtalk_calendar_briefing.py" -WorkingDirectory "C:\你的路径\dingtalk-digest"
$trigger2 = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At "18:04"
Register-ScheduledTask -TaskName "钉钉晚报" -Trigger $trigger2 -Action $action2 -Description "工作日18:04发送明日行程简报"

# ===== 周报 - 周一 10:30 =====
$action3 = New-ScheduledTaskAction -Execute "python" -Argument "dingtalk_task_weekly.py" -WorkingDirectory "C:\你的路径\dingtalk-digest"
$trigger3 = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At "10:30"
Register-ScheduledTask -TaskName "钉钉周报" -Trigger $trigger3 -Action $action3 -Description "周一10:30发送团队任务周报"
```

> 把 `C:\你的路径\` 替换为你解压本工具的实际路径。

#### Claude Code 定时（会话内，7天过期）

每次新会话运行一次：

```
CronCreate("7 10 * * 1-5")  # 工作日 10:07 发早报
CronCreate("4 18 * * 1-5")  # 工作日 18:04 发晚报
CronCreate("30 10 * * 1")   # 周一 10:30 发周报
```

---

## 文件结构

```
dingtalk-digest/
├── README.md                    # 本文件
├── .gitignore                   # 防止提交 config.json / user_map.json
├── config.example.json          # 配置模板（复制为 config.json 后填写）
├── user_map.example.json        # 人员映射模板
├── dingtalk_common.py           # 共享：MCP客户端 + 机器人加签发送
├── dingtalk_daily_digest.py     # 早报：今日到期 + 近7天逾期待办
├── dingtalk_calendar_briefing.py # 晚报：明日日历行程
└── dingtalk_task_weekly.py       # 周报：AI表格未完成任务汇总
```

---

## 依赖说明

**无需安装任何 Python 包** —— 全部使用 Python 3 标准库，直接运行即可。

需要 Python 3.7+。

---

## 常见问题

**Q: 推送发到了别人的群**
A: 你的 `config.json` 里的 `robot_webhook` 是你自己创建的机器人的地址，每个人不同。

**Q: 拉取数据为空或报错**
A: 确认 MCP 网关已开通对应应用的权限，且应用对你的账号可见。

**Q: 周报里有人名显示为 userId**
A: 打开 `user_map.json`，找到对应的 userId，填入姓名。

**Q: 定时任务没有执行**
A: 检查 Windows 任务计划程序中该任务的上次运行结果，确保 Python 在系统 PATH 中。

**Q: 团队里每个人都用这个工具，推送会不会重复？**
A: 不会。因为每个人的 `robot_webhook` 是独立的，各自推送到自己的群。不会互相干扰。

---

## GitHub Actions 部署（可选）

将本项目部署到 GitHub Actions，摆脱本地电脑依赖。

### 第一步：创建 GitHub 私有仓库

在 GitHub 创建私有仓库（如 `dingtalk-digest`），将项目 push 上去。

> **注意**：`config.json` 已通过 `.gitignore` 排除，不会提交到 GitHub。

### 第二步：配置 Secrets

在仓库页面 → Settings → Secrets and variables → Actions，添加以下 7 个 Secret：

| Secret 名 | 来源 |
|-----------|------|
| `DINGTALK_MCP_URL` | 来自 config.json 的 `mcp_url` |
| `DINGTALK_CALENDAR_MCP_URL` | 来自 config.json 的 `calendar_mcp_url` |
| `DINGTALK_TABLE_MCP_URL` | 来自 config.json 的 `table_mcp_url` |
| `DINGTALK_BASE_ID` | 来自 config.json 的 `base_id` |
| `DINGTALK_TABLE_ID` | 来自 config.json 的 `table_id` |
| `DINGTALK_ROBOT_WEBHOOK` | 来自 config.json 的 `robot_webhook` |
| `DINGTALK_ROBOT_SECRET` | 来自 config.json 的 `robot_secret` |

### 第三步：验证

在 GitHub 仓库 → Actions 页面，手动触发任一 workflow，确认消息正常发送到钉钉群。

### 定时说明

| Workflow | 北京时间 | 触发条件 |
|----------|----------|----------|
| 钉钉早报 | 工作日 10:07 | 自动 |
| 钉钉晚报 | 工作日 18:04 | 自动 |
| 钉钉周报 | 周一 10:30 | 自动 |

也可以手动触发（workflow_dispatch）：仓库 → Actions → 选择 workflow → Run workflow。
