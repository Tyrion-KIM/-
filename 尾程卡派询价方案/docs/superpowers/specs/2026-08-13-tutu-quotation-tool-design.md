# 途兔卡派内部询价工具 — 设计文档

日期：2026-08-13
状态：待复审

## 1. 背景与目标

内部运营团队需要为「车行（欧洲各汽车经销商）」做尾程卡车派送报价。目前报价依赖供应商（途兔卡派）提供的季度静态价卡（`YOKEE-车行询价.xlsx`），运营需手工查表。

目标：做一个**单文件 HTML 内部工具**，运营选定目的地 + 货物，工具直接调用途兔卡派官方报价 API，实时返回报价。用途兔 API 作为「后端资源库」，前端作为内部产品。

范围：**MVP 只做「获取产品及服务 + 询价」两个接口**。创建订单 / 轨迹 / 取消订单不在本期。

## 2. 现状

### 2.1 途兔卡派 API（V2）

- 沙箱 Base URL：`http://test.teknihall-trucking.com:8080/api`；正式环境 URL 待销售经理提供。
- 鉴权：请求头 `Api-Key`。
- 业务范围：Groupage（零担）+ LTL（零担卡派）。
- **CORS 已确认开放**：`Access-Control-Allow-Origin: *`，浏览器可直接跨域调用。
- **前置**：当前 `Api-Key` 返回 `{"code":500,"msg":"暂无权限，请联系相关人员开通"}`，需先在途兔侧开通 API 权限后方可联调。

### 2.2 询价接口 `POST /external/orders/v2/quotation`

入参 `ApiOrderQuotationRequestV2`：

| 字段 | 必填 | 说明 |
|---|---|---|
| `pickAddress` | ✅ | 提货地址（`ApiAddressInfoV2`） |
| `dropAddress` | ✅ | 卸货地址（`ApiAddressInfoV2`） |
| `goodsInfoList` | ✅ | 货物列表（`ApiGoodsInfoV2[]`） |
| `pickDate` | ✅ | 拣货日期 `yyyy-MM-dd` |
| `serviceCodes` | 可选 | 附加服务编码列表 |
| `productCode` | 可选 | 固定产品编码；留空则自动取最低价 |
| `valueOfGoods` | 可选 | 货值 |
| `packageExchangeQuantity` | 可选 | 托盘交换数量 |

地址 `ApiAddressInfoV2` 必填：`contactPerson / contactEmail / contactPhone / phonePrefix / addressLine / country(2位) / city / postCode / isPrivate`（均不能含中文）；`companyName` 可选（私人地址可为空）。

货物 `ApiGoodsInfoV2` 必填：`packageTypeCode(FP欧托/HP半托/KT纸箱/EP一次性托/KI木箱) / weight / length / width / height / packageUnit / stackable / goodsName / isDangerous`。

返回 `ApiOrderQuotationResponseV2`：`productCode / productName / channel / price / priceDetail[{code,price,name}]`。

### 2.3 基础数据（`YOKEE-车行询价.xlsx`）

- **固定发货仓**（sheet「填写说明与货件参数」）：德国自营仓 Neuss —— ANTHBOT GER GMBH，Bussardweg 4, 41468 Neuss, Germany；电话 +49-(0)15223942230。
- **目的地地址库**（sheet「询价主表」）：99 个车行，25 国（丹麦22/德国18/荷兰7/立陶宛6/比利时6/瑞典5/波兰5/…），字段：`国家(中英)/邮编/城市/详细街道地址/公司名称/公路距离`。部分行公司名称为空。
- **标准货物**（sheet1 货件参数）：托盘 120×80×200cm、240kg/托；单件产品 67×47×33cm、23kg。

## 3. 架构（方案 A：单文件 HTML 直连）

交付物：`尾程卡派询价方案\卡派询价工具.html`（单文件，零部署，双击即开）。

文件内分 5 块，各自独立：

| 模块 | 作用 | 转 C 时 |
|---|---|---|
| ① 配置区（顶部） | `API_BASE`、`API_KEY`、`ORIGIN`、`DEFAULT_CONTACT`、`ADDRESS_BOOK` | key/base 改指向自家后端 |
| ② 地址库 | 99 目的地 JSON + 固定发货仓 | 不动 |
| ③ 表单 | 输入区（见 §4） | 不动 |
| ④ `callTutu(path, body)` | 唯一碰网络的函数，拼 `Api-Key` 头 + fetch | **只换这层** |
| ⑤ 结果展示 | 报价渲染 | 不动 |

**转 C 预留**：`callTutu` 是唯一网络出口。迁移时将其实现从「直连途兔」改为「调自家后端」，其余代码零改动。

## 4. 表单与字段映射

### 4.1 表单

- **发货仓**：默认锁定 Neuss（可点开改）。
- **目的地**：99 车行**搜索下拉**（按国家/城市/邮编过滤）+ 「手动输入」切换（国家下拉 2 位码 / 城市 / 邮编 / 街道 / 联系人等，含中文校验）。
- **货物**：默认「1 托 · 120×80×200cm · 240kg · FP欧托 · 可堆叠」，件数/尺寸/重量/包装类型/堆叠/品名/危险品可改，支持多行。
- **拣货日期**：默认今天。
- **高级项（折叠）**：附加服务（来自「获取产品及服务」）、固定产品编码、货值、托盘交换数量。

### 4.2 xlsx → API 字段映射

| xlsx 列 | API 字段 | 备注 |
|---|---|---|
| 国家（英文名） | `country` | 转 2 位码（Austria→AT…United Kingdom→GB，25 国全映射） |
| 邮编 | `postCode` | |
| 城市 | `city` | |
| 详细街道地址 | `addressLine` | |
| 公司名称 | `companyName` | 可为空 |
| （发货仓 sheet1） | `contactPerson/contactPhone/phonePrefix` | 默认联系人 |

### 4.3 联系人字段兜底

目的地表无联系人信息，接口又要求非空。方案：配置区 `DEFAULT_CONTACT` 统一兜底——`contactPerson`=ANTHBOT GER GMBH、`phonePrefix`=+49、`contactPhone`=15223942230；`contactEmail` 发货仓表里为空，先放配置区一个占位（`DEFAULT_CONTACT.contactEmail`，运营可填一个公司公共邮箱）。表单可逐单改。报价不受联系人影响。

> 待验证：接口对「必填联系人字段为空」的实际容忍度。若空邮箱被拒，则回退为强制填默认邮箱。

### 4.4 下拉显示

空公司名的目的地，下拉标题用「城市 + 邮编」；非空用公司名称。

## 5. 数据流

表单 → 拼 `ApiOrderQuotationRequestV2` JSON → `callTutu('/external/orders/v2/quotation', body)` → `{productName, channel, price, priceDetail[]}` → 结果页显示「产品名 + 渠道 + 总价 + 明细表 + 复制报价」。

页面加载时额外调一次 `GET /external/orders/v2/listProductAndService` 填充高级项的附加服务列表。

## 6. 错误处理

| 场景 | 处理 |
|---|---|
| `code≠0` 或 `暂无权限` | 中文友好提示（「秘钥未开通权限，请联系途兔销售经理」） |
| 网络失败 / CORS / 超时 | 友好提示 + 重试按钮 |
| 手动输入含中文 | 当场拦截标红 |
| 必填项缺失 | 提交前校验并高亮 |

## 7. 测试

- **演示模式**：内置 mock 报价开关，key 未开通前先验 UI 与字段拼装。
- **真实联调**：key 开通后切换真实调用，验证报价正确性。

## 8. 前置条件 / 待办

1. 途兔侧开通 `Api-Key` 权限（当前「暂无权限」）。
2. 拿正式环境 Base URL。
3. 运营后续补充目的地缺失的联系人（可选，非阻塞）。
