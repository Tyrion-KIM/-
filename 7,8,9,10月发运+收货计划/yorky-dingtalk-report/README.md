# 56yorky 转运状态日报 → 钉钉

每天 10:00 从 56yorky TMS 拉取全部入仓单轨迹，过滤出"在途"单（排除已送达/签收），
生成钉钉 ActionCard 报表（问题件置顶、按转运状态分组）推送到钉钉群。

## 目录结构

| 文件 | 作用 |
|---|---|
| `main.py` | 入口，编排：拉取 → 过滤 → 报表 → 推送 |
| `config.py` | 加载并校验 `config.yaml` |
| `yorky_client.py` | 56yorky API 封装（分页 / 2 秒限速 / 失败标记） |
| `report_builder.py` | 在途过滤 + 分组 + Markdown 生成 |
| `dingtalk_sender.py` | 钉钉加签 + ActionCard 推送（含重试） |
| `run_daily.bat` | Windows 任务计划程序调用入口 |
| `install_task.ps1` | 一键注册每日 10:00 定时任务 |
| `tests/` | 单元测试（20 个） |

## 配置

1. 复制配置模板：`copy config.example.yaml config.yaml`
2. 编辑 `config.yaml`，填入：
   - `yorky.api_key`：你的 56yorky apiKey（登录系统后在 api 工具里生成）
   - `dingtalk.webhook`：钉钉群机器人 Webhook 地址
   - `dingtalk.secret`：钉钉机器人"加签"密钥
3. 安装依赖：`python -m pip install -r requirements.txt`

> `config.yaml` 已在 `.gitignore` 中，不会入库。

## 钉钉机器人获取方法

钉钉群 → 群设置 → 智能群助手 → 添加机器人 → 选择"自定义" →
安全设置勾选 **加签** → 完成后复制 **Webhook** 与 **加签 secret**。

## 测试

```bash
python -m pytest tests/ -v
```

## 手动运行

```bash
# 本地预览（调用真实 API 拉取，但不推送钉钉）
python main.py --dry-run

# 正式运行（拉取 + 推送）
python main.py
```

## 注册每日定时任务（Windows）

在 PowerShell 中运行（无需管理员，注册到当前用户）：

```powershell
powershell -ExecutionPolicy Bypass -File install_task.ps1
```

查看任务：

```powershell
schtasks /Query /TN YorkyDingTalkReport /V /FO LIST
```

> 前提：每天 10:00 这台电脑处于开机状态，否则该次跳过。

## 在途过滤规则（可在 config.yaml 调整）

- 排除 `trackStatus == 2`（已送达）
- 排除 `deliveryStatus == "C"`（签收）
- 其余全部保留（待转动 / 转运中 / 问题件 / 未提取 / 已下单 / 运输中）
- 在途单超过 `long_tail_threshold`（默认 50）时，只发分组计数概要 + 后台跳转按钮

## 日志

每次运行写入 `logs/YYYY-MM-DD.log`。
