# PI 自动解析 + 金蝶云星空销售订单导入工具 — 设计文档

日期：2026-07-15
状态：已与用户确认

## 1. 背景与目标

收到客户 PI（Proforma Invoice）后，目前需要在金蝶云星空手动录入销售订单。手动录入经常出现**币种、单价、数量**三类错误。

目标：做一个自动化工具——
1. 自动解析 PI（格式多样：PDF/Excel 混杂、不同客户模板不同），提取关键字段；
2. 人工核对确认后，通过金蝶云星空 WebAPI 自动创建**销售订单**。

## 2. 已确认的关键决策

| 决策点 | 结论 |
|---|---|
| 金蝶版本 | 金蝶云星空（K3 Cloud），走标准 REST WebAPI |
| PI 格式 | 格式多样（PDF/Excel、不同客户不同模板） |
| 解析方案 | AI 大模型解析（Claude API），新客户/新格式无需改代码 |
| 导入目标单据 | 销售订单 `SAL_SaleOrder` |
| 物料编码 | PI 上自带金蝶物料编码，可直接对应 |
| 确认环节 | 人工确认后导入（网页预览 + 可编辑 + 异常标红） |
| 接口条件 | 已有 K3 Cloud API 账号 + 测试账套 |
| 触发方式 | 拖 PI 文件到 inbox 文件夹 + 双击桌面图标运行 |
| 工具形态 | 本地小网页（Flask，双击启动自动打开浏览器） |

## 3. 整体流程

```
拖 PI 文件到 inbox/ 文件夹
   ↓ 双击桌面「启动PI导入工具.cmd」
启动本地 Flask 并自动打开浏览器（127.0.0.1）
   ↓ 点【解析】
reader 读取原始文本/表格 → Claude API 提取为统一 JSON
   ↓
validator 校验（币种/单价/数量/合计/客户/物料）→ 异常标红
   ↓ 人工在网页核对（可直接修改字段）
点【导入金蝶】
   ↓
防重检查（按 PI 号）→ WebAPI Save 草稿（可选自动 Submit）
   ↓
成功：返回金蝶订单号，文件归档 done/；失败：进 failed/ 并显示金蝶错误原因
```

## 4. 模块划分

```
项目/
├─ 启动PI导入工具.cmd        # 桌面双击入口
├─ config.yaml               # 金蝶地址/账号/账套、Claude API Key、文件夹路径（账密不入代码）
├─ requirements.txt
├─ app/
│  ├─ main.py                # Flask 入口 + 路由
│  ├─ pi_parser/
│  │  ├─ reader.py           # PDF→文本+表格(pdfplumber)；Excel→表格(openpyxl)
│  │  ├─ extractor.py        # 调 Claude API，输出统一 PI JSON
│  │  └─ schema.py           # PI 字段定义（pydantic 校验）
│  ├─ validator.py           # 校验 + 标红规则
│  ├─ kingdee/
│  │  ├─ client.py           # WebAPI 封装：登录/查询/保存/提交
│  │  └─ mapping.py          # PI JSON → SAL_SaleOrder JSON 映射
│  ├─ storage.py             # SQLite：解析记录、导入日志、客户映射缓存
│  ├─ templates/  static/    # 网页 UI（列表/预览/编辑/导入/结果）
├─ inbox/                    # 拖 PI 到这里
├─ done/  failed/            # 处理后自动归档
└─ logs/
```

## 5. PI 统一字段（extractor 输出 schema）

- 头：`pi_no`（PI号）、`customer_name`、`currency`（币种）、`pi_date`、`delivery_date`（交期）、`trade_terms`（FOB等）、`payment_terms`、`remark`
- 明细 `items[]`：`material_no`（金蝶物料编码，PI自带）、`product_name`、`qty`、`unit`、`unit_price`、`amount`
- 尾：`total_amount`
- 每个字段附带 `confidence` 或缺失标记，供网页标红

## 6. 人工确认界面（防错核心）

- 明细表格化展示，以下情况**自动标红**：
  - 必填字段缺失 / AI 置信度低
  - 单价 = 0、数量 = 0
  - 明细合计 ≠ PI 总金额
  - 币种不在常用列表（USD/EUR/CNY 等）
  - 物料编码在金蝶中查不到（调金蝶查询接口核对）
- **客户映射**：PI 上是客户名称 → 网页下拉选择金蝶客户（从金蝶拉客户列表）；首次选择后写入本地映射缓存，之后同客户自动带出
- 所有字段可在网页上直接修改，修改后再导入

## 7. 金蝶导入

- 单据：`SAL_SaleOrder`（标准销售订单）
- 流程：**先 Save 保存为草稿**（金蝶里可复核），配置项可开启自动 Submit
- **防重复导入**：导入前按 PI 号查询金蝶是否已存在该订单，存在则阻止并提示
- 失败处理：网页原样显示金蝶返回错误；文件进 `failed/`；修正后可重新导入
- 关键字段映射：`FCustId`←客户编码、`FCurrencyId`←币种、`FDate`←PI日期、`FDeliveryDate`←交期、`FMaterialId/FQty/FPrice`←明细行、备注←PI号（具体字段在测试账套联调时核对确认）

## 8. 错误处理

| 场景 | 处理 |
|---|---|
| AI 解析失败/超时 | 标记解析失败，可重试或手工在网页录入 |
| 字段缺失/置信度低 | 网页标红，必须人工补齐才能导入 |
| 客户无法匹配 | 网页下拉手工选择，记住映射 |
| 金蝶 API 报错 | 显示原始错误信息，进 failed/，可重导 |
| 重复 PI | 按 PI 号查重阻止 |

## 9. 配置与隐私

- `config.yaml`：金蝶服务器地址、API 账号、密码、账套 ID（先配测试账套）、Claude API Key、inbox/done/failed 路径
- 账密不写入代码仓库（config.yaml 加入 .gitignore）
- PI 内容仅发送给 Claude API 用于解析，不存储到任何第三方

## 10. 验证计划

1. 用户提供 2~3 份真实 PI 样本 → 验证解析准确率（目标：关键字段 100% 正确或可被人检出）
2. 连**测试账套**分三步走：
   - 第一步只跑查询接口（客户/物料核对），不写数据
   - 第二步 Save 草稿，人工在金蝶里逐字段核对
   - 第三步核对无误后启用正式导入（视需要开启自动 Submit）
3. validator 校验规则写单元测试
4. 防重逻辑测试：同一 PI 导入两次，第二次必须被阻止

## 11. 技术栈

Python 3.12（本机已装）+ Flask + pdfplumber + openpyxl + requests + anthropic SDK + pydantic + SQLite（标准库 sqlite3）。
