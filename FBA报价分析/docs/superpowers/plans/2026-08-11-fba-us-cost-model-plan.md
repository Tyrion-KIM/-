# FBA 美国站全链路成本数据模型 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建 `fba_us_cost_model.json` — 美国站 FBA 全链路核心费率结构化数据（AGL海运 + FBA配送费 + 月度仓储费）

**Architecture:** 单一 Python 脚本 `scripts/build_fba_cost_model.py`，分三个模块按序提取数据，最终组装 JSON。AGL 数据来自本地 Excel（openpyxl），FBA 费率通过 WebFetch 拉取 Amazon 官方页面后手工结构化映射。

**Tech Stack:** Python 3 + openpyxl (Excel 读取) + json (输出)

## Global Constraints

- 输出目录：`data/`
- JSON 文件名：`fba_us_cost_model.json`
- 脚本入口：`scripts/build_fba_cost_model.py`
- 校验报告：`docs/validation_report.md`
- 美国站 only，不含欧洲站
- 费率项仅核心三项（配送费 + 仓储费 + AGL海运），不含附加费

---

## 文件结构

```
FBA报价分析/
├── scripts/
│   └── build_fba_cost_model.py    # ★ 主脚本 — 读取 Excel + 组装 JSON
├── data/
│   └── fba_us_cost_model.json     # ★ 输出 — 结构化费率数据
├── docs/
│   └── validation_report.md       # 校验报告
└── AGL海运价卡 2026.7.31.xlsx     # 源数据（只读）
```

- `build_fba_cost_model.py`：约 200 行，三个函数 `extract_agl()`, `build_fulfillment()`, `build_storage()`，一个 `assemble()`，一个 `main()`
- `fba_us_cost_model.json`：纯数据，无依赖
- `validation_report.md`：手工编写，标注每项数据来源 URL 和置信度

---

## AGL Excel 列映射（已确认）

| Col | 字段 | 用途 |
|-----|------|------|
| A (0) | No. | 行号 |
| B (1) | Dest.Region | US |
| C (2) | Speed Mode | Standard Ocean / Fast Ocean |
| D (3) | Currency | RMB / USD |
| E (4) | Product | AMP |
| F (5) | FOB | FOB / non-FOB |
| G (6) | Origin Port | 深圳/上海/宁波/青岛/天津/厦门 |
| I (8) | Destination Region | 美西/美东 |
| K (10) | Destination City | Los Angeles / New York 等 |
| M (12) | Amazon FC | FC 代码 (POC1/POC2/POC3 等) |
| O (14) | FC Type | 标准件 / 一般件 |
| Q (16) | Fixed Fee | 固定费用 (RMB) |
| S (18) | 1-5 CBM | 运价 |
| T (19) | 5-10 CBM | 运价 |
| U (20) | 10-15 CBM | 运价 |
| V (21) | >15 CBM | 运价 |

---

### Task 1: 项目脚手架 + AGL 数据提取模块

**Files:**
- Create: `scripts/build_fba_cost_model.py`

**Interfaces:**
- Produces: `extract_agl(excel_path: str) -> dict` — 返回 `agl_ocean_freight` 段完整结构
- Produces: `build_fulfillment() -> dict` — 返回 `fba_fulfillment` 段（占位，Task 2 填充）
- Produces: `build_storage() -> dict` — 返回 `fba_storage` 段（占位，Task 3 填充）
- Produces: `assemble(agl, fulfillment, storage) -> dict` — 拼合三段 + meta
- Produces: `main()` — 入口

- [ ] **Step 1: 创建目录结构**

```bash
mkdir -p scripts data docs
```

- [ ] **Step 2: 安装依赖**

```bash
pip install openpyxl
```

- [ ] **Step 3: 编写脚本骨架 + AGL 提取函数**

```python
"""build_fba_cost_model.py — 美国站 FBA 全链路成本数据提取与组装"""
import json
import os
from datetime import date
from openpyxl import load_workbook

# === 配置 ===
EXCEL_PATH = os.path.join(os.path.dirname(__file__), "..", "AGL海运价卡 2026.7.31.xlsx")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "fba_us_cost_model.json")

# === AGL 数据提取 ===

def extract_agl(excel_path: str) -> dict:
    """从 AGL 海运价卡 Excel 提取所有路由和运价"""
    wb = load_workbook(excel_path, data_only=True)
    ws = wb["sheet1"]

    routes = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[1] != "US":
            continue
        origin = str(row[6]).strip()        # Col G: Origin Port
        dest_city = str(row[10]).strip()    # Col K: Destination City
        dest_region = str(row[8]).strip()   # Col I: Destination Region
        amazon_fc = str(row[12]).strip()    # Col M: Amazon FC
        fc_type = str(row[14]).strip()      # Col O: FC Type
        speed_mode = str(row[2]).strip()    # Col C: Speed Mode
        fob = str(row[5]).strip()           # Col F: FOB/non-FOB
        currency = str(row[3]).strip()      # Col D: Currency
        product = str(row[4]).strip()       # Col E: Product
        fixed_fee = float(row[16])          # Col Q: Fixed Fee
        rate_1_5 = float(row[18])           # Col S: 1-5 CBM
        rate_5_10 = float(row[19])          # Col T: 5-10 CBM
        rate_10_15 = float(row[20])         # Col U: 10-15 CBM
        rate_gt15 = float(row[21])          # Col V: >15 CBM

        routes.append({
            "origin_port": origin,
            "dest_city_en": dest_city,
            "dest_region": dest_region,
            "amazon_fc": amazon_fc,
            "fc_type": fc_type,
            "speed_mode": speed_mode,
            "fob": fob,
            "currency": currency,
            "product": product,
            "fixed_fee": fixed_fee,
            "rate_1_5_cbm": rate_1_5,
            "rate_5_10_cbm": rate_5_10,
            "rate_10_15_cbm": rate_10_15,
            "rate_gt15_cbm": rate_gt15
        })

    wb.close()
    return {
        "description": "AGL海运头程价卡 — 中国→美国",
        "source_file": os.path.basename(excel_path),
        "valid_from": "2026-07-31",
        "routes": routes
    }


# === FBA 配送费（占位，Task 2 填充） ===

def build_fulfillment() -> dict:
    """FBA 配送费 — 美国站 2026 费率"""
    # 数据通过 WebFetch 提取后手工结构化填入
    return {
        "description": "FBA配送费 — 美国站 2026（2026/1/15生效）",
        "currency": "USD",
        "source_url": "https://sellercentral.amazon.com/help/hub/reference/external/GMUTB89XM7AATPR3",
        "effective_period": {
            "non_peak": "2026-01-15 to 2026-10-14",
            "peak": "2026-10-15 to 2027-01-14"
        },
        "size_tiers": [
            # Task 2 填充
        ]
    }


# === FBA 仓储费（占位，Task 3 填充） ===

def build_storage() -> dict:
    """FBA 月度仓储费 — 美国站"""
    return {
        "description": "FBA月度仓储费 — 美国站",
        "currency": "USD",
        "unit": "per_cubic_foot_per_month",
        "source_url": "https://sellercentral.amazon.com/help/hub/reference/external/G200612770",
        "rates": [
            # Task 3 填充
        ]
    }


# === 组装 ===

def assemble(agl: dict, fulfillment: dict, storage: dict) -> dict:
    return {
        "meta": {
            "version": "1.0",
            "generated_at": date.today().isoformat(),
            "source_urls": {
                "fba_fulfillment": "https://sellercentral.amazon.com/help/hub/reference/external/GMUTB89XM7AATPR3",
                "fba_fee_changes": "https://sellercentral.amazon.com/help/hub/reference/external/ABBX6GZPA8MSZGW",
                "fba_storage": "https://sellercentral.amazon.com/help/hub/reference/external/G200612770",
                "chinese_summary": "https://gs.amazon.cn/news/news-notices-251016"
            },
            "effective_date": "2026-01-15",
            "notes": "美国站FBA全链路成本核心项：AGL海运头程 + FBA配送费 + FBA月度仓储费。不含长期仓储/移除/退货/低库存等附加费。"
        },
        "agl_ocean_freight": agl,
        "fba_fulfillment": fulfillment,
        "fba_storage": storage
    }


# === 入口 ===

def main():
    print("Extracting AGL rates...")
    agl = extract_agl(EXCEL_PATH)
    print(f"  → {len(agl['routes'])} routes extracted")

    print("Building fulfillment rates...")
    fulfillment = build_fulfillment()

    print("Building storage rates...")
    storage = build_storage()

    print("Assembling...")
    model = assemble(agl, fulfillment, storage)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(model, f, ensure_ascii=False, indent=2)

    print(f"Done → {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 运行脚本验证 AGL 数据提取**

```bash
cd "C:\Users\LD1621\Desktop\FBA报价分析" && python scripts/build_fba_cost_model.py
```

预期：输出 `data/fba_us_cost_model.json`，AGL routes 数量 > 0，fulfillment/storage 为空占位。

- [ ] **Step 5: 提交**

```bash
git add scripts/build_fba_cost_model.py data/fba_us_cost_model.json
git commit -m "feat: 项目脚手架 + AGL数据提取模块"
```

---

### Task 2: FBA 配送费率数据提取

**Files:**
- Modify: `scripts/build_fba_cost_model.py` — `build_fulfillment()` 函数

**Interfaces:**
- Consumes: 无
- Produces: `build_fulfillment() -> dict` — 填充完整的 FBA 配送费 `size_tiers` 数组

- [ ] **Step 1: WebFetch 拉取 Amazon FBA 配送费率页面**

```
URL: https://sellercentral.amazon.com/help/hub/reference/external/GMUTB89XM7AATPR3
提取内容: 所有尺寸分段 × 重量阶梯 × 旺季/非旺季 × 服装/非服装 的配送费率数字
```

- [ ] **Step 2: 提取费率数字，填入 `size_tiers` 数组**

从 WebFetch 渲染的 markdown 中找到费率表，提取以下尺寸分段：

| 尺寸分段 | 重量上限 | 非旺季(服装) | 非旺季(非服装) | 旺季(服装) | 旺季(非服装) |
|---|---|---|---|---|---|
| 小号标准 | ≤4 oz | ... | ... | ... | ... |
| 小号标准 | 4-8 oz | ... | ... | ... | ... |
| 小号标准 | 8-12 oz | ... | ... | ... | ... |
| 小号标准 | 12-16 oz | ... | ... | ... | ... |
| 大号标准 | ≤4 oz | ... | ... | ... | ... |
| 大号标准 | 4-8 oz | ... | ... | ... | ... |
| ... | ... | ... | ... | ... | ... |
| 大号大件 | ≤1 lb | ... | ... | ... | ... |
| ... | ... | ... | ... | ... | ... |

将数据按以下结构填入 `build_fulfillment()` 的 `size_tiers` 列表：

```python
{
    "tier_name": "小号标准",
    "size_limits": "≤15×12×0.75 in, ≤0.75 lb",
    "is_apparel": False,
    "weight_breakpoints": [
        {"max_weight_oz": 4, "non_peak": 3.12, "peak": 3.26},
        {"max_weight_oz": 8, "non_peak": 3.46, "peak": 3.60},
        ...
    ]
}
```

- [ ] **Step 3: 同步更新中文通告页面确认费率版本**

```
URL: https://gs.amazon.cn/news/news-notices-251016
确认 2026 美国站费率变更日期和关键数字与 Step 2 一致
```

- [ ] **Step 4: 运行脚本，检查 JSON 输出完整性**

```bash
cd "C:\Users\LD1621\Desktop\FBA报价分析" && python scripts/build_fba_cost_model.py
```

验证 `fba_fulfillment.size_tiers` 非空，每个 tier 包含完整 weight_breakpoints。

- [ ] **Step 5: 提交**

```bash
git add scripts/build_fba_cost_model.py data/fba_us_cost_model.json
git commit -m "feat: FBA配送费率数据 — 美国站2026尺寸分段×重量阶梯"
```

---

### Task 3: FBA 月度仓储费率数据提取

**Files:**
- Modify: `scripts/build_fba_cost_model.py` — `build_storage()` 函数

**Interfaces:**
- Consumes: 无
- Produces: `build_storage() -> dict` — 填充完整的仓储费 `rates` 数组

- [ ] **Step 1: WebFetch 拉取 FBA 仓储费页面**

```
URL: https://sellercentral.amazon.com/help/hub/reference/external/G200612770
提取内容: 标准件/大件 × 每立方英尺月费 × 旺季(10-12月)/非旺季(1-9月)
```

- [ ] **Step 2: 提取费率填入 `rates` 列表**

预期结构：

```python
"rates": [
    {
        "category": "标准件",
        "non_peak_jan_sep": 0.78,    # 每立方英尺/月
        "peak_oct_dec": 2.40
    },
    {
        "category": "大件",
        "non_peak_jan_sep": 0.56,
        "peak_oct_dec": 1.67
    }
]
```

- [ ] **Step 3: 运行脚本，检查 JSON 输出完整性**

```bash
cd "C:\Users\LD1621\Desktop\FBA报价分析" && python scripts/build_fba_cost_model.py
```

验证 `fba_storage.rates` 非空，含标准件和大件两个 category。

- [ ] **Step 4: 提交**

```bash
git add scripts/build_fba_cost_model.py data/fba_us_cost_model.json
git commit -m "feat: FBA月度仓储费率数据 — 美国站标准件/大件费率"
```

---

### Task 4: 校验报告 + 最终定稿

**Files:**
- Create: `docs/validation_report.md`

- [ ] **Step 1: 编写校验报告**

```markdown
# FBA 美国站全链路成本模型 — 校验报告

## 数据来源

| 数据段 | 来源 | URL | 提取方式 | 置信度 |
|---|---|---|---|---|
| AGL 海运价 | AGL海运价卡 2026.7.31.xlsx | 本地文件 | openpyxl 自动读取 | ✔ 已验证 |
| FBA 配送费 | Amazon Seller Central | GMUTB89XM7AATPR3 | WebFetch + 手工结构化 | 需确认 |
| FBA 仓储费 | Amazon Seller Central | G200612770 | WebFetch + 手工结构化 | 需确认 |

## AGL 校验

- 总路由数: [自动填充]
- 起运港: [自动填充]
- 目的城市: [自动填充]
- FC 类型: [自动填充]
- 费率范围(CBM): [自动填充]

## FBA 配送费校验

- 尺寸分段数: [手工填写]
- 费率数字与官方页面一致性: [手工确认]
- 旺季/非旺季日期范围: [手工确认]

## FBA 仓储费校验

- 费率与官方页面一致性: [手工确认]
- 旺季月份范围: 10-12月
```

- [ ] **Step 2: 逐项校验并更新报告**

运行 `build_fba_cost_model.py`，根据输出的 JSON 数据填充校验报告中的自动字段。手动对比 Amazon 官方页面确认费率数字。

- [ ] **Step 3: 提交定稿**

```bash
git add docs/validation_report.md
git commit -m "docs: 校验报告 — FBA全链路成本数据来源与置信度"
```
