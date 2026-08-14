# 途兔卡派内部询价工具 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 做一个单文件 HTML 内部询价工具，运营选定目的地车行 + 货物，工具直连途兔卡派官方报价 API 实时返回报价。

**Architecture:** 一个 Python 脚本把 `YOKEE-车行询价.xlsx` 的 99 个目的地抽成 `address_book.js`（数据文件）；一个 HTML 主文件加载它并直连途兔 API。网络出口全部收敛到 `callTutu()` 一个函数，方便日后迁到自建后端（方案 C）。

**Tech Stack:** 纯前端 HTML/CSS/JS（无构建、无框架）；Python 3.12 + openpyxl（仅用于生成地址库，运行时不需要）；unittest（stdlib）做脚本单测；Playwright 做手工验证。

## Global Constraints

- 交付物放在 `C:\Users\LD1621\Desktop\尾程卡派询价方案\`（下称项目根）。
- 途兔 API 沙箱 Base：`http://test.teknihall-trucking.com:8080/api`；鉴权头 `Api-Key`。
- 接口所有文本字段「不能包含中文」；国家用 2 位码；包装类型枚举 `FP/HP/KT/EP/KI`。
- `Api-Key` 当前未开通权限（返回 `暂无权限`），联调前先在途兔侧开通。
- HTML 必须双击（file:// 协议）即可用：**不依赖 fetch 本地文件**，地址库用 `<script src>` 加载；分享时 `.html` 与 `address_book.js` 放同一目录。
- 币种 EUR；报价总价字段 `price`，明细 `priceDetail[]`。
- 演示模式开关 `DEMO_MODE`：true 时 `callTutu` 返回本地 mock，不触网。

## File Structure

```
尾程卡派询价方案/
├── YOKEE-车行询价.xlsx            # 已有，地址库唯一数据源，勿改
├── extract_address_book.py        # 新：xlsx → address_book.js
├── test_extract_address_book.py   # 新：抽取脚本单测（unittest）
├── address_book.js                # 生成物：const ADDRESS_BOOK = [...]
├── 卡派询价工具.html              # 新：询价工具主文件
├── 更新地址库.bat                 # 新：双击重生成 address_book.js
└── README.md                      # 新：使用与更新说明
```

---

### Task 1: 地址库抽取脚本

**Files:**
- Create: `extract_address_book.py`
- Test: `test_extract_address_book.py`

**Interfaces:**
- Consumes: `YOKEE-车行询价.xlsx`（sheet「询价主表」，数据从第 6 行起；列：A序号 B国家 C邮编 D城市 E街道 F公司名称）
- Produces: 函数 `english_name(cell)`、`country_code(cell)`、`clean_company(cell)`、`make_label(company, city, postcode)`、`extract_rows(path) -> list[dict]`、`write_js(rows, out_path)`；生成物 `address_book.js`，内容为 `const ADDRESS_BOOK = [ {id,label,country,countryName,city,postCode,addressLine,companyName}, ... ];`

- [ ] **Step 1: 写失败的测试**

```python
# test_extract_address_book.py
import unittest, os, tempfile
from extract_address_book import english_name, country_code, clean_company, make_label, write_js

class TestExtract(unittest.TestCase):
    def test_english_name_strips_chinese(self):
        self.assertEqual(english_name("奥地利 Austria"), "Austria")
        self.assertEqual(english_name("英国 United Kingdom"), "United Kingdom")

    def test_country_code_mapping(self):
        self.assertEqual(country_code("奥地利 Austria"), "AT")
        self.assertEqual(country_code("英国 United Kingdom"), "GB")
        self.assertEqual(country_code("丹麦 Denmark"), "DK")
        self.assertEqual(country_code("未知 Xyzzy"), "")

    def test_clean_company_drops_junk_and_empty(self):
        self.assertEqual(clean_company("EICO A/S"), "EICO A/S")
        self.assertEqual(clean_company("VAT ID: ATU1  EMAIL: a@b.com"), "")
        self.assertEqual(clean_company(""), "")
        self.assertEqual(clean_company(None), "")

    def test_make_label(self):
        self.assertEqual(make_label("EICO A/S", "Sønderborg", "6400"), "EICO A/S")
        self.assertEqual(make_label("", "Genk", "3600"), "Genk 3600")

    def test_write_js_emits_const(self):
        rows = [{"id":1,"label":"Genk 3600","country":"BE","countryName":"Belgium",
                 "city":"Genk","postCode":"3600","addressLine":"De Schom 39","companyName":""}]
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "address_book.js")
            write_js(rows, p)
            text = open(p, encoding="utf-8").read()
            self.assertIn("const ADDRESS_BOOK = [", text)
            self.assertIn('"postCode": "3600"', text)

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m unittest test_extract_address_book -v`
Expected: 失败，`ModuleNotFoundError: No module named 'extract_address_book'`

- [ ] **Step 3: 写抽取脚本**

```python
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
        f.write(f"const ADDRESS_BOOK = {body};\n")

if __name__ == "__main__":
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(here, "YOKEE-车行询价.xlsx")
    out = os.path.join(here, "address_book.js")
    rows = extract_rows(src)
    write_js(rows, out)
    print(f"已生成 {len(rows)} 条地址 → {out}")
```

- [ ] **Step 4: 运行确认通过 + 真实生成**

Run: `python -m unittest test_extract_address_book -v`
Expected: 全部 PASS（6 项）。

Run: `python extract_address_book.py`
Expected: 输出 `已生成 99 条地址 → ...address_book.js`；`address_book.js` 首行为 `const ADDRESS_BOOK = [`。

- [ ] **Step 5: Commit**

```bash
git add extract_address_book.py test_extract_address_book.py address_book.js
git commit -m "feat: 地址库抽取脚本 — xlsx 99 目的地 → address_book.js"
```

---

### Task 2: 询价工具 HTML 主文件

**Files:**
- Create: `卡派询价工具.html`

**Interfaces:**
- Consumes: `address_book.js` 里全局 `window.ADDRESS_BOOK`；途兔 API `GET /external/orders/v2/listProductAndService`、`POST /external/orders/v2/quotation`。
- Produces: 全局 `CONFIG`、`callTutu(path, body)`、`buildQuotationRequest()`、`renderResult(data)`、`renderError(msg)`、`applyAddress(entry)`；`CONFIG.API_KEY`、`CONFIG.DEMO_MODE`、`CONFIG.ORIGIN`、`CONFIG.DEFAULT_CONTACT`。

HTML 按 5 模块组织（均内联 `<script>`，无外部依赖，除 `address_book.js`）：

1. **配置区**（`<script>` 顶部常量，转 C 时改这里）：
```js
const CONFIG = {
  API_BASE: "http://test.teknihall-trucking.com:8080/api",
  API_KEY: "sk_o4BEldSLEhr4o4x4D5Nu7pi75Cz8pb6dZzGnRlGNAfk74upSEUqkBeD_9UQK5f04",
  DEMO_MODE: true, // 演示模式：key 未开通前置 true；开通后改 false
  ORIGIN: {  // 固定发货仓 Neuss
    companyName: "ANTHBOT GER GMBH",
    contactPerson: "ANTHBOT GER GMBH", contactEmail: "",
    contactPhone: "15223942230", phonePrefix: "+49",
    addressLine: "Bussardweg 4", addressLine2: "",
    country: "DE", city: "Neuss", postCode: "41468", isPrivate: false,
  },
  DEFAULT_CONTACT: {  // 目的地缺联系人时的兜底
    contactPerson: "ANTHBOT GER GMBH", contactEmail: "",
    contactPhone: "15223942230", phonePrefix: "+49",
  },
};
```

2. **地址库**：`<script src="address_book.js"></script>` 置于主脚本之前，读 `window.ADDRESS_BOOK` 填充目的地下拉；下拉支持按 label/国家/城市/邮编做子串过滤。选中后 `applyAddress(entry)` 把 entry 合并 `CONFIG.DEFAULT_CONTACT`，得到完整 dropAddress（`{...DEFAULT_CONTACT, companyName, addressLine, country, city, postCode, isPrivate:false}`）。

3. **表单**：发货仓（默认锁 CONFIG.ORIGIN，可点开改）；目的地（下拉 + 「手动输入」切换：国家2位码下拉 / 城市 / 邮编 / 街道 / 联系人 / 电话 / 邮箱 / 是否私人地址，含「不能含中文」实时校验）；货物清单（可增删行：包装类型下拉 FP欧托/HP半托/KT纸箱/EP一次性托/KI木箱、单件重量kg、长宽高cm、件数、堆叠checkbox、品名、危险品checkbox，默认一行「FP · 240kg · 120×80×200 · 1件 · 堆叠 · goodsName=pallet · 非危险」）；拣货日期（默认今天 `yyyy-MM-dd`）；高级项折叠（附加服务多选、固定产品编码、货值、托盘交换数量）。

4. **网络层**（唯一出口）：
```js
async function callTutu(path, body) {
  if (CONFIG.DEMO_MODE) {
    return { code: 0, msg: "", data: {
      productCode: "DEMO-LTL", productName: "零担卡派（演示）", channel: "DEMO",
      price: 320, priceDetail: [
        { code: "base", price: 280, name: "基础运费" },
        { code: "fuel", price: 40, name: "燃油附加费" },
      ] } };
  }
  const url = CONFIG.API_BASE + path;
  const opts = {
    method: body ? "POST" : "GET",
    headers: { "Api-Key": CONFIG.API_KEY, "Content-Type": "application/json" },
  };
  if (body) opts.body = JSON.stringify(body);
  try {
    const res = await fetch(url, opts);
    return await res.json();
  } catch (e) {
    return { code: -1, msg: "网络错误：无法连接途兔服务（请检查网络，或确认已切回真实模式）", data: null };
  }
}
```

5. **请求拼装 + 结果渲染**：
```js
function buildQuotationRequest() {
  const drop = currentDropAddress();       // 由下拉选中或手动输入得来，含 DEFAULT_CONTACT 合并
  const goods = collectGoods();            // 读表单货物行 → goodsInfoList
  const req = {
    pickAddress: CONFIG.ORIGIN,
    dropAddress: drop,
    goodsInfoList: goods,
    pickDate: document.getElementById("pickDate").value,
  };
  const svc = collectServiceCodes();       // 高级项多选
  if (svc.length) req.serviceCodes = svc;
  const prod = document.getElementById("productCode").value.trim();
  if (prod) req.productCode = prod;
  const val = parseFloat(document.getElementById("valueOfGoods").value);
  if (!isNaN(val)) req.valueOfGoods = val;
  const exch = parseInt(document.getElementById("packageExchangeQuantity").value, 10);
  if (!isNaN(exch)) req.packageExchangeQuantity = exch;
  return req;
}

async function onQuote() {
  if (!validateForm()) return;             // 必填 + 含中文校验，失败则标红并 return
  setLoading(true);
  const body = buildQuotationRequest();
  const r = await callTutu("/external/orders/v2/quotation", body);
  setLoading(false);
  if (r.code === 0 && r.data) { renderResult(r.data); }
  else { renderError(r.code === 500 ? "秘钥未开通权限，请联系途兔销售经理开通后重试" : (r.msg || "报价失败")); }
}
```

`renderResult(data)` 显示产品名 `productName`、渠道 `channel`、总价 `price`（EUR）、明细表 `priceDetail[]`（code/name/price），附「复制报价」按钮（把结果拼文本写剪贴板）。`renderError` 显示红色提示条 + 重试。页面加载时调 `callTutu("/external/orders/v2/listProductAndService")` 填充高级项附加服务（demo 模式下返回空列表即可）。

- [ ] **Step 1: 写 HTML 骨架 + 配置区 + 地址库加载**

写完整 `.html`：`<!doctype html>`、中文界面、内联 CSS（简洁卡片式，参考既有看板风格，浅色底 + 主色块）、`<script src="address_book.js">`、CONFIG、空 `renderResult/renderError` 占位函数。双击打开，控制台无报错，地址库下拉能列出 99 条。

- [ ] **Step 2: 实现表单 + 校验 + buildQuotationRequest**

实现发货仓/目的地下拉+手动切换/货物行增删/日期/高级项折叠；`collectGoods()`、`currentDropAddress()`、`validateForm()`（必填 + 中文拦截）。在演示模式下点「计算报价」，`buildQuotationRequest()` 返回结构正确（可临时 `console.log(JSON.stringify(req))` 验证字段齐全、国家为 2 位码、无中文字段值）。

- [ ] **Step 3: 实现网络层 + 结果/错误渲染 + 演示模式闭环**

接通 `onQuote` 全流程：演示模式下点「计算报价」→ 出「零担卡派（演示）/ 320 EUR / 明细两条」；复制按钮可用。切 `DEMO_MODE=false` 且 key 未开通时 → 显示「秘钥未开通权限」提示条。

- [ ] **Step 4: 手工验证（Playwright）**

用 Playwright 打开 `file:///C:/Users/LD1621/Desktop/尾程卡派询价方案/卡派询价工具.html`：确认地址库下拉 99 条可搜索、默认货物行正确、演示模式报价渲染、复制按钮、错误提示均正常。

- [ ] **Step 5: Commit**

```bash
git add "卡派询价工具.html"
git commit -m "feat: 途兔卡派询价工具 — 单文件 HTML 直连报价 API（含演示模式）"
```

---

### Task 3: 更新脚本入口 + README

**Files:**
- Create: `更新地址库.bat`
- Create: `README.md`

**Interfaces:**
- Consumes: `extract_address_book.py`
- Produces: 运营可双击重生成 `address_book.js` 的一键入口 + 使用说明。

- [ ] **Step 1: 写 `更新地址库.bat`**

```bat
@echo off
chcp 65001 >nul
cd /d "%~dp0"
python extract_address_book.py
pause
```

- [ ] **Step 2: 写 `README.md`**

内容：工具用途；`卡派询价工具.html` 双击即用；`address_book.js` 由 `YOKEE-车行询价.xlsx` 生成，改完表双击 `更新地址库.bat`；`DEMO_MODE` 说明（演示/真实切换）；分享时 `.html` + `address_book.js` 同目录；`Api-Key` 开通权限与正式环境 URL 待办。

- [ ] **Step 3: 终验**

双击 `更新地址库.bat` 能重生成 `address_book.js`（99 条不变）；README 与工具实际行为一致。

- [ ] **Step 4: Commit**

```bash
git add 更新地址库.bat README.md
git commit -m "docs: 询价工具使用说明 + 一键更新地址库入口"
```

---

## Self-Review 记录

- **Spec 覆盖**：①配置区→Task2 模块1；②地址库→Task1+Task2 模块2；③表单与字段映射→Task2 模块3/5；④数据流→Task2 模块4/5；⑤错误处理→Task2 模块5（`暂无权限`/网络/中文校验）；⑥测试演示模式→Task2 模块4/Step4；⑦前置（key 开通）→Global Constraints + README。
- **占位符扫描**：无 TBD/TODO；代码块均含真实实现。
- **类型一致性**：`ADDRESS_BOOK` 条目字段 `{id,label,country,countryName,city,postCode,addressLine,companyName}` 在 Task1 生成与 Task2 `applyAddress` 消费一致；`callTutu` 返回 `{code,msg,data}` 与 `onQuote` 判 `r.code===0 && r.data` 一致。
