# 物流中心 DAP 成本模型

## 文件结构

```
物流成本模型/
├── build_all.py              # 主脚本：从 full_table.json 生成全部 HTML
├── full_table.json            # 数据源：从在线表格导出
├── 成本云图_G系列_M系列.html  # 输出：气泡云图 + 德/美分线卡片
└── 物流中心费用_汇报.html     # 输出：德国路线汇总 + 成本结构柱状图
```

## 使用方法

### 1. 更新数据

从物流中心费用汇总在线表格导出 `full_table.json`，替换本目录下的同名文件。

### 2. 生成报告

```bash
python build_all.py
```

### 3. 查看结果

用浏览器打开：
- `成本云图_G系列_M系列.html` — G/M/N 系列气泡云图 + 德国/美国分线对比卡片
- `物流中心费用_汇报.html` — DAP 德国路线汇总表 + 成本结构柱状图 + KPI

## 数据映射规则 (2026-08-04)

| 费用项 | C端谷仓 | B端中转 | 美东/美西 |
|--------|---------|---------|-----------|
| A 头程 | col[7]+col[8]+col[11] | 同 | 同 |
| B 上架 | col[13] | col[15] | C端优先 |
| C 仓储 | col[17] | col[18] | C端优先 |
| D 出库 | col[20] | col[19] | C端优先 |
| E 尾程 | col[21] (快递) | col[24] (卡车) | C端优先 |

## 定期更新

将在线成本表维护好后，导出 JSON → 替换 `full_table.json` → 运行 `build_all.py` → 上传 HTML 到 GitHub Pages 或直接分发。

## GitHub 上传

```bash
git add .
git commit -m "更新物流成本模型"
git push
```
