# FBA 美国站全链路成本数据模型 — 设计规格

## 概述

构建美国站 Amazon FBA 全链路成本结构化数据，覆盖 **AGL 海运头程 → FBA 仓储配送 → 末端交付** 的核心费用项，输出可机读 JSON，后续可接计算器或看板。

## 范围

- **站点**：美国站（US）
- **费用项**：AGL 海运价 + FBA 配送费 + FBA 月度仓储费（核心三项）
- **产出**：`fba_us_cost_model.json` + 数据提取脚本 + 校验报告

## 数据模型

### 顶层结构

```json
{
  "meta": { ... },
  "agl_ocean_freight": { ... },
  "fba_fulfillment": { ... },
  "fba_storage": { ... }
}
```

### meta — 元信息

| 字段 | 类型 | 说明 |
|---|---|---|
| version | string | 数据版本号 |
| generated_at | string | 生成日期 ISO |
| source_urls | object | 每段数据的源 URL 映射 |
| effective_date | string | 费率生效日期 |
| notes | string | 备注 |

### agl_ocean_freight — AGL 海运头程

| 字段 | 类型 | 说明 |
|---|---|---|
| origin | string | 起运地 |
| destination | string | 目的地 |
| currency | string | 币种 (USD) |
| unit | string | 计费单位 (per_CBM) |
| routes | array | 路由列表 |

路由对象：`route`, `rate_usd_per_cbm`, `service_level`, `valid_from`

### fba_fulfillment — FBA 配送费

| 字段 | 类型 | 说明 |
|---|---|---|
| description | string | 费率说明 |
| currency | string | 币种 (USD) |
| effective_period | object | 非旺季/旺季日期范围 |
| size_tiers | array | 尺寸分段列表 |

尺寸分段对象：`tier_name`, `size_limits` (max L×W×H, max weight), `is_apparel` (bool), `weight_breakpoints` (含 max_weight, non_peak_rate, peak_rate)

### fba_storage — FBA 月度仓储费

| 字段 | 类型 | 说明 |
|---|---|---|
| description | string | 费率说明 |
| currency | string | 币种 (USD) |
| unit | string | 计费单位 (per_cubic_foot_per_month) |
| rates | array | 费率列表 |

费率对象：`category` (standard/oversize), `non_peak_jan_sep`, `peak_oct_dec`

## 数据提取流程

```
Step 1: AGL Excel  →  openpyxl 读取  →  路由×运价
Step 2: FBA配送费  →  WebFetch   →  markdown表格解析
Step 3: FBA仓储费  →  WebFetch   →  markdown表格解析
Step 4: 组装校验   →  JSON拼合   →  校验报告
```

### Step 1: AGL Excel 解析
- 输入：`AGL海运价卡 2026.7.31.xlsx`
- 方法：读取后按路由（起点→目的港）提取运价（USD/CBM）
- 需先探查 Excel 结构确定列映射

### Step 2: FBA 配送费 WebFetch
- 源 URL：`https://sellercentral.amazon.com/help/hub/reference/external/GMUTB89XM7AATPR3`
- 目标：提取尺寸分段 × 重量阶梯 × 旺季/非旺季 × 服装/非服装 的配送费率
- 策略：先 Fetch 查看 markdown 渲染结果，再决定解析方式（正则/结构化提取/手工映射）

### Step 3: FBA 仓储费 WebFetch
- 源 URL：`https://sellercentral.amazon.com/help/hub/reference/external/G200612770`
- 目标：提取标准件/大件 × 每立方英尺月费 × 旺季/非旺季
- 同样先 Fetch 后定策略

### Step 4: 组装校验
- 三段数据按 JSON schema 拼合
- 生成 `validation_report.md`，标注每个字段的数据来源和置信度

## 源 URL 清单

| 数据段 | URL |
|---|---|
| FBA 配送费率 | `sellercentral.amazon.com/help/hub/reference/external/GMUTB89XM7AATPR3` |
| FBA 费用变更总览 | `sellercentral.amazon.com/help/hub/reference/external/ABBX6GZPA8MSZGW` |
| 月度仓储费 | `sellercentral.amazon.com/help/hub/reference/external/G200612770` |
| 中文变更通告 | `gs.amazon.cn/news/news-notices-251016` |

## 文件组织

```
FBA报价分析/
├── data/
│   └── fba_us_cost_model.json     # ★ 主输出
├── scripts/
│   └── build_fba_cost_model.py    # 数据提取+组装脚本
├── docs/
│   ├── validation_report.md       # 校验报告
│   └── superpowers/specs/         # 本规格文档
└── AGL海运价卡 2026.7.31.xlsx     # 源数据（不变）
```

## 非目标（明确排除）

- 不含欧洲站费率
- 不含长期仓储费、移除费、退货处理费、低库存费等附加费
- 不含交互式计算器（本次只出数据层，计算器后续迭代）
- 不含 HTML 看板/可视化

## 验收标准

1. JSON schema 完整覆盖三个阶段的所有字段
2. FBA 费率与官方 2026 生效版本一致
3. 校验报告明确标注每项数据的来源和置信度
4. 脚本可复跑（费率变更时只需重新运行）
