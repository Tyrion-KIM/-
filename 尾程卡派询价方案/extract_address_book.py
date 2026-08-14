# extract_address_book.py
import openpyxl, re, json

COUNTRY_CODE = {
    "austria": "AT", "denmark": "DK", "germany": "DE", "estonia": "EE",
    "sweden": "SE", "france": "FR", "italy": "IT", "poland": "PL",
    "czech republic": "CZ", "lithuania": "LT", "slovenia": "SI", "latvia": "LV",
    "romania": "RO", "netherlands": "NL", "hungary": "HU", "united states": "US",
    "greece": "GR", "bulgaria": "BG", "united kingdom": "GB", "belgium": "BE",
    "switzerland": "CH", "portugal": "PT", "croatia": "HR", "norway": "NO",
    "ireland": "IE",
}

def english_name(cell):
    s = re.sub(r"[^\x00-\x7F]", " ", str(cell or ""))
    return re.sub(r"\s+", " ", s).strip()

def country_code(cell):
    return COUNTRY_CODE.get(english_name(cell).lower(), "")

def clean_company(cell):
    s = str(cell or "").strip()
    up = s.upper()
    if not s or "@" in s or "VAT" in up or "EMAIL" in up:
        return ""
    return s

def clean_postcode(cell):
    if cell is None:
        return ""
    if isinstance(cell, (int, float)):
        return str(int(cell))
    return str(cell).strip()

def make_label(company, city, postcode):
    return company if company else f"{city} {postcode}".strip()

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
        address = re.sub(r"\s+", " ", str(r[4] or "")).strip()
        company = clean_company(r[5])
        label = make_label(company, city, postcode)
        rows.append({
            "id": len(rows) + 1,
            "label": label,
            "country": code,
            "countryName": country,
            "city": city,
            "postCode": postcode,
            "addressLine": address,
            "companyName": company,
        })
    return rows

def write_js(rows, out_path):
    body = json.dumps(rows, ensure_ascii=False, indent=2)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"window.ADDRESS_BOOK = {body};\n")

if __name__ == "__main__":
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(here, "YOKEE-车行询价.xlsx")
    out = os.path.join(here, "address_book.js")
    rows = extract_rows(src)
    write_js(rows, out)
    print(f"已生成 {len(rows)} 条地址 → {out}")
