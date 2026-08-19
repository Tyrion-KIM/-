# FBA 全链路成本分析（美国 / 欧洲）

> **状态: ⚠ 暂定稿 (DRAFT)** — 数据与页面已可正常使用，但费率数据仍有缺口（见「已知限制」），待人工从 Seller Central 补齐后定稿。
> 最后更新: 2026-08-19 | 数据版本: 2.1 (AGL 美 8.8 · 欧 8.7 双区域) + AGL切换评估定稿

## 项目概述

构建 **FBA 全链路单件成本模型**，覆盖：AGL 海运头程（美国 / 欧洲双区域）+ FBA 配送费 + FBA 月度仓储费。

交付物是一个**自包含、零依赖、双击即开**的单页 HTML 全景页。

---

## AGL 切换评估（2026-08-19 定稿）

评估「头程切 AGL 是否整体省成本」：545 天逐日库存仿真，4 策略（A 现状谷仓 / B AGL整柜FBA / C AGL散货LCL 45天批 / D 分流）× 3 系列（G/M/N）× 3 情景（0.5/1.0/1.5x），动态计入 FBA 旺季仓储（10-12月 $1.40/cuft/月）、仓储利用率附加费（供应>22周）、超龄附加费（≥181天，271天跳10倍）、移除费。

**结论 — 按系列分流，不一刀切：**

| 系列 | 建议 | 关键数字 |
|---|---|---|
| M | ✅ AGL整柜直发FBA | 三情景省 10.2~12.8万/柜；盈亏平衡=预期销量22% |
| G | ⚠️ AGL散货LCL 45天批 | 整柜平衡点=预期64%，0.5x反亏11.5万；LCL批省3~5万零冗余 |
| N | ❌ 禁止整柜进FBA | 预期情景多花102万/柜（超龄63万+利用率26万+移除8万），959天清不完 |

配套规则：配货必须按销量比例（G尾部0.125/天SKU均分66件→每件超龄1,887元）；三柜同日到仓合并利用率22.4周刚好触发账户级附加费。原表AGL行K/N两列重复计海运价，修正后整柜再省3.3万/柜。

- 报告: `output/agl_switch_report.html`（自包含双击即开）
- 仿真: `scripts/agl_vs_forwarder_sim.py` → `data/agl_sim_results.json`；出报告: `scripts/build_agl_report.py`
- 源数据: `data/logistics_center_costs_20260803_raw.json`（钉钉《物流中心费用20260803V1》原始API响应存档）


---

## 文件结构

```
FBA报价分析/
├── README.md                              ← 你现在看的文件
│
├── data/
│   └── fba_us_cost_model.json             ← ★ 结构化费率数据 (JSON)
│
├── scripts/
│   └── build_fba_cost_model.py            ← ★ 生成 JSON 的脚本
│
├── output/
│   └── fba_us_cost_panorama.html          ← ★ 最终交付物 (双击即开)
│
├── docs/
│   └── validation_report.md               ← 数据校验报告
│
├── AGL 2026年8月8日生效美线日线海运价格.xlsx   ← AGL 源数据 (美国, 当前)
├── EUK价卡计算器_2026年8月7日生效海运价格.xlsx  ← AGL 源数据 (欧洲, 当前)
└── AGL海运价卡 2026.7.31.xlsx                 ← AGL 源数据 (旧版)
```

---

## 数据源

| 数据段 | 源文件/URL | 提取方式 | 覆盖范围 |
|---|---|---|---|
| AGL 海运头程 (美国) | `AGL 2026年8月8日...xlsx` → `FCL价卡`+`LCL价卡` | openpyxl 自动 | 2828 条 (13港→10城) |
| AGL 海运头程 (欧洲) | `EUK价卡计算器_2026年8月7日...xlsx` → `FCL价卡`+`LCL价卡` | openpyxl 自动 | 856 条 (9港→5城) |
| FBA 配送费 | Amazon Seller Central + 第三方汇总 | 手工结构化 | 7 尺寸分段 × 48 重量断点 (仅美国) |
| FBA 月度仓储费 | Amazon Seller Central + 第三方汇总 | 手工结构化 | 标准件/大件 × 非旺季/旺季 (仅美国) |

### AGL 价卡结构

- **双区域**: `agl_ocean_freight: {us: {...}, eu: {...}}`，页头「美国/欧洲」按钮切换
- **FCL (整柜)**: `{固定费, 20GP, 40GP, 40HQ}` — USD 或 RMB
- **LCL (散货)**: `{固定费, 1-5CBM, 5-10CBM, 10-15CBM, >15CBM}` — USD 或 RMB
- **美国** (8.8 生效): 2828 条 (FCL 1680 + LCL 1148)，13 港 → 10 城
- **欧洲** (8.7 生效): 856 条 (FCL 688 + LCL 168)，9 港 → 5 城 (德国/意大利/法国/英国/西班牙)
- 更多细节见 `data/fba_us_cost_model.json` → `agl_ocean_freight.<us|eu>.summary`

---

## 三 Tab 页面功能

### Tab 1 - 费率速查表
- **FBA 配送费**: 可折叠 accordion 表格，筛选器（季节/售价档位/服装）
- **月度仓储费**: 内联条形图对比，标注旺季倍数
- **AGL 头程价卡**: 页头「美国/欧洲」区域切换 + 6 维筛选（方式/起运港/目的地/FC类型/速度/FOB），分页 20 行
  - "全部方式" 混合显示 FCL+LCL，FCL 行末填充 `—`
  - 筛选 "🚢 整柜 (FCL)" 看 20GP/40GP/40HQ
  - 筛选 "📦 散货 (LCL)" 看 CBM 阶梯价

### Tab 2 - 汇报看板
- 5 张 KPI 卡片 + 两组 SVG 条形图 + 关键洞察

### Tab 3 - 费率计算器
- 输入: 长宽高(in) + 重量(lb) + 售价档位 + 服装/非服装 + 季节 + 仓储月数 + FOB/non-FOB + 燃油附加费
- 实时识别 Amazon 尺寸分段 (5 级决策树)
- 输出: FBA配送费 + 仓储费 + AGL头程分摊 + 燃油附加费 + 合计
- **AGL 使用 LCL 散货路由 1-5CBM 均值** (USD 直接计价, RMB 按 7.25 换算)

---

## 如何更新数据

### 更新 AGL 报价单

1. 将新的 AGL Excel 放到项目根目录
2. 修改 `scripts/build_fba_cost_model.py` 中的 `EXCEL_PATH_US` / `EXCEL_PATH_EU`（对应美国/欧洲价卡），并在 `AGL_REGIONS` 里更新生效日期与描述
3. 运行: `cd "C:\Users\LD1621\Desktop\FBA报价分析" && python scripts/build_fba_cost_model.py`
4. 新 JSON 自动输出到 `data/fba_us_cost_model.json`

### 更新 HTML (嵌入新 JSON)

用 Python 嵌入 (避免 PowerShell/记事本损坏 UTF-8):

```python
import json

with open('data/fba_us_cost_model.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
json_str = json.dumps(data, ensure_ascii=False)

with open('output/fba_us_cost_panorama.html', 'r', encoding='utf-8') as f:
    html = f.read()

start = html.find('<script id="data-source" type="application/json">') + len('<script id="data-source" type="application/json">')
end = html.find('</script>', start)
new_html = html[:start] + '\n' + json_str + '\n' + html[end:]

with open('output/fba_us_cost_panorama.html', 'w', encoding='utf-8') as f:
    f.write(new_html)
```

### 更新 FBA 配送费/仓储费

直接编辑 `scripts/build_fba_cost_model.py` 中的 `_fulfillment_tiers()` 和 `build_storage()` 函数，然后重新运行脚本。

---

## 关键算法

### 尺寸分段判定 (classifySizeTier)

```
1. ≤16oz, 最长边≤15", 中边≤12", 最短边≤0.75" → 小号标准
2. ≤20lb, 最长边≤18", 中边≤14", 最短边≤8"   → 大号标准
3. ≤50lb, 最长边≤60", 长+围≤130"             → 小号大件
4. ≤50lb                                      → 大号大件
5. >50lb                                      → 超大件 (按重量子分段: 0-50/50-70/70-150/150+)
```

### 公式费率解析 (parseFormula)

```javascript
// "6.97 + 0.08/4oz above 3lb"  →  6.97 + 0.08 * Math.ceil((ozAbove - ozAt3lb)/4)
// "7.55 + 0.38/lb above 1st lb" → 7.55 + 0.38 * (weight_lb - 1)
// "51.32 + 0.75/lb above 71 lb" → 51.32 + 0.75 * (weight_lb - 71)
```

---

## 已知限制

1. **欧洲 FBA 配送费/仓储费缺失**: 欧洲站目前仅有 AGL 头程价卡，FBA 配送费/仓储费数据暂缺，计算器切到欧洲区时仍按美国站费率估算
2. **服装非旺季费率缺失**: 目前仅有旺季数据，非旺季需从 Seller Central 补充
3. **旺季 under_10 / over_50 档位**: 部分未完全填充
4. **超大件 150+lb 旺季费率**: 未找到匹配数据
5. **AGL 计算器**: 使用全量 LCL 路由均价，实际需根据具体起运港/目的 FC 精确匹配
6. **不含**: 长期仓储费、退货处理费、低库存费、SIPP 包装费 ($2.07/件)

---

## 验收标准 (上次验证通过)

| # | 测试项 | 结果 |
|---|---|---|
| 1 | 双击 HTML 直接打开，无网络请求 | ✅ |
| 2 | 三 Tab 切换正常 | ✅ |
| 3 | 配送费表筛选器生效 | ✅ |
| 4 | AGL 表按方式/港口/目的地/FC 筛选 | ✅ |
| 5 | Dashboard 两个 SVG 图表正常 | ✅ |
| 6 | 10×8×0.5in, 0.5lb → 小号标准 $3.54 | ✅ |
| 7 | 16×12×6in, 2.5lb → 大号标准 $6.10 | ✅ |
| 8 | 亮/暗主题切换 + localStorage 持久化 | ✅ |
| 9 | Console 零 JS 错误 | ✅ |

## 三产品验证 (2026-08-12)

| 产品 | 尺寸(cm) | 重量 | 分段 | 配送费 | 仓储(3月) | AGL | 合计 |
|---|---|---|---|---|---|---|---|
| P1 | 80×48×37 | 23kg | 超大件 | $37.32 | $8.43 | $212.17 | $259.23 |
| P2 | 68×48×35 | 20kg | 小号大件 | $23.92 | $6.78 | $212.17 | $243.71 |
| P3 | 76×53.5×50 | 32.2kg | 超大件 | $51.32 | $12.06 | $212.17 | $277.35 |

> 条件: FOB / 燃油附加费 / 非旺季 / 非服装 / $10-50 售价档位 / 仓储 3 个月

---

## 技术栈

- **数据提取**: Python 3 + openpyxl
- **交付物**: 单 HTML (~920KB), 零外部依赖
- **图表**: 自建 SVG builder (纯 JS, viewBox 响应式)
- **主题**: CSS 自定义属性双主题 (light/dark + localStorage 持久化)
- **JSON 嵌入**: Python `json.dumps(ensure_ascii=False)` → 直接写入 HTML `<script>` 标签

---

## 变更历史 (Changelog)

| 日期 | 版本 | 变更 |
|---|---|---|
| 2026-08-11 | v1.0 | 初版 — 基于 `AGL海运价卡 2026.7.31.xlsx` (RMB/LCL only, 434 路由) + FBA 配送费 + 仓储费，构建三 Tab 单页 HTML |
| 2026-08-12 | v2.0 | **AGL 价卡切换** — 新文件 `AGL 2026年8月8日...xlsx` (USD+RMB / FCL整柜+LCL散货, 2828 路由)，新增整柜 20GP/40GP/40HQ 运价、越南港口(海防/胡志明)、更细目的地分区 |
| 2026-08-13 | v2.0 draft | 标记为「暂定稿」，补齐工程文档与待办清单 |
| 2026-08-14 | v2.1 | **新增欧洲区域** — 集成 `EUK价卡计算器_2026年8月7日...xlsx` (856 条 AGL 欧线价卡)，页头「美国/欧洲」切换，Tab1 价卡表 + Tab3 计算器 AGL 部分联动；FBA 配送费/仓储费仍仅美国站 |
| 2026-08-19 | — | **AGL切换评估定稿** — 545天冗余仿真（4策略×3系列×3情景），结论 M整柜/G散货LCL/N禁整柜，交付 `output/agl_switch_report.html` |

---

## 待办事项 (TODO)

**定稿前必须完成：**

- [ ] **服装非旺季费率** — 目前仅有旺季数据，需登录 Seller Central 补齐
- [ ] **旺季 under_10 / over_50 售价档位** — 部分缺失，需补齐
- [ ] **超大件 150+lb 旺季费率** — 未找到公开数据

**可选增强：**

- [ ] 计算器支持「指定起运港 + 目的 FC」精确匹配 AGL 费率（当前用全量 LCL 均价）
- [ ] 计算器支持「整柜 FCL」分摊模式（输入整柜件数，摊 20GP/40GP 运价）
- [x] 欧洲 AGL 头程 — 已集成欧线价卡，页头区域切换 (2026-08-14)
- [ ] 欧洲站 FBA 配送费/仓储费 — 数据待补齐 (当前计算器欧洲区按美站费率估算)
- [ ] 加入长期仓储费、退货处理费、低库存费等附加费

---

## 关键设计决策

| 决策 | 理由 |
|---|---|
| **计算器 AGL 用 LCL 散货均价** | FCL 整柜是按柜计价，无法直接摊到单件；LCL 按 CBM 计价适合单件估算 |
| **USD 直接计价 + RMB 按 7.25 换算** | 新价卡半 USD 半 RMB，统一折算成 USD 后取均值 |
| **JSON 用 Python 嵌入而非手工粘贴** | PowerShell/记事本会损坏 CJK UTF-8（曾出现 `。`→`€` 乱码），Python `ensure_ascii=False` 保证编码安全 |
| **Tab 切换用 JS 而非纯 CSS** | CSS `~` 兄弟选择器无法跨 `.tab-nav` 边界，改用 JS 直接 toggle `display` |
| **尺寸分段名匹配时去下划线** | 数据 `small_standard` vs 显示 `Small Standard`，匹配前 `replace(/_/g,' ')` |
| **混合 oz/lb 断点换算** | 早期断点用 oz、后期用 lb，匹配时 `max_weight_oz/16` 折算成 lb |

---

## 快速上手 (3 步)

1. **看结果**: 双击 `output/fba_us_cost_panorama.html` 直接打开
2. **改数据**: 编辑 `scripts/build_fba_cost_model.py` → 运行 → 自动更新 JSON
3. **刷新 HTML**: 用上文「更新 HTML」的 Python 片段重新嵌入 JSON
