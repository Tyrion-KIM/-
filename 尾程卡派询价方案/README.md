# 卡派询价工具

内部运营询价工具：选定「目的地车行 + 货物」，返回尾程卡车派送报价（Groupage / LTL）。

当前有**两个版本**，数据源都是 `YOKEE-车行询价.xlsx`（途兔季度价卡，99 个车行、25 国）：

| 文件 | 版本 | 报价方式 | 状态 |
|---|---|---|---|
| `卡派询价工具-测试版V2.html` | **测试版 V2** | **本地查价卡**（目的地 × 托盘数） | ✅ 现在就能用 |
| `卡派询价工具.html` | V1 | 直连途兔实时报价 API | ⏳ 等 `Api-Key` 开通 |

---

## 测试版 V2（本地查表 · 推荐先用）

不依赖 API，直接查 `YOKEE-车行询价.xlsx` 里的季度价卡。报价逻辑：**选目的地 → 填托盘数（1–33）→ 查那一行那一列的价格**。

1. 双击 **`卡派询价工具-测试版V2.html`**（本地浏览器即开，无需部署）。
2. `② 目的地` 搜索 / 选择车行 → `③ 托盘数量` 填几托 → 点「计算报价」。
3. 结果区显示：**运输总价（EUR）** + 公路距离 + 拼车/整车时效 + 备注，可「复制报价」。

要点：

- **仅支持价卡内 99 个车行**，不支持手动输入表外新地址（表外无报价）。
- 价卡按「托盘数」定价，重量/尺寸不影响价格；标准托盘 120×80×200 cm · 240 kg/托。
- 数据里 **9 个目的地无报价**（5 个备注「无服务」：美/英×2/瑞士/挪威/爱尔兰；另 4 个价卡留空），选中会明确提示「暂无报价」。
- 1 个目的地（FPL Trading，立陶宛）只报满 6 托，其余 89 个满 33 托。
- 依赖 `price_book.js`，与 HTML 放同一目录。

## V1（直连 API · 待开通）

选定目的地 + 货物，直连途兔报价 API 实时返回报价（含手动输入任意地址）。

- 双击 `卡派询价工具.html`；依赖 `address_book.js`。
- 当前默认 `DEMO_MODE: true`（返回本地假报价，随目的地/货物变化），因为 `Api-Key` 尚未在途兔侧开通。
- 开通后：把 `CONFIG.DEMO_MODE` 改 `false`，并替换 `API_BASE`（正式环境 URL）与 `API_KEY`。

---

## 数据更新（两个版本共用）

`address_book.js`（V1 地址库）与 `price_book.js`（V2 报价库）都由 `YOKEE-车行询价.xlsx` 自动生成。

- 数据源是 `YOKEE-车行询价.xlsx` 的「询价主表」sheet（**请勿改结构**，只改表格内容）。
- 改完表后双击 **`更新地址库.bat`**（需本机 Python 3 + `openpyxl`），会同时重生成两个 js。

脚本：`extract_address_book.py`、`extract_price_book.py`；单测：`test_extract_address_book.py`（`python -m unittest test_extract_address_book`）。

## 待办

1. 途兔侧开通 `Api-Key` 权限（当前「暂无权限」），V1 即可联调。
2. 拿正式环境 Base URL。
3. （可选）补充 9 个无报价车行 / 各目的地真实联系人。

## 文件清单

```
尾程卡派询价方案/
├── YOKEE-车行询价.xlsx             # 唯一数据源，勿改结构
├── extract_address_book.py         # xlsx → address_book.js（V1 地址库）
├── extract_price_book.py           # xlsx → price_book.js（V2 报价库）
├── test_extract_address_book.py    # 抽取脚本单测
├── address_book.js                 # 生成物（99 条地址）
├── price_book.js                   # 生成物（99 条 × 33 档托盘价）
├── 卡派询价工具-测试版V2.html      # V2 本地查表询价（推荐先用）
├── 卡派询价工具.html               # V1 直连 API 询价
├── 更新地址库.bat                  # 一键重生成两个 js
└── README.md
```
