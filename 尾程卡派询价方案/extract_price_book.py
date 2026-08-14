# extract_price_book.py
# 从 YOKEE-车行询价.xlsx 的「询价主表」抽取完整报价数据 → price_book.js
# 列映射（A=0 起）：B国家 C邮编 D城市 E街道 F公司 G公路距离 H..AN 托盘数1..33
#                   AO拼车时效 AP整车时效 AQ DHL报价 AR DHL时效 AS UPS报价 AT UPS时效 AU备注
import openpyxl, re, json
from extract_address_book import english_name, country_code, clean_company, clean_postcode, make_label

PALLET_COLS = list(range(7, 40))  # H..AN = 托盘数1..33
IDX_GROUPAGE_LEAD = 40   # AO 拼车时效
IDX_FULLTUCK_LEAD = 41   # AP 整车时效
IDX_NOTE = 46            # AU 备注

def clean_number(cell):
    """把价格/距离等单元格转成 float（空→None，去掉逗号/货币符号）。"""
    if cell is None:
        return None
    if isinstance(cell, (int, float)):
        v = float(cell)
    else:
        s = str(cell).strip().replace(",", "").replace("€", "").replace("EUR", "").strip()
        if not s:
            return None
        try:
            v = float(s)
        except ValueError:
            return None
    return round(v, 2)

def clean_text(cell):
    s = str(cell or "").strip()
    return re.sub(r"\s+", " ", s)

def extract_rows(path):
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb["询价主表"]
    rows = []
    for r in ws.iter_rows(min_row=6, values_only=True):
        if not r or r[1] is None:
            continue
        country = english_name(r[1])
        code = country_code(r[1])
        city = str(r[3] or "").strip()
        postcode = clean_postcode(r[2])
        address = clean_text(r[4])
        company = clean_company(r[5])
        label = make_label(company, city, postcode)
        distance = clean_number(r[6]) if len(r) > 6 else None
        pallet_prices = [clean_number(r[i]) if len(r) > i else None for i in PALLET_COLS]
        max_pallets = 0
        for i, p in enumerate(pallet_prices, start=1):
            if p is not None:
                max_pallets = i
        rows.append({
            "id": len(rows) + 1,
            "label": label,
            "country": code,
            "countryName": country,
            "city": city,
            "postCode": postcode,
            "addressLine": address,
            "companyName": company,
            "distanceKm": distance,
            "palletPrices": pallet_prices,
            "maxPallets": max_pallets,
            "groupageLeadTime": clean_text(r[IDX_GROUPAGE_LEAD]) if len(r) > IDX_GROUPAGE_LEAD else "",
            "fullTruckLeadTime": clean_text(r[IDX_FULLTUCK_LEAD]) if len(r) > IDX_FULLTUCK_LEAD else "",
            "note": clean_text(r[IDX_NOTE]) if len(r) > IDX_NOTE else "",
        })
    return rows

def write_js(rows, out_path):
    body = json.dumps(rows, ensure_ascii=False, indent=2)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"window.PRICE_BOOK = {body};\n")

if __name__ == "__main__":
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(here, "YOKEE-车行询价.xlsx")
    out = os.path.join(here, "price_book.js")
    rows = extract_rows(src)
    write_js(rows, out)
    print(f"已生成 {len(rows)} 条报价 → {out}")
