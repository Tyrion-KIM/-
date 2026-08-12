# FBA 美国站全链路成本分析

> 最后更新: 2026-08-12 | 数据版本: 2.0 (AGL 8.8 新版)

## 项目概述

构建 **FBA 美国站全链路单件成本模型**，覆盖：AGL 海运头程 + FBA 配送费 + FBA 月度仓储费。

交付物是一个**自包含、零依赖、双击即开**的单页 HTML 全景页。

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
├── AGL 2026年8月8日生效美线日线海运价格.xlsx   ← AGL 源数据 (当前)
└── AGL海运价卡 2026.7.31.xlsx                 ← AGL 源数据 (旧版)
```

---

## 数据源

| 数据段 | 源文件/URL | 提取方式 | 覆盖范围 |
|---|---|---|---|
| AGL 海运头程 FCL | `AGL 2026年8月8日...xlsx` → Sheet `FCL价卡` | openpyxl 自动 | 1680 条 (13港→5区) |
| AGL 海运头程 LCL | `AGL 2026年8月8日...xlsx` → Sheet `LCL价卡` | openpyxl 自动 | 1148 条 (8港→5区) |
| FBA 配送费 | Amazon Seller Central + 第三方汇总 | 手工结构化 | 7 尺寸分段 × 48 重量断点 |
| FBA 月度仓储费 | Amazon Seller Central + 第三方汇总 | 手工结构化 | 标准件/大件 × 非旺季/旺季 |

### AGL 价卡结构

- **FCL (整柜)**: `{固定费, 20GP, 40GP, 40HQ}` — USD 或 RMB
- **LCL (散货)**: `{固定费, 1-5CBM, 5-10CBM, 10-15CBM, >15CBM}` — USD 或 RMB
- 币种: FCL 840USD+840RMB, LCL 574USD+574RMB (半半)
- 起运港 13 个: 上海/厦门/天津/宁波/海防/深圳/珠海/盐田/福州/胡志明市/连云港/青岛/香港
- 目的地 10 城: 洛杉矶/奥克兰/纽约/巴尔的摩/萨凡纳/诺福克/西雅图/休斯顿/堪萨斯城/孟菲斯
- 更多细节见 `data/fba_us_cost_model.json` → `agl_ocean_freight.summary`

---

## 三 Tab 页面功能

### Tab 1 - 费率速查表
- **FBA 配送费**: 可折叠 accordion 表格，筛选器（季节/售价档位/服装）
- **月度仓储费**: 内联条形图对比，标注旺季倍数
- **AGL 头程价卡**: 6 维筛选（方式/起运港/目的地/FC类型/速度/FOB），分页 20 行
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
2. 修改 `scripts/build_fba_cost_model.py` 第 6 行的 `EXCEL_PATH`
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

1. **服装非旺季费率缺失**: 目前仅有旺季数据，非旺季需从 Seller Central 补充
2. **旺季 under_10 / over_50 档位**: 部分未完全填充
3. **超大件 150+lb 旺季费率**: 未找到匹配数据
4. **AGL 计算器**: 使用全量 LCL 路由均价，实际需根据具体起运港/目的 FC 精确匹配
5. **不含**: 长期仓储费、退货处理费、低库存费、SIPP 包装费 ($2.07/件)

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
