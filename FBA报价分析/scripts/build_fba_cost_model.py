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

    # 列映射 (0-indexed, 共 17 列):
    # 0:No.  1:Dest.Region  2:SpeedMode  3:Currency  4:Product  5:FOB
    # 6:OriginPort(中英|分隔)  7:DestRegion(中英)  8:DestCity(中英)
    # 9:AmazonFC(中英)  10:FCType(中英)
    # 11:FixedFee  12:1-5CBM  13:5-10CBM  14:10-15CBM  15:>15CBM  16:RateKey

    def safe_str(v):
        return str(v).strip() if v else ""

    def safe_float(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0.0

    def split_cn_en(raw: str) -> tuple:
        """解析 'English | 中文' 或 '中文' 格式的混合列"""
        raw = raw.strip()
        if " | " in raw:
            parts = raw.split(" | ", 1)
            return parts[0].strip(), parts[1].strip()
        return raw, ""

    routes = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if len(row) < 17:
            continue
        if not row[1] or str(row[1]).strip() != "US":
            continue

        origin_en, origin_cn = split_cn_en(safe_str(row[6]))
        dest_region_en, dest_region_cn = split_cn_en(safe_str(row[7]))
        dest_city_en, dest_city_cn = split_cn_en(safe_str(row[8]))
        fc_en, fc_cn = split_cn_en(safe_str(row[9]))
        fc_type_en, fc_type_cn = split_cn_en(safe_str(row[10]))

        routes.append({
            "origin_port": origin_en,
            "origin_port_cn": origin_cn,
            "dest_region": dest_region_en,
            "dest_region_cn": dest_region_cn,
            "dest_city": dest_city_en,
            "dest_city_cn": dest_city_cn,
            "amazon_fc": fc_en,
            "amazon_fc_cn": fc_cn,
            "fc_type": fc_type_en,
            "fc_type_cn": fc_type_cn,
            "speed_mode": safe_str(row[2]),
            "fob": safe_str(row[5]),
            "currency": safe_str(row[3]),
            "product": safe_str(row[4]),
            "fixed_fee": safe_float(row[11]),
            "rate_1_5_cbm": safe_float(row[12]),
            "rate_5_10_cbm": safe_float(row[13]),
            "rate_10_15_cbm": safe_float(row[14]),
            "rate_gt15_cbm": safe_float(row[15])
        })

    wb.close()

    # 汇总统计
    origins = sorted(set(r["origin_port"] for r in routes))
    dest_cities = sorted(set(r["dest_city"] for r in routes))
    fc_types = sorted(set(r["fc_type"] for r in routes))
    fob_types = sorted(set(r["fob"] for r in routes))
    currencies = sorted(set(r["currency"] for r in routes))
    speed_modes = sorted(set(r["speed_mode"] for r in routes))

    return {
        "description": "AGL海运头程价卡 — 中国→美国",
        "source_file": os.path.basename(excel_path),
        "valid_from": "2026-07-31",
        "summary": {
            "total_routes": len(routes),
            "origin_ports": origins,
            "dest_cities": dest_cities,
            "fc_types": fc_types,
            "fob_types": fob_types,
            "currencies": currencies,
            "speed_modes": speed_modes
        },
        "routes": routes
    }


# === FBA 配送费（Task 2 填充） ===

def build_fulfillment() -> dict:
    """FBA 配送费 — 美国站 2026 费率"""
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


# === FBA 仓储费（Task 3 填充） ===

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
    print(f"  -> {agl['summary']['total_routes']} routes extracted")
    print(f"  -> Origins: {', '.join(agl['summary']['origin_ports'])}")
    print(f"  -> Destinations: {', '.join(agl['summary']['dest_cities'])}")
    print(f"  -> FC types: {', '.join(agl['summary']['fc_types'])}")
    print(f"  -> FOB types: {', '.join(agl['summary']['fob_types'])}")

    print("Building fulfillment rates...")
    fulfillment = build_fulfillment()

    print("Building storage rates...")
    storage = build_storage()

    print("Assembling...")
    model = assemble(agl, fulfillment, storage)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(model, f, ensure_ascii=False, indent=2)

    print(f"Done -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
