# 56yorky 转运状态日报 → 钉钉推送 工具设计规格

- 日期：2026-07-17
- 状态：已评审（设计已与用户逐段确认）
- 范围：单一可独立实现的工具

## 1. 背景与目标

用户拥有 56yorky TMS（运输管理系统）的合法 API 访问权限。希望每天定时把系统中
"在途"入仓单的最新转运状态汇总成报表，推送到钉钉群，便于每日跟进物流进展。

**非目标**：不做订单创建/修改、不做库存看板、不做实时告警、不接入其它系统。

## 2. 上游 API（56yorky）

来源：官方《API 对接文档》（https://tmsv2.56yorky.com/yk/API对接文档.pdf）。

- 正式环境 base：`https://api.56yorky.com`
- 鉴权：请求头 `apiKey: <密钥>`
- 全局限速：**2 秒 / 次请求**

### 2.1 主接口：轨迹推送列表

`POST /api/depot/expand/trackList/push`

- 请求体（application/json）支持分页与筛选：
  - `limit` Integer —— 每页条数
  - `offset` Integer —— 页码（从 0 起）
  - `trackNos / userNos / billNums / containerNums` String —— 可选过滤
  - `createPrefixDate / createSuffixDate` —— 创建时间窗口（yyyy-MM-dd）
  - `updatePrefixDate / updateSuffixDate` —— 状态变更时间窗口
  - `busiIdList / clientId / companyIdList` 等 —— 可选
- 返回 `data.list` 数组，每条关键字段：
  - `inputId` 预报编号
  - `userNo` 客户单号
  - `serviceName` 渠道名称
  - `productName` 产品线名称
  - `getNum` 已收箱数
  - `fbaCode` FBA 仓库编码
  - `countryText` 国家
  - `trackDesc` 轨迹描述（最新一条）
  - `trackTime` 轨迹创建时间
  - `statusTime` 状态变更时间
  - `trackStatus` 转运状态 code（0待转动 / 1转运中 / 2已送达）
  - `trackStatusText` 转运状态文本
  - `userContent` 客户名-客户id-公司名
  - `boxList[].deliveryReference` 跟踪号

### 2.2 备用接口（本次不使用，仅记录）

- `POST /api/depot/expand/updatePushStatus` —— 回写推送状态（增量推送场景才需要）
- `GET api/expand/depot/track/info` —— 按 inputId/userNo 查明细轨迹（本方案用列表接口已够）

## 3. 方案选择

已选定 **方案 3：全量拉取 + 在途过滤**。

- 每天分页拉取全部轨迹记录（不预设 pushStatus 等业务过滤）
- 在脚本内过滤掉"已完结"的单，只推在途单
- 理由：既满足"全部入仓单"的全量感，又避免每天刷一堆已签收老单

## 4. 运行流程

```
Windows 任务计划程序 (Daily 10:00)
   └─ run_daily.bat
        └─ python main.py
              ├─ 1. 加载 config.yaml
              ├─ 2. YorkyClient.fetch_all_tracks()   分页拉取（每页间隔 2s）
              ├─ 3. ReportBuilder.build()             过滤在途 + 分组 + 生成报表数据
              ├─ 4. DingTalkSender.send_action_card() 加签 + 推送
              └─ 5. 写日志 logs/YYYY-MM-DD.log
```

## 5. 模块设计

项目根：`7,8,9,10月发运+收货计划/yorky-dingtalk-report/`

| 文件 | 职责 | 对外接口 |
|---|---|---|
| `main.py` | 编排 5 步流程，入口 | `python main.py` |
| `yorky_client.py` | 56yorky API 封装：分页、2s 限速、重试 | `fetch_all_tracks() -> list[dict]` |
| `report_builder.py` | 在途过滤 + 按状态分组 + 生成 Markdown | `build(records) -> ReportData` |
| `dingtalk_sender.py` | ActionCard 拼装 + 加签 + 推送 + 重试 | `send_action_card(title, markdown) -> bool` |
| `config.py` | 加载并校验 config.yaml | `load_config(path) -> Config` |
| `config.yaml` | 真实配置（gitignore） | — |
| `config.example.yaml` | 配置模板（可提交） | — |
| `requirements.txt` | `requests`, `pyyaml` | — |
| `run_daily.bat` | Task Scheduler 调用入口 | — |
| `install_task.ps1` | 一键注册 Windows 定时任务 | — |
| `logs/` | 每日运行日志 | — |
| `tests/` | 单元测试（过滤、分组、加签） | — |

模块间只通过明确数据结构（`list[dict]`、`ReportData`）传递，互不依赖对方内部实现。

## 6. 关键规则

### 6.1 在途过滤（已与用户确认）

**排除**（视为已完结，不推）：
- `trackStatus == 2`（已送达）
- 物流状态为签收（`deliveryStatus == "C"`，若该字段出现在返回中）

**保留**：其余全部，含 待转动 / 转运中 / 问题件 / 未提取 / 已下单 / 运输中。

> 已删除（inStatus=6）单据默认不进入 trackList/push 列表，无需额外处理。

### 6.2 分页与限速

- `limit=100`，`offset` 从 0 递增
- 每次请求后 `sleep(2)`（遵守 2 秒/次）
- 当某页返回 < limit 条时停止
- 单页请求失败：重试 3 次，指数退避（2s/4s/8s）；仍失败则记 error 日志，跳过该页继续（避免一页失败拖垮整体）

### 6.3 报表分组与展示

- 按 `trackStatusText` 分组
- **问题件优先**：若某条记录含问题指示（`trackStatusText`/`trackDesc` 含"问题/异常"
  或返回中存在 `deliveryStatus=="W"`），单独归入"问题件"组并置于报表最前；
  若该批数据无可识别的问题指示，则仅按 `trackStatusText` 自然分组（不强行造组）
- 每组显示数量与表格：`客户单号 | 渠道 | 国家 | 转运状态 | 最新轨迹 | 时间`
- 轨迹描述超 40 字截断 + `…`
- 在途单 > 50 条时：只发概要（分组计数）+ 后台跳转按钮，避免钉钉消息超长截断

> 说明：trackList/push 返回字段以实际为准（文档中 trackStatus 仅明确 0/1/2）。
> 所有过滤与分组规则均为"字段存在才应用"，缺失字段不影响主流程。

### 6.4 钉钉推送

- 安全方式：**加签**（HMAC-SHA256，timestamp+secret → base64 → urlencode）
- 消息类型：`actionCard`
  - `actionCardTitle`：`📦 每日转运状态报表（YYYY-MM-DD）`
  - `actionCardText`：Markdown 正文（分组表格）
  - `btns`：`[{"title":"查看 56yorky 后台","actionURL":"https://www.56yorky.com"}]`，`btnOrientation=0`
- 推送失败重试 2 次

## 7. 错误处理与边界

| 场景 | 处理 |
|---|---|
| 拉取到 0 条在途单 | 推送一条 `✅ 今日全部已送达，无在途单` |
| 某页 API 失败 | 重试 3 次后跳过该页，日志记录，继续后续页 |
| 全部页失败 / 0 总记录 | 推送一条告警 `⚠️ 数据拉取失败，请检查` + 日志 |
| 钉钉推送失败 | 重试 2 次；仍失败写日志 + 控制台非零退出码 |
| apiKey / webhook 缺失 | 启动即校验，缺失则报错退出，不运行 |

## 8. 配置与安全

`config.yaml`（gitignore，不放仓库）：
```yaml
yorky:
  base_url: https://api.56yorky.com
  api_key: <你的 apiKey>
  page_size: 100
  page_sleep_seconds: 2

dingtalk:
  webhook: https://oapi.dingtalk.com/robot/send?access_token=xxx
  secret: <加签密钥>
  backend_url: https://www.56yorky.com

filter:
  exclude_track_status: [2]          # 2=已送达
  exclude_delivery_status: ["C"]     # C=签收
  long_tail_threshold: 50            # 超过则只发概要

logging:
  dir: logs
```

`.gitignore` 至少包含：`config.yaml`、`logs/`、`__pycache__/`、`.venv/`。

## 9. 定时任务

`install_task.ps1` 使用 `schtasks /create`：
- 触发器：每日 10:00
- 动作：运行 `run_daily.bat`（内部 `cd` 到项目目录并 `python main.py`）
- 工作目录设为项目根

前提：每天 10:00 该 Windows 电脑处于开机状态。

## 10. 测试策略

- `tests/test_report_builder.py`：在途过滤规则、分组顺序（问题件置顶）、长描述截断、超 50 条只发概要
- `tests/test_dingtalk_sign.py`：加签算法正确性（用钉钉官方示例向量校验）
- `tests/test_yorky_client.py`：用 mock 的 requests 验证分页停止条件、2 秒 sleep、重试退避
- 不对真实 API / 真实钉钉做集成测试（避免副作用）；提供 `--dry-run` 本地联调开关

## 11. 验收标准

1. `python main.py` 能成功拉取在途单并推送一条 ActionCard 到钉钉（需真实 config）
2. `python main.py --dry-run` 不发钉钉、不调真实 API，仅打印将推送的内容（用本地样本）
3. 0 条在途时推送"今日全部已送达"
4. 单元测试全部通过
5. `install_task.ps1` 注册后，`schtasks /query` 能看到该任务
