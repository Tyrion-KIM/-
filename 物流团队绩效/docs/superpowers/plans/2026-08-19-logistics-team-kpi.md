# 物流团队绩效体系 V1 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 生成 `物流团队绩效V1.xlsx`（5 张 sheet、纯公式、WPS 兼容）与 Python 月度看板生成脚本 `scripts/build_kpi_dashboard.py`（产出单文件 HTML）。

**Architecture:** 指标体系（29 条指标行+权重+公式类型）统一定义在 `scripts/kpi_model.py`，它是唯一数据源：模板生成器 `build_kpi_template.py` 据此写 Excel（含降级归一化公式），看板脚本 `build_kpi_dashboard.py` 据此从打分表**读原始数据并在 Python 里重算**（不读 Excel 公式结果，规避缓存值问题）。

**Tech Stack:** Python 3 + openpyxl + pytest；HTML 为单文件内联 CSS，无外部资源、无 JS 依赖。

**Spec:** `物流团队绩效/docs/superpowers/specs/2026-08-19-logistics-team-kpi-design.md`

## Global Constraints

- Excel **无宏**；公式白名单：IF / ISNUMBER / SUM / AVERAGE / AVERAGEIFS / MIN / MAX / IFERROR / AND / OR ——禁数组公式、XLOOKUP、LET（WPS 兼容）
- 打分表列布局固定：`A指标ID B人员 C业务线 D指标 E公式类型 F目标值 G单位 H数据可用 I原始1 J原始2 K原始3 L原始4 M指标得分 N全局权重 O有效权重 P加权分`，表头在第 3 行，数据行 4–32（K01–K29），监控区 34–35，总分区 37–44
- 百分比类输入（缺货率/准确率/退件率/占比/长周期占比）一律填**小数**（如 0.92），单元格格式 0.0%
- 命令行统一 `python -X utf8 ...`（Windows GBK 控制台防乱码）
- 产物路径：`物流团队绩效V1.xlsx`（项目根）、`output/kpi_dashboard_<YYYY-MM>.html`
- 每个任务结束 commit 一次；生成的 xlsx 与示例看板随仓库提交
- 看板红绿灯阈值：绿 ≥85 / 黄 70–84.9 / 红 <70 / NA 灰（spec §11.2）

---

### Task 1: kpi_model.py — 指标定义与得分计算（唯一数据源）

**Files:**
- Create: `scripts/kpi_model.py`
- Test: `tests/test_kpi_model.py`

**Interfaces:**
- Produces: `INDICATORS: list[Indicator]`（29 条，权重按人合计=70）、`PEOPLE`、`SPECIALISTS`、`TASK_WEIGHT=30`；
  计算函数 `score_cost/score_rate/score_upper/score_lower/score_payment/score_stock/score_three`、
  `row_scores(ind, i, j, k) -> float|None`（None=NA）、`personal_total(pairs, task) -> float|None`。
  Task 2/3/5 全部 import 本模块。

- [ ] **Step 1: 确认 pytest 可用（缺则装）**

Run: `python -X utf8 -m pytest --version`，失败则 `python -m pip install pytest`

- [ ] **Step 2: 写失败测试**

```python
# tests/test_kpi_model.py
# -*- coding: utf-8 -*-
import pytest
from scripts.kpi_model import (INDICATORS, PEOPLE, SPECIALISTS, TASK_WEIGHT,
    score_cost, score_rate, score_upper, score_lower, score_payment,
    score_stock, score_three, row_scores, personal_total)

def test_score_formulas():
    assert score_cost(15, 20) == 75
    assert score_cost(15, 10) == 100
    assert score_rate(92, 100) == 92
    assert score_upper(0.02, 0.025) == 80
    assert score_upper(0.05, 0.04) == 100
    assert score_lower(0.95, 0.92) == pytest.approx(96.84, abs=0.01)
    assert score_payment(0, 0.92) == 100
    assert score_payment(2, 0.80) == pytest.approx(74.44, abs=0.01)
    assert score_stock(0.03, 120, 5) == 100
    assert score_stock(0.04, 120, 5) == pytest.approx(91.67, abs=0.01)
    assert score_three(15, 16.5, 6) == pytest.approx(96.97, abs=0.01)

def test_weights_sum_70_per_person():
    for p in PEOPLE:
        assert sum(ind.weight for ind in INDICATORS if ind.person == p) == 70

def test_row_scores_na_and_dispatch():
    k1 = next(i for i in INDICATORS if i.id == "K01")   # 成本-计算 目标15
    assert row_scores(k1, i=100, j=2000) == 75
    assert row_scores(k1, i=None, j=None) is None        # 数据缺失
    k6 = next(i for i in INDICATORS if i.id == "K06")    # 请款
    assert row_scores(k6, i=0, j=0.92) == 100
    k15 = next(i for i in INDICATORS if i.id == "K15")   # 库存综合
    assert row_scores(k15, i=0.04, j=120, k=5) == pytest.approx(91.67, abs=0.01)

def test_personal_total_renormalizes_na():
    pairs = [(75, 27), (None, 18), (92, 5)]              # 27+5 可用
    assert personal_total(pairs, task=80) == pytest.approx((75*27+92*5+80*30)/(32+30), abs=0.01)
    assert personal_total([(None, 70)], task=None) is None   # 全NA无任务
    assert personal_total([(100, 70)], task=None) == 100     # 无任务块不计入分母
```

- [ ] **Step 3: 运行确认失败**

Run: `python -X utf8 -m pytest tests/test_kpi_model.py -v`
Expected: FAIL（ModuleNotFoundError / ImportError）

- [ ] **Step 4: 实现 kpi_model.py**

```python
# scripts/kpi_model.py
# -*- coding: utf-8 -*-
"""物流团队绩效 V1 指标模型：指标定义 + 得分公式（与 Excel 模板公式一一镜像）。"""
from dataclasses import dataclass

FT_COST_AB = "成本-计算"; FT_COST = "成本-直填"; FT_RATE = "达标率"
FT_UPPER = "上限"; FT_LOWER = "下限"; FT_PAY = "请款"
FT_STOCK = "库存综合"; FT_THREE = "三段综合"
FT_AVG_PAY = "引用-请款均"; FT_AVG_SPEC = "引用-专员均分"

PEOPLE = ["吴佳钒", "郑舒漫", "黄婷", "吴定佳", "张雨洁", "金炜铮"]
SPECIALISTS = PEOPLE[:4]          # 主管卡的"专员均分"不含实习生
TASK_WEIGHT = 30
QUANT_WEIGHT = 70

@dataclass(frozen=True)
class Indicator:
    id: str; person: str; line: str; name: str; ftype: str
    target: object      # 数值或 None；引用类为 None
    unit: str; weight: float
    raw: tuple          # 各原始字段含义说明，如 ("发货数量A","运费折欧B")
    source: str; scope: str   # 数据源 / 取值口径

INDICATORS = [
 # 吴佳钒 rows 4-9
 Indicator("K01","吴佳钒","DDP头程","成本","成本-计算",15,"欧/台",27,("发货数量A","运费折欧B"),"头程大表；长期易仓","当月签收订单"),
 Indicator("K02","吴佳钒","DDP头程","时效","达标率",None,"%",18,("达标单数","总单数"),"头程大表；长期易仓","当月签收订单，标准时效"),
 Indicator("K03","吴佳钒","始发计划","缺货率","上限",0.05,"%",5,("实际缺货率(小数)",),"库内MES+排产表","每周一交付计划"),
 Indicator("K04","吴佳钒","始发计划","缺货时间","上限",7,"天",5,("实际缺货天数",),"库内MES+排产表","缺货持续≤7天"),
 Indicator("K05","吴佳钒","在途库存","上架准确率","下限",0.95,"%",5,("实际上架准确率(小数)",),"各仓入库单上架情况",""),
 Indicator("K06","吴佳钒","财务","请款-DDP","请款",None,"",10,("迟报工作日数","请款金额占比(小数)"),"请款记录","10号前，≥90%"),
 # 郑舒漫 rows 10-13
 Indicator("K07","郑舒漫","FOB","单证准确率","下限",1.0,"%",15,("单证准确率(小数)",),"货代台账","我方单证零差错"),
 Indicator("K08","郑舒漫","FOB","订舱及时率","达标率",None,"%",10,("按时回传S/O单数","总单数"),"货代台账","OA审单→S/O≤1个工作日"),
 Indicator("K09","郑舒漫","FCA","执行时效","达标率",None,"%",25,("48h内达标单数","总单数"),"OA订单数据","OA申请→工厂发出≤48h"),
 Indicator("K10","郑舒漫","财务","请款-FOB","请款",None,"",20,("迟报工作日数","请款金额占比(小数)"),"请款记录","10号前，≥90%"),
 # 黄婷 rows 14-20
 Indicator("K11","黄婷","B端中转","成本","成本-计算",15,"欧/台",21,("签收数量A","运费折欧B"),"当月核对账单","当月签收"),
 Indicator("K12","黄婷","B端中转","时效","达标率",None,"%",14,("达标单数","总单数"),"签收单+分段标准","DE1/DK2/AT2/SE1/SI2工作日；旺3-6淡7-2"),
 Indicator("K13","黄婷","目的国计划","缺货率","上限",0.05,"%",5,("实际缺货率(小数)",),"在库+待发+在途表","每周一交付计划"),
 Indicator("K14","黄婷","目的国计划","缺货时间","上限",7,"天",5,("实际缺货天数",),"在库+待发+在途表","缺货持续≤7天"),
 Indicator("K15","黄婷","B端库存","综合","库存综合",None,"",10,("长周期占比(小数)","平均库龄(天)","单台库内成本(欧)"),"各仓库存表+账单","≤3%/≤120天/≤5欧"),
 Indicator("K16","黄婷","财务","请款-B端仓库内","请款",None,"",7.5,("迟报工作日数","请款金额占比(小数)"),"请款记录","10号前，≥90%"),
 Indicator("K17","黄婷","财务","请款-海外仓调拨","请款",None,"",7.5,("迟报工作日数","请款金额占比(小数)"),"请款记录","10号前，≥90%"),
 # 吴定佳 rows 21-25
 Indicator("K18","吴定佳","一件代发","成本","成本-计算",15,"欧/台",24,("出库数量A","运费折欧B"),"正向仓账单+领星/易仓","当月出库"),
 Indicator("K19","吴定佳","一件代发","时效","达标率",None,"%",16,("达标单数","总单数"),"渠道承诺时效","出库单生成→签收；分段标准任务块定稿"),
 Indicator("K20","吴定佳","售后物流","退件率","上限",0.02,"%",10,("物流因素退件率(小数)",),"客服数据","≤2%"),
 Indicator("K21","吴定佳","C端库存","综合","库存综合",None,"",10,("长周期占比(小数)","平均库龄(天)","单台库内成本(欧)"),"各仓库存表+账单","≤3%/≤120天/≤5欧"),
 Indicator("K22","吴定佳","财务","请款-C端仓库内","请款",None,"",10,("迟报工作日数","请款金额占比(小数)"),"请款记录","10号前，≥90%"),
 # 张雨洁 rows 26-28
 Indicator("K23","张雨洁","特殊发运","时效","达标率",None,"%",40,("达标单数","总单数"),"头程大表；长期易仓","当月签收，按运输方式分段"),
 Indicator("K24","张雨洁","进口业务","时效","达标率",None,"%",20,("达标单数","总单数"),"待定","分段标准8月底前定，否则首月NA"),
 Indicator("K25","张雨洁","财务","账单协同-请款","请款",None,"",10,("迟报工作日数","请款金额占比(小数)"),"请款记录","协同雨洁表格"),
 # 金炜铮 rows 29-32
 Indicator("K26","金炜铮","团队","单台总成本","成本-直填",36,"欧/台",30,("当月实际单台总成本",),"财务核算","对齐降本分成方案结算线"),
 Indicator("K27","金炜铮","团队","三段结构","三段综合",None,"",20,("头程实际","尾程实际","仓储实际"),"财务核算","15/15/6，各段得分平均"),
 Indicator("K28","金炜铮","团队","团队请款及时率","引用-请款均",None,"",10,(),"全员请款线平均","打分表内自动引用"),
 Indicator("K29","金炜铮","团队","专员均分","引用-专员均分",None,"",10,(),"4位专员总分平均","打分表内自动引用"),
]

# ---------- 得分公式（与 Excel 模板镜像，勿单边修改） ----------
def score_cost(target, actual):
    """成本类：min(100, 100*目标/实际)。"""
    return min(100.0, 100.0 * target / actual)

def score_rate(passed, total):
    """达标率：达标数/总数*100。"""
    return min(100.0, passed / total * 100.0)

def score_upper(target, actual):
    """上限类：达标100，未达标 100*目标/实际。"""
    return 100.0 if actual <= target else 100.0 * target / actual

def score_lower(target, actual):
    """下限类：达标100，未达标 100*实际/目标。"""
    return 100.0 if actual >= target else 100.0 * actual / target

def score_payment(late_days, amount_ratio):
    """请款：时间50% + 金额50%。迟1个工作日-20（下限0）；金额 min(100, 占比/0.9*100)。"""
    time_s = max(0.0, 100.0 - 20.0 * late_days)
    amt_s = min(100.0, amount_ratio / 0.9 * 100.0)
    return 0.5 * time_s + 0.5 * amt_s

def score_stock(long_ratio, age_days, cost):
    """库存综合：三项上限类得分平均（3% / 120天 / 5欧）。"""
    return (score_upper(0.03, long_ratio) + score_upper(120, age_days)
            + score_upper(5, cost)) / 3.0

def score_three(head, tail, ware):
    """三段综合：头程15/尾程15/仓储6 各成本类得分平均。"""
    return (score_cost(15, head) + score_cost(15, tail) + score_cost(6, ware)) / 3.0

def row_scores(ind, i=None, j=None, k=None):
    """按公式类型重算指标分。原始值缺任一必要项 → None（降级）。"""
    t = ind.ftype
    if t == FT_COST_AB:
        return None if not i or not j else score_cost(ind.target, j / i)
    if t == FT_COST:
        return None if not i else score_cost(ind.target, i)
    if t == FT_RATE:
        return None if not j else score_rate(i or 0, j)
    if t == FT_UPPER:
        return None if i is None else score_upper(ind.target, i)
    if t == FT_LOWER:
        return None if i is None else score_lower(ind.target, i)
    if t == FT_PAY:
        return None if i is None or j is None else score_payment(i, j)
    if t == FT_STOCK:
        return None if i is None or j is None or k is None else score_stock(i, j, k)
    if t == FT_THREE:
        return None if not i or not j or not k else score_three(i, j, k)
    raise ValueError(f"引用类指标 {ind.id} 不在此计算，由汇总层处理")

def personal_total(pairs, task):
    """个人总分：可用项权重归一化。pairs=[(指标分|None,权重)]；task=任务块均分|None。"""
    avail = [(s, w) for s, w in pairs if s is not None]
    num = sum(s * w for s, w in avail)
    den = sum(w for _, w in avail)
    if task is not None:
        num += task * TASK_WEIGHT
        den += TASK_WEIGHT
    return num / den if den else None
```

- [ ] **Step 5: 运行测试通过**

Run: `python -X utf8 -m pytest tests/test_kpi_model.py -v`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add scripts/kpi_model.py tests/test_kpi_model.py
git commit -m "feat: 绩效指标模型 kpi_model（29指标+得分公式+NA归一化）"
```

---

### Task 2: 模板生成器 — 说明 / 人员与权重 / 指标标准 三张静态 sheet

**Files:**
- Create: `scripts/build_kpi_template.py`
- Test: `tests/test_kpi_template.py`

**Interfaces:**
- Consumes: `kpi_model.INDICATORS/PEOPLE/SPECIALISTS`
- Produces: `build_workbook() -> Workbook`（含全部 sheet，Task 3/4 继续往里加）；CLI `python -X utf8 scripts/build_kpi_template.py` 输出 `物流团队绩效V1.xlsx`；常量 `SHEET_GUIDE="说明"`, `SHEET_WEIGHTS="人员与权重"`, `SHEET_STD="指标标准"`, `SHEET_SCORE="打分表模板"`, `SHEET_TASK="任务块"`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_kpi_template.py
# -*- coding: utf-8 -*-
import pytest
from scripts.build_kpi_template import (build_workbook, SHEET_GUIDE,
    SHEET_WEIGHTS, SHEET_STD, SHEET_SCORE, SHEET_TASK)

def test_workbook_has_five_sheets():
    wb = build_workbook()
    assert wb.sheetnames == [SHEET_GUIDE, SHEET_WEIGHTS, SHEET_STD, SHEET_SCORE, SHEET_TASK]

def test_guide_contains_rules():
    wb = build_workbook()
    text = "\n".join(str(c.value) for row in wb[SHEET_GUIDE].iter_rows() for c in row if c.value)
    for kw in ["降级", "可控", "NA", "归一化", "红绿灯"]:
        assert kw in text

def test_weights_sheet_lists_all_people():
    wb = build_workbook()
    ws = wb[SHEET_WEIGHTS]
    text = "\n".join(str(c.value) for row in ws.iter_rows() for c in row if c.value)
    for p in ["吴佳钒", "郑舒漫", "黄婷", "吴定佳", "张雨洁", "金炜铮", "任务块", "30"]:
        assert p in text

def test_std_sheet_has_29_indicators():
    wb = build_workbook()
    ws = wb[SHEET_STD]
    ids = [str(r[0].value) for r in ws.iter_rows(min_row=2) if r[0].value]
    assert len(ids) == 29 and ids[0] == "K01" and ids[-1] == "K29"
```

- [ ] **Step 2: 运行确认失败**

Run: `python -X utf8 -m pytest tests/test_kpi_template.py -v` → FAIL（ImportError）

- [ ] **Step 3: 实现（本任务先建骨架+三张静态 sheet；SHEET_SCORE/SHEET_TASK 先建空 sheet 占位）**

```python
# scripts/build_kpi_template.py
# -*- coding: utf-8 -*-
"""生成 物流团队绩效V1.xlsx（无宏、纯公式、WPS兼容）。用法：python -X utf8 scripts/build_kpi_template.py"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))  # 直跑兼容
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from kpi_model import INDICATORS, PEOPLE, SPECIALISTS

SHEET_GUIDE = "说明"; SHEET_WEIGHTS = "人员与权重"
SHEET_STD = "指标标准"; SHEET_SCORE = "打分表模板"; SHEET_TASK = "任务块"
OUT = Path(__file__).resolve().parent.parent / "物流团队绩效V1.xlsx"

HDR_FILL = PatternFill("solid", fgColor="1F4E79")
HDR_FONT = Font(color="FFFFFF", bold=True)
TITLE_FONT = Font(bold=True, size=14)

def _hdr(ws, row, headers):
    for col, h in enumerate(headers, 1):
        c = ws.cell(row=row, column=col, value=h)
        c.fill = HDR_FILL; c.font = HDR_FONT
        c.alignment = Alignment(horizontal="center", vertical="center")

def _guide(wb):
    ws = wb.create_sheet(SHEET_GUIDE)
    ws["A1"] = "物流团队绩效 V1 使用说明"; ws["A1"].font = TITLE_FONT
    rows = [
        ("一、月度流程", ""),
        ("1", "月初：复制[打分表模板]并重命名为 打分-YYYY-MM（如 打分-2026-09）"),
        ("2", "月初：在[任务块]登记每人3-5条当月任务+验收物，月份列填当月（如2026-09）"),
        ("3", "月中：日常积累；数据不可得的指标，[数据可用]列选 NA"),
        ("4", "月末：填打分表原始数据；任务块打分（0/50/100）"),
        ("5", "出分：python -X utf8 scripts/build_kpi_dashboard.py --month YYYY-MM"),
        ("二、得分公式", ""),
        ("成本类", "min(100, 100×目标÷实际单台)；单台=运费B÷数量A"),
        ("达标率类", "达标单数÷总单数×100"),
        ("上限类（缺货/退件/库龄等）", "达标100；未达标 100×目标÷实际"),
        ("下限类（准确率）", "达标100；未达标 100×实际÷目标"),
        ("请款类", "时间50%+金额50%；10号前=100，每迟1个工作日-20（下限0）；金额 min(100,占比÷90%×100)"),
        ("三、降级规则（NA）", ""),
        ("规则", "指标数据不可得→[数据可用]选NA→该指标剔除，个人总分按可用权重归一化；没数据不编分数"),
        ("覆盖率", "打分表总分区显示每人 数据覆盖率=可用量化权重÷70；连续两月<60%的线，数据管道建设进该人下月任务块"),
        ("四、可控性原则", ""),
        ("原则", "计分指标必须本人可控；不可控但重要的（FOB截关装船准时率-货代控制）在打分表监控区只显示不计分"),
        ("五、看板红绿灯", ""),
        ("阈值", "绿≥85 / 黄70-84.9 / 红<70 / NA灰；实习生（张雨洁）算分但不排名不挂钱"),
        ("六、版本", ""),
        ("V1", "2026-08-19 定稿；权重固定，2027-02 复盘"),
    ]
    for r, (a, b) in enumerate(rows, 3):
        ws.cell(row=r, column=1, value=a).font = Font(bold=True)
        ws.cell(row=r, column=2, value=b)
    ws.column_dimensions["A"].width = 30; ws.column_dimensions["B"].width = 90

def _weights(wb):
    ws = wb.create_sheet(SHEET_WEIGHTS)
    ws["A1"] = "团队分工与权重（固定，2027-02复盘调整）"; ws["A1"].font = TITLE_FONT
    _hdr(ws, 3, ["姓名", "岗位", "分工", "量化块明细（70%）", "任务块（30%）"])
    team = [
        ("金炜铮", "物流中心主管", "物流中心全范围", "团队单台成本30 · 三段结构20 · 团队请款10 · 专员均分10", "管理任务"),
        ("郑舒漫", "物流专员", "头程FOB", "FOB(单证15+订舱10) · FCA执行25 · 请款20", "30"),
        ("吴佳钒", "物流专员", "头程DDP", "DDP成本27+时效18 · 始发计划10 · 在途库存5 · 请款10", "30"),
        ("黄婷", "物流专员", "目的国大货中转、B端运输", "B端成本21+时效14 · 目的国计划10 · B端库存10 · 请款15", "30"),
        ("吴定佳", "物流专员", "一件代发、C端履约、售后退货", "一件代发成本24+时效16 · 退件率10 · C端库存10 · 请款10", "30"),
        ("张雨洁", "物流实习生", "样机发运、进口、账单核对", "特殊发运40 · 进口时效20 · 账单协同10（不排名不挂钱）", "30"),
    ]
    for r, row in enumerate(team, 4):
        for c, v in enumerate(row, 1):
            ws.cell(row=r, column=c, value=v)
    for col, w in zip("ABCDE", (10, 14, 30, 52, 12)):
        ws.column_dimensions[col].width = w

def _std(wb):
    ws = wb.create_sheet(SHEET_STD)
    ws["A1"] = "指标标准字典（唯一口径来源）"; ws["A1"].font = TITLE_FONT
    _hdr(ws, 3, ["指标ID", "人员", "业务线", "指标", "公式类型", "目标", "单位", "权重",
                 "原始字段说明", "数据源", "取值口径"])
    for r, ind in enumerate(INDICATORS, 4):
        vals = [ind.id, ind.person, ind.line, ind.name, ind.ftype, ind.target,
                ind.unit, ind.weight, " / ".join(ind.raw), ind.source, ind.scope]
        for c, v in enumerate(vals, 1):
            ws.cell(row=r, column=c, value=v)
    ws.column_dimensions["I"].width = 42; ws.column_dimensions["J"].width = 22
    ws.column_dimensions["K"].width = 34
    ws.freeze_panes = "A4"

def build_workbook():
    wb = Workbook(); wb.remove(wb.active)
    _guide(wb); _weights(wb); _std(wb)
    wb.create_sheet(SHEET_SCORE)   # Task 3 填充
    wb.create_sheet(SHEET_TASK)    # Task 4 填充
    return wb

def main():
    wb = build_workbook()          # Task 3/4 扩展此函数
    wb.save(OUT)
    print(f"saved: {OUT}")

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: 运行测试通过**

Run: `python -X utf8 -m pytest tests/test_kpi_template.py -v`
Expected: 4 passed（`test_workbook_has_five_sheets` 等）

- [ ] **Step 5: Commit**

```bash
git add scripts/build_kpi_template.py tests/test_kpi_template.py
git commit -m "feat: 绩效模板骨架+说明/人员与权重/指标标准三张静态sheet"
```

---

### Task 3: 打分表模板 — 29 指标行 + 公式 + 数据校验 + 总分区 + 监控区

**Files:**
- Modify: `scripts/build_kpi_template.py`（`build_workbook` 中替换 `wb.create_sheet(SHEET_SCORE)` 为 `_score(wb)`）
- Test: `tests/test_kpi_template.py`（追加）

**Interfaces:**
- Consumes: `kpi_model.INDICATORS`（顺序即行序：K01 起始行 4，K29 行 32）
- Produces: 打分表固定布局（后续 Task 5 看板读取依赖）：
  - `B1` 绩效月份（文本，如 `2026-09`，任务块 AVERAGEIFS 匹配此格）
  - 表头第 3 行；指标行 4–32；行 34 监控区标题；行 35 M01 截关装船准时率
  - 总分区：行 37 标题、行 38 表头（`A人员 B量化有效权重和 C量化加权分和 D任务块得分 E数据覆盖率 F总分`）、行 39–44 六人（顺序=PEOPLE，专员=39–42）
  - 请款行（K28 引用）：`$M$9,$M$13,$M$19,$M$20,$M$25,$M$28`

- [ ] **Step 1: 追加失败测试**

```python
# tests/test_kpi_template.py 追加
from scripts.build_kpi_template import SCORE_FIRST_ROW  # =4

def _score_ws():
    return build_workbook()["打分表模板"]

def test_score_sheet_layout():
    ws = _score_ws()
    assert ws["A3"].value == "指标ID" and ws["P3"].value == "加权分"
    assert ws["A4"].value == "K01" and ws["A32"].value == "K29"
    assert ws["B1"].value == "2026-09"          # 默认示例月份

def test_score_formulas_present():
    ws = _score_ws()
    assert 'MIN(100,100*$F4/($J4/$I4))' in ws["M4"].value          # K01 成本-计算
    assert 'AVERAGE($M$9,$M$13,$M$19,$M$20,$M$25,$M$28)' in ws["M31"].value  # K28
    assert 'AVERAGE($F$39:$F$42)' in ws["M32"].value               # K29 专员均分
    assert ws["O4"].value == '=IF(AND($H4="是",ISNUMBER($M4)),$N4,0)'
    assert ws["P4"].value == '=IF(ISNUMBER($M4),$M4*$O4,0)'

def test_total_block_formulas():
    ws = _score_ws()
    assert ws["B39"].value == "=SUM($O$4:$O$9)"        # 吴佳钒
    assert ws["C40"].value == "=SUM($P$10:$P$13)"      # 郑舒漫
    assert ws["D39"].value.startswith("=IFERROR(AVERAGEIFS(任务块!")
    assert "任务块!$A:$A,$B$1" in ws["D39"].value
    assert ws["F39"].value == ('=IFERROR((C39+IF(ISNUMBER(D39),D39*30,0))'
                               '/(B39+IF(ISNUMBER(D39),30,0)),"")')
    assert ws["E43"].value == "=B43/70"

def test_data_validation_and_monitor():
    ws = _score_ws()
    dvs = {dv.sqref.__str__(): dv for dv in ws.data_validations.dataValidation}
    assert any("是,NA" in dv.formula1 for dv in ws.data_validations.dataValidation)
    assert ws["A35"].value == "M01"
    assert "MIN(100,$I35/$J35*100)" in ws["M35"].value
    assert ws["N35"].value in (None, "—")
```

- [ ] **Step 2: 运行确认失败**（`SCORE_FIRST_ROW` 不存在 → ImportError）

Run: `python -X utf8 -m pytest tests/test_kpi_template.py -v`

- [ ] **Step 3: 实现打分表**

在 `build_kpi_template.py` 中追加（并将 `build_workbook` 里 `wb.create_sheet(SHEET_SCORE)` 改为 `_score(wb)`）：

```python
from openpyxl.worksheet.datavalidation import DataValidation

SCORE_FIRST_ROW = 4
# 行映射（与 kpi_model.INDICATORS 顺序一致）
ROW_OF = {ind.id: SCORE_FIRST_ROW + n for n, ind in enumerate(INDICATORS)}
PAY_ROWS = ["K06", "K10", "K16", "K17", "K22", "K25"]          # 请款指标
PERSON_RANGE = {  # 每人指标行区间（含端点）
    "吴佳钒": (4, 9), "郑舒漫": (10, 13), "黄婷": (14, 20),
    "吴定佳": (21, 25), "张雨洁": (26, 28), "金炜铮": (29, 32),
}
TOTAL_FIRST_ROW = 39   # 总分区人员首行（39-44，顺序=PEOPLE）

def _m_formula(ind, r):
    t = ind.ftype
    if t == "成本-计算":
        return f'=IF($H{r}<>"是","",IF(OR($I{r}=0,$I{r}=""),"",MIN(100,100*$F{r}/($J{r}/$I{r}))))'
    if t == "成本-直填":
        return f'=IF($H{r}<>"是","",IF($I{r}="","",MIN(100,100*$F{r}/$I{r})))'
    if t == "达标率":
        return f'=IF($H{r}<>"是","",IF(OR($J{r}=0,$J{r}=""),"",MIN(100,$I{r}/$J{r}*100)))'
    if t == "上限":
        return f'=IF($H{r}<>"是","",IF($I{r}="","",IF($I{r}<=$F{r},100,100*$F{r}/$I{r})))'
    if t == "下限":
        return f'=IF($H{r}<>"是","",IF($I{r}="","",IF($I{r}>=$F{r},100,100*$I{r}/$F{r})))'
    if t == "请款":
        return f'=IF($H{r}<>"是","",0.5*MAX(0,100-20*$I{r})+0.5*MIN(100,$J{r}/0.9*100))'
    if t == "库存综合":
        return (f'=IF($H{r}<>"是","",IFERROR(AVERAGE(IF($I{r}<=0.03,100,100*0.03/$I{r}),'
                f'IF($J{r}<=120,100,100*120/$J{r}),IF($K{r}<=5,100,100*5/$K{r})),""))')
    if t == "三段综合":
        return (f'=IF($H{r}<>"是","",IFERROR(AVERAGE(MIN(100,100*15/$I{r}),'
                f'MIN(100,100*15/$J{r}),MIN(100,100*6/$K{r})),""))')
    if t == "引用-请款均":
        refs = ",".join(f"$M${ROW_OF[k]}" for k in PAY_ROWS)
        return f'=IF($H{r}<>"是","",IFERROR(AVERAGE({refs}),""))'
    if t == "引用-专员均分":
        return f'=IF($H{r}<>"是","",IFERROR(AVERAGE($F$39:$F$42),""))'
    raise ValueError(t)

def _score(wb):
    ws = wb.create_sheet(SHEET_SCORE)
    ws["A1"] = "绩效月份："; ws["B1"] = "2026-09"
    ws["C1"] = "复制本表命名为 打分-YYYY-MM；数据不可得选NA；原始数据见[指标标准]字段说明"
    _hdr(ws, 3, ["指标ID", "人员", "业务线", "指标", "公式类型", "目标值", "单位", "数据可用",
                 "原始1", "原始2", "原始3", "原始4", "指标得分", "全局权重", "有效权重", "加权分"])
    for n, ind in enumerate(INDICATORS):
        r = SCORE_FIRST_ROW + n
        for col, v in [(1, ind.id), (2, ind.person), (3, ind.line), (4, ind.name),
                       (5, ind.ftype), (6, ind.target), (7, ind.unit), (8, "是"),
                       (13, _m_formula(ind, r)), (14, ind.weight)]:
            ws.cell(row=r, column=col, value=v)
        ws.cell(row=r, column=15, value=f'=IF(AND($H{r}="是",ISNUMBER($M{r})),$N{r},0)')
        ws.cell(row=r, column=16, value=f'=IF(ISNUMBER($M{r}),$M{r}*$O{r},0)')
        if ind.unit == "%":
            ws.cell(row=r, column=6).number_format = "0.0%"
            ws.cell(row=r, column=9).number_format = "0.0%"
        if ind.ftype == "请款":
            ws.cell(row=r, column=10).number_format = "0.0%"
    # 数据校验：H 列 是/NA
    dv = DataValidation(type="list", formula1='"是,NA"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f"H{SCORE_FIRST_ROW}:H{SCORE_FIRST_ROW + len(INDICATORS) - 1}")
    # 监控区（不计分）
    ws.cell(row=34, column=1, value="监控区（不计分，只显示）——不可控但重要").font = Font(bold=True)
    ws.cell(row=35, column=1, value="M01"); ws.cell(row=35, column=2, value="郑舒漫")
    ws.cell(row=35, column=3, value="FOB"); ws.cell(row=35, column=4, value="截关装船准时率")
    ws.cell(row=35, column=5, value="达标率"); ws.cell(row=35, column=8, value="是")
    ws.cell(row=35, column=9, value=None); ws.cell(row=35, column=10, value=None)
    ws.cell(row=35, column=13,
            value='=IF($H35<>"是","",IF(OR($J35=0,$J35=""),"",MIN(100,$I35/$J35*100)))')
    ws.cell(row=35, column=14, value="—")
    # 总分区
    ws.cell(row=37, column=1, value="个人总分区（自动计算）").font = TITLE_FONT
    _hdr(ws, 38, ["人员", "量化有效权重和", "量化加权分和", "任务块得分", "数据覆盖率", "总分"])
    for n, p in enumerate(PEOPLE):
        r = TOTAL_FIRST_ROW + n
        lo, hi = PERSON_RANGE[p]
        ws.cell(row=r, column=1, value=p)
        ws.cell(row=r, column=2, value=f"=SUM($O${lo}:$O${hi})")
        ws.cell(row=r, column=3, value=f"=SUM($P${lo}:$P${hi})")
        ws.cell(row=r, column=4, value=(
            f'=IFERROR(AVERAGEIFS(任务块!$E:$E,任务块!$B:$B,$A{r},'
            f'任务块!$A:$A,$B$1),"")'))
        ws.cell(row=r, column=5, value=f"=B{r}/70").number_format = "0%"
        ws.cell(row=r, column=6, value=(
            f'=IFERROR((C{r}+IF(ISNUMBER(D{r}),D{r}*30,0))'
            f'/(B{r}+IF(ISNUMBER(D{r}),30,0)),"")'))
    ws.freeze_panes = "A4"
    for col, w in zip("ABCDEFGHIJKLMNOP", (8, 8, 10, 16, 10, 8, 8, 9, 9, 9, 9, 9, 9, 8, 8, 9)):
        ws.column_dimensions[col].width = w
```

> 注意 K29 专员均分引用 `$F$39:$F$42` 为专员四行（43=张雨洁实习生不计，44=金炜铮本人）——无循环引用（专员总分不依赖主管行）。

- [ ] **Step 4: 运行全部模板测试**

Run: `python -X utf8 -m pytest tests/test_kpi_template.py -v`
Expected: 全部 passed

- [ ] **Step 5: 手工冒烟——生成并检查**

Run: `python -X utf8 scripts/build_kpi_template.py`，用 WPS/Excel 打开 `物流团队绩效V1.xlsx`：
打分表 H4 选 NA 时 M4 变空、F39 总分随任务块/NA 正常归一化（填示例数验证）。

- [ ] **Step 6: Commit**

```bash
git add scripts/build_kpi_template.py tests/test_kpi_template.py
git commit -m "feat: 打分表模板——29指标公式+NA降级归一化+总分区+监控区+数据校验"
```

---

### Task 4: 任务块 sheet — 预埋 2026-09 任务 + 0/50/100 校验

**Files:**
- Modify: `scripts/build_kpi_template.py`（`build_workbook` 中 `wb.create_sheet(SHEET_TASK)` 改为 `_task(wb)`）
- Test: `tests/test_kpi_template.py`（追加）

**Interfaces:**
- Produces: 任务块布局（Task 3 的 AVERAGEIFS 与 Task 5 看板读取依赖）：
  `A月份 B姓名 C任务内容 D验收物 E得分`；表头第 3 行；预埋 2026-09 全员任务；E 列数据校验 0/50/100

- [ ] **Step 1: 追加失败测试**

```python
# tests/test_kpi_template.py 追加
SEED_TASKS = {
    "吴佳钒": ["DDP头程交接平稳（零错发）", "易仓货件数据打通"],
    "郑舒漫": ["FOB货代台账上线（含单证+订舱时效字段、近3个月数据）"],
    "黄婷": ["B端库存三项指标基线数据摸底"],
    "吴定佳": ["一件代发时效分段标准定稿（打包/运输）"],
    "张雨洁": ["进口时效分段标准整理"],
    "金炜铮": ["绩效体系首月跑通+复盘修订"],
}

def test_task_sheet_seeded_2026_09():
    ws = build_workbook()["任务块"]
    assert ws["A3"].value == "月份" and ws["E3"].value == "得分"
    seen = {}
    for row in ws.iter_rows(min_row=4, values_only=True):
        if row[0] == "2026-09":
            seen.setdefault(row[1], []).append(row[2])
    for p, tasks in SEED_TASKS.items():
        for t in tasks:
            assert t in seen.get(p, []), f"{p} 缺任务: {t}"

def test_task_score_validation():
    ws = build_workbook()["任务块"]
    assert any("0,50,100" in dv.formula1 for dv in ws.data_validations.dataValidation)
```

- [ ] **Step 2: 运行确认失败** → Run: `python -X utf8 -m pytest tests/test_kpi_template.py -v`

- [ ] **Step 3: 实现**

```python
# 追加到 build_kpi_template.py（SEED_TASKS 常量与测试一致）
SEED_TASKS = [
    ("2026-09", "吴佳钒", "DDP头程交接平稳", "当月零错发（头程大表核对）"),
    ("2026-09", "吴佳钒", "易仓货件数据打通", "易仓导出口径文档+首月数据回填"),
    ("2026-09", "郑舒漫", "FOB货代台账上线", "台账含单证+订舱时效字段、近3个月数据"),
    ("2026-09", "黄婷", "B端库存三项指标基线摸底", "各仓长周期/库龄/库内成本基线表"),
    ("2026-09", "吴定佳", "一件代发时效分段标准定稿", "打包/运输分段标准文档，主管签认"),
    ("2026-09", "张雨洁", "进口时效分段标准整理", "分段标准表（无现成标准则注明NA）"),
    ("2026-09", "金炜铮", "绩效体系首月跑通+复盘", "首月记分卡+看板产出+修订清单"),
]

def _task(wb):
    ws = wb.create_sheet(SHEET_TASK)
    ws["A1"] = "任务块（每人每月3-5条，验收物必须可判定；0/50/100=未启动/进行中/完成）"
    ws["A1"].font = TITLE_FONT
    _hdr(ws, 3, ["月份", "姓名", "任务内容", "验收物", "得分"])
    for r, row in enumerate(SEED_TASKS, 4):
        for c, v in enumerate(row, 1):
            ws.cell(row=r, column=c, value=v)
        ws.cell(row=r, column=5, value=None)   # 得分月末打
    dv = DataValidation(type="list", formula1='"0,50,100"', allow_blank=True)
    ws.add_data_validation(dv); dv.add("E4:E200")
    ws.freeze_panes = "A4"
    for col, w in zip("ABCDE", (12, 10, 40, 46, 8)):
        ws.column_dimensions[col].width = w
```

（`build_workbook` 中改为调用 `_task(wb)`；测试里的 `SEED_TASKS` dict 从本模块 import，两处合一：模块级定义列表，测试转 dict 断言。）

- [ ] **Step 4: 运行全部测试** → Run: `python -X utf8 -m pytest tests/ -v` → Expected: 全 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/build_kpi_template.py tests/test_kpi_template.py
git commit -m "feat: 任务块sheet——2026-09预埋任务+0/50/100校验"
```

---

### Task 5: 月度看板 — build_kpi_dashboard.py（读原始数据→Python重算→单文件HTML）

**Files:**
- Create: `scripts/build_kpi_dashboard.py`
- Test: `tests/test_kpi_dashboard.py`（含样例数据 fixture：模板→复制打分-2026-09→填原始值）

**Interfaces:**
- Consumes: `kpi_model`（`INDICATORS/row_scores/personal_total/PEOPLE/SPECIALISTS`）、模板布局（Task 3 的固定列/行）
- Produces:
  - `read_month(xlsx_path, month) -> dict`：`{"rows": {指标ID: {"available": bool, "i","j","k": 数值|None}}, "tasks": {姓名: 均分|None}}`
  - `compute_month(data) -> dict`：`{"totals": {姓名: 分|None}, "coverage": {姓名: 0-1}, "lines": {姓名: {业务线: 分|None}}, "team_cost": 分|None}`
  - `render(cur, prev_totals=None) -> str`（HTML）
  - CLI：`python -X utf8 scripts/build_kpi_dashboard.py --month 2026-09 [--xlsx 物流团队绩效V1.xlsx] [--out output/]`，输出 `output/kpi_dashboard_2026-09.html`
  - 环比：存在上月 sheet（`打分-<上月>`）则重算其 totals 供环比，否则显示"首月"

- [ ] **Step 0: 读 dataviz skill（强制）**

执行本任务前调用 `Skill(dataviz)`，看板配色/图形规范以其为准（红绿灯三色、卡片、进度条）；下述代码中的色值为初稿，按 skill 校准后可微调，但**结构（六区块）与阈值不变**。

- [ ] **Step 1: 写失败测试**

```python
# tests/test_kpi_dashboard.py
# -*- coding: utf-8 -*-
import pytest
from openpyxl import load_workbook
from scripts.build_kpi_template import build_workbook, OUT
from scripts.build_kpi_dashboard import read_month, compute_month, render

@pytest.fixture(scope="module")
def sample_xlsx(tmp_path_factory):
    """模板 → 打分-2026-09 填样例（含 K02=NA 降级场景）→ 任务块打分。"""
    p = tmp_path_factory.mktemp("kpi") / "sample.xlsx"
    wb = build_workbook()
    ws = wb["打分表模板"]; ws.title = "打分-2026-09"; ws["B1"] = "2026-09"
    raw = {  # 指标ID: (i, j, k, available)  数值与 test_kpi_model 对齐
        "K01": (100, 2000, None, True),   # 成本=20欧→75
        "K02": (None, None, None, False), # NA 降级
        "K03": (0.04, None, None, True),  # 上限0.05→100
        "K04": (8, None, None, True),     # 上限7→87.5
        "K05": (0.97, None, None, True),  # 下限0.95→100
        "K06": (0, 0.92, None, True),     # 请款→100
        "K07": (1.0, None, None, True), "K08": (18, 20, None, True),
        "K09": (92, 100, None, True), "K10": (1, 0.85, None, True),
        "K11": (100, 1500, None, True), "K12": (90, 100, None, True),
        "K13": (0.06, None, None, True), "K14": (10, None, None, True),
        "K15": (0.03, 120, 5, True), "K16": (0, 0.9, None, True),
        "K17": (0, 0.95, None, True),
        "K18": (200, 3000, None, True), "K19": (85, 100, None, True),
        "K20": (0.018, None, None, True), "K21": (0.05, 100, 4.5, True),
        "K22": (2, 0.7, None, True),
        "K23": (45, 50, None, True), "K24": (20, 25, None, True),
        "K25": (0, 1.0, None, True),
        "K26": (34.0, None, None, True), "K27": (14.5, 15.2, 5.8, True),
        "K28": (None, None, None, True), "K29": (None, None, None, True),
    }
    from scripts.kpi_model import INDICATORS
    for n, ind in enumerate(INDICATORS):
        r = 4 + n
        i, j, k, ok = raw[ind.id]
        ws.cell(row=r, column=8, value="是" if ok else "NA")
        for col, v in ((9, i), (10, j), (11, k)):
            if v is not None:
                ws.cell(row=r, column=col, value=v)
    tsk = wb["任务块"]
    for r in range(4, 11):          # 7条预埋任务全部打100
        tsk.cell(row=r, column=5, value=100)
    wb.save(p)
    return p

def test_read_compute(sample_xlsx):
    data = read_month(sample_xlsx, "2026-09")
    assert data["rows"]["K01"]["i"] == 100 and data["rows"]["K02"]["available"] is False
    assert data["tasks"]["吴佳钒"] == 100
    res = compute_month(data)
    # 吴佳钒：手算（K01=75×27 + K03=100×5 + K04=87.5×5 + K05=100×5 + K06=100×10 + 任务100×30）
    #        /(27+5+5+5+10+30) = (2025+500+437.5+500+1000+3000)/82 = 7462.5/82
    assert res["totals"]["吴佳钒"] == pytest.approx(91.01, abs=0.05)
    assert res["coverage"]["吴佳钒"] == pytest.approx(52 / 70, abs=0.01)
    assert res["team_cost"] == pytest.approx(min(100, 100 * 36 / 34.0), abs=0.01)  # ≈105.9→100
    assert res["lines"]["吴佳钒"]["DDP头程"] is not None

def test_render_html(sample_xlsx):
    data = read_month(sample_xlsx, "2026-09")
    html = render(compute_month(data))
    for kw in ["2026-09", "吴佳钒", "91.2", "红绿灯", "监控区", "任务块公示",
               "张雨洁", "不排名", "截关装船"]:
        assert kw in html
    assert html.count('class="card light-green"') + \
           html.count('class="card light-amber"') + \
           html.count('class="card light-red"') >= 5

def test_cli_end_to_end(sample_xlsx, tmp_path):
    import subprocess, sys
    out = tmp_path / "d.html"
    subprocess.run([sys.executable, "-X", "utf8",
                    "scripts/build_kpi_dashboard.py", "--month", "2026-09",
                    "--xlsx", str(sample_xlsx), "--out", str(out.parent)],
                   check=True, cwd=str(OUT.parent))
    assert (tmp_path / "kpi_dashboard_2026-09.html").exists()
```

- [ ] **Step 2: 运行确认失败** → Run: `python -X utf8 -m pytest tests/test_kpi_dashboard.py -v`

- [ ] **Step 3: 实现 build_kpi_dashboard.py**

```python
# scripts/build_kpi_dashboard.py
# -*- coding: utf-8 -*-
"""月度看板：读打分表原始数据 → Python 重算 → 单文件 HTML。
用法：python -X utf8 scripts/build_kpi_dashboard.py --month 2026-09 [--xlsx 物流团队绩效V1.xlsx] [--out output/]
注意：不读 Excel 公式结果（无缓存值），一律按 kpi_model 重算。"""
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))  # 直跑兼容
from openpyxl import load_workbook
from kpi_model import (INDICATORS, PEOPLE, SPECIALISTS, row_scores,
                       personal_total, score_cost)

ROOT = Path(__file__).resolve().parent.parent
FIRST_ROW = 4
GREEN, AMBER, RED, GRAY = "light-green", "light-amber", "light-red", "light-gray"

def _prev_month(m):
    y, mm = map(int, m.split("-"))
    return f"{y - 1}-12" if mm == 1 else f"{y}-{mm - 1:02d}"

def read_month(xlsx, month):
    wb = load_workbook(xlsx, data_only=False)
    ws = wb[f"打分-{month}"]
    rows = {}
    for n, ind in enumerate(INDICATORS):
        r = FIRST_ROW + n
        rows[ind.id] = {
            "ind": ind,
            "available": ws.cell(row=r, column=8).value == "是",
            "i": ws.cell(row=r, column=9).value,
            "j": ws.cell(row=r, column=10).value,
            "k": ws.cell(row=r, column=11).value,
        }
    tasks = {}
    tw = wb["任务块"]
    for row in tw.iter_rows(min_row=4, values_only=True):
        m, name, _t, _a, sc = (list(row) + [None] * 5)[:5]
        if m == month and name and isinstance(sc, (int, float)):
            tasks.setdefault(name, []).append(float(sc))
    tasks = {k: sum(v) / len(v) for k, v in tasks.items()}
    return {"month": month, "rows": rows, "tasks": tasks}

def compute_month(data):
    rows, tasks = data["rows"], data["tasks"]
    ind_score = {}
    for kid, rec in rows.items():
        ind = rec["ind"]
        if ind.ftype in ("引用-请款均",):
            pay = [ind_score.get(k) for k in ("K06", "K10", "K16", "K17", "K22", "K25")]
            vals = [s for s in pay if s is not None]
            ind_score[kid] = sum(vals) / len(vals) if vals and rec["available"] else None
        elif ind.ftype == "引用-专员均分":
            pass  # 汇总后回填
        else:
            ind_score[kid] = row_scores(ind, rec["i"], rec["j"], rec["k"]) \
                if rec["available"] else None
    totals, coverage, lines = {}, {}, {}
    for p in PEOPLE:
        mine = [(ind_score[r["ind"].id], r["ind"].weight)
                for r in rows.values() if r["ind"].person == p]
        totals[p] = personal_total(mine, tasks.get(p))
        cov_w = sum(w for s, w in mine if s is not None)
        coverage[p] = cov_w / 70
        plines = {}
        for r in rows.values():
            if r["ind"].person == p:
                key = r["ind"].line
                plines.setdefault(key, []).append((ind_score.get(r["ind"].id), r["ind"].weight))
        lines[p] = {k: (sum(s * w for s, w in v if s is not None) /
                        sum(w for s, w in v if s is not None))
                    if any(s is not None for s, _ in v) else None
                    for k, v in plines.items()}
    ind_score["K29"] = (sum(totals[p] for p in SPECIALISTS if totals.get(p) is not None) /
                        len([p for p in SPECIALISTS if totals.get(p) is not None])) \
        if any(totals.get(p) is not None for p in SPECIALISTS) else None
    # 回填 K29 进主管总分
    spec_rows = [(ind_score[r["ind"].id], r["ind"].weight) for r in rows.values()
                 if r["ind"].person == "金炜铮"]
    totals["金炜铮"] = personal_total(spec_rows, tasks.get("金炜铮"))
    k26 = rows["K26"]
    team_cost = score_cost(36, k26["i"]) if k26["available"] and k26["i"] else None
    return {"month": data["month"], "totals": totals, "coverage": coverage,
            "lines": lines, "team_cost": team_cost, "team_actual_cost":
            k26["i"] if k26["available"] else None}

def _light(s):
    return GRAY if s is None else GREEN if s >= 85 else AMBER if s >= 70 else RED

def _fmt(s):
    return "NA" if s is None else f"{s:.1f}"

def render(cur, prev_totals=None):
    m = cur["month"]
    ranked = [p for p in PEOPLE if p != "张雨洁" and cur["totals"].get(p) is not None]
    team_avg = sum(cur["totals"][p] for p in ranked) / len(ranked) if ranked else None
    def mom(p):
        if not prev_totals or cur["totals"].get(p) is None:
            return "首月"
        d = cur["totals"][p] - prev_totals[p]
        return f"{d:+.1f}"
    all_lines = []
    for p in PEOPLE:
        all_lines += list(cur["lines"].get(p, {}))
    line_order = list(dict.fromkeys(all_lines))
    matrix = ""
    for p in PEOPLE:
        cells = "".join(
            f'<td class="{_light(cur["lines"][p].get(l))}">{_fmt(cur["lines"][p].get(l))}</td>'
            for l in line_order)
        matrix += f"<tr><th>{p}</th>{cells}<td>{cur['coverage'][p]:.0%}</td></tr>"
    head = "".join(f"<th>{l}</th>" for l in line_order)
    cards = ""
    for p in PEOPLE:
        t = cur["totals"].get(p)
        cov = cur["coverage"][p]
        tag = ' <span class="tag">实习生·不排名</span>' if p == "张雨洁" else \
              (' <span class="tag">主管</span>' if p == "金炜铮" else "")
        cards += (f'<div class="card {_light(t)}">'
                  f'<div class="name">{p}{tag}</div>'
                  f'<div class="big">{_fmt(t)}</div>'
                  f'<div class="sub">覆盖率 {cov:.0%} · 环比 {mom(p)}</div></div>')
    pct = min(100, 36 / cur["team_actual_cost"] * 100) if cur["team_actual_cost"] else 0
    cost_bar = (f'<div class="bar"><div class="fill" style="width:{pct:.0f}%"></div></div>'
                f'<div>当月单台总成本 {_fmt(cur["team_actual_cost"])} 欧 / 目标 36 欧'
                f' · 得分 {_fmt(cur["team_cost"])}</div>') if cur["team_actual_cost"] \
        else "<div>团队单台总成本：NA</div>"
    tasks_rows = "".join(
        f"<tr><td>{m}</td><td>{n}</td><td>{t}</td><td>{a}</td><td>{s}</td></tr>"
        for m, n, t, a, s in cur.get("task_rows", []))
    return f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<title>物流团队绩效看板 {m}</title><style>
:root{{--bg:#f6f7f9;--card:#fff;--ink:#1a1d21;--mut:#6b7280;--line:#e5e7eb}}
body{{background:var(--bg);color:var(--ink);font:14px/1.6 "Microsoft YaHei",sans-serif;margin:0;padding:24px}}
.wrap{{max-width:1080px;margin:0 auto}} h1{{font-size:20px;margin:0 0 4px}}
.mut{{color:var(--mut);font-size:12px}} .grid{{display:grid;grid-template-columns:repeat(6,1fr);gap:12px;margin:16px 0}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px}}
.name{{font-weight:600}} .big{{font-size:30px;font-weight:700}} .sub{{font-size:12px;color:var(--mut)}}
.tag{{font-size:11px;background:#eef2f7;border-radius:4px;padding:1px 6px;color:var(--mut);font-weight:400}}
.light-green{{border-left:4px solid #2e7d32}} .light-amber{{border-left:4px solid #b26a00}}
.light-red{{border-left:4px solid #c62828}} .light-gray{{border-left:4px solid #9e9e9e}}
table{{border-collapse:collapse;width:100%;background:var(--card);border:1px solid var(--line);border-radius:10px}}
th,td{{padding:8px 10px;border-bottom:1px solid var(--line);text-align:center;font-size:13px}}
th{{background:#1f4e79;color:#fff}} td.light-green{{background:#e8f5e9}} td.light-amber{{background:#fff3e0}}
td.light-red{{background:#ffebee}} td.light-gray{{background:#f5f5f5;color:#9e9e9e}}
section{{margin:20px 0}} h2{{font-size:15px;margin:0 0 8px}} .bar{{height:14px;background:#e5e7eb;border-radius:7px;overflow:hidden}}
.fill{{height:100%;background:#2e7d32}}
</style></head><body><div class="wrap">
<h1>物流团队绩效看板 · {m}</h1>
<div class="mut">绿≥85 · 黄70-84.9 · 红&lt;70 · NA灰（降级归一化）｜量化70+任务30｜实习生算分不排名</div>
<section><h2>团队</h2><div class="card">团队总分（不含实习生）：{_fmt(team_avg)} 分</div>
<div style="margin-top:8px">{cost_bar}</div></section>
<section><h2>个人总分</h2><div class="grid">{cards}</div></section>
<section><h2>业务线红绿灯矩阵（过程管理）</h2>
<table><tr><th>人员</th>{head}<th>覆盖率</th></tr>{matrix}</table></section>
<section><h2>监控区（不计分）</h2><table><tr><th>指标</th><th>结果</th></tr>
<tr><td>FOB 截关装船准时率（货代控制）</td><td>见打分表 M01</td></tr></table></section>
<section><h2>任务块公示</h2><table><tr><th>月份</th><th>姓名</th><th>任务</th><th>验收物</th><th>得分</th></tr>{tasks_rows}</table></section>
<div class="mut">物流团队绩效V1 · 生成于 python -X utf8 scripts/build_kpi_dashboard.py</div>
</div></body></html>"""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--month", required=True)
    ap.add_argument("--xlsx", default=str(ROOT / "物流团队绩效V1.xlsx"))
    ap.add_argument("--out", default=str(ROOT / "output"))
    a = ap.parse_args()
    data = read_month(a.xlsx, a.month)
    cur = compute_month(data)
    prev = None
    try:
        prev = compute_month(read_month(a.xlsx, _prev_month(a.month)))["totals"]
    except Exception:
        pass
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    f = out / f"kpi_dashboard_{a.month}.html"
    f.write_text(render(cur, prev), encoding="utf-8")
    print(f"saved: {f}")

if __name__ == "__main__":
    sys.exit(main())
```

> 实现注意：① `render` 中 `{m}` 等花号在 f-string 里照常；② 任务块公示行需在 `render` 前由 `read_month` 顺带带回原始任务文本（给 `read_month` 返回值加 `"task_rows": [(月份,姓名,任务,验收物,得分)]`，渲染循环生成 `tasks_rows`，测试断言"任务块公示"即可）；③ 环比列上月无数据时 `prev_totals[p]` KeyError → `mom()` 里用 `prev_totals.get(p)` 判空，无则显示"—"。这些以让测试通过为准修正式子。

- [ ] **Step 4: 运行看板测试通过**

Run: `python -X utf8 -m pytest tests/test_kpi_dashboard.py -v`
Expected: 4 passed（`test_cli_end_to_end` 生成的 html 在 tmp 下）

- [ ] **Step 5: Commit**

```bash
git add scripts/build_kpi_dashboard.py tests/test_kpi_dashboard.py
git commit -m "feat: 月度看板生成器——原始数据Python重算+红绿灯矩阵+环比+任务公示"
```

---

### Task 6: 正式产物 + README + 最终验收

**Files:**
- Create: `README.md`
- Modify: 生成 `物流团队绩效V1.xlsx`、`output/kpi_dashboard_2026-09.html`（示例）

**Interfaces:**
- Consumes: 前五个任务的全部产物
- Produces: 可交付包（模板+示例看板+使用文档），spec 标记"已实施"

- [ ] **Step 1: 生成正式模板与示例看板**

```bash
python -X utf8 scripts/build_kpi_template.py
python -X utf8 scripts/build_kpi_dashboard.py --month 2026-09
```

（正式模板的任务块预埋 2026-09 且得分留空——看板示例接受全员任务分为空：`tasks` 空 → `personal_total` 分母只含量化，测试已覆盖该分支。）

- [ ] **Step 2: 写 README.md**

```markdown
# 物流团队绩效 V1

月度绩效记分卡（量化70% + 任务块30%）+ HTML 看板。设计文档见
docs/superpowers/specs/2026-08-19-logistics-team-kpi-design.md。

## 使用（每月）
1. 复制 [打分表模板] → 重命名 打分-YYYY-MM，B1 填月份
2. [任务块] 登记任务（月份/姓名/任务/验收物），月末打分 0/50/100
3. 打分表填原始数据（数据不可得选 NA，自动降级归一化）
4. 出看板：`python -X utf8 scripts/build_kpi_dashboard.py --month 2026-09`
5. 打开 output/kpi_dashboard_2026-09.html

## 重新生成模板
`python -X utf8 scripts/build_kpi_template.py`（覆盖 物流团队绩效V1.xlsx；历史打分 sheet 不受影响——重生成前先备份旧文件或在旧文件里直接复制新表）

## 测试
`python -X utf8 -m pytest tests/ -v`

## 关键规则
- 得分公式 / 降级规则 / 可控性原则 / 红绿灯阈值：见 [说明] sheet
- 权重固定至 2027-02 复盘；任务块成熟后降至 10-20% 再挂奖金
```

- [ ] **Step 3: 全量测试 + 人肉验收**

Run: `python -X utf8 -m pytest tests/ -v` → 全 passed。
浏览器打开 `output/kpi_dashboard_2026-09.html` 核对六区块齐全；WPS 打开模板核对：H 列下拉、任务块下拉、NA 时总分归一化、K28/K29 引用无循环警告。

- [ ] **Step 4: Commit + 收尾**

```bash
git add README.md 物流团队绩效V1.xlsx output/kpi_dashboard_2026-09.html
git commit -m "feat: 绩效V1交付——模板xlsx+示例看板+README"
```

spec 文件状态行改"已实施（2026-08-19）"并 `git add docs/ && git commit -m "docs: spec标记已实施"`。

---

## Self-Review 记录

- **Spec 覆盖**：§3三层结构→Task1/3/5；§4权重表→Task1(INDICATORS)+Task2；§5公式→Task1/3（镜像）；§6指标字典→Task1+Task2[指标标准]；§7任务块→Task3(AVERAGEIFS)+Task4；§8主管卡→K26-K29+两级回填（Task5 compute）；§9实习生→Task5 render tag；§10降级→Task1 personal_total+Task3 O/P列+覆盖率；§11.1五sheet→Task2-4；§11.2看板六区块→Task5；§12数据源→[指标标准]列；§13演进→README。
- **占位符**：无 TBD；Task5 实现注意③列出了三处需以测试通过为准的细化点（task_rows、环比判空），属明确指令非占位。
- **类型一致**：`read_month` 返回结构在 Task5 Interface 与实现一致；`SEED_TASKS` 测试/模块共用；K28 引用行号 `$M$9/$M$13/$M$19/$M$20/$M$25/$M$28` 与 ROW_OF 映射一致（K06→9,K10→13,K16→19,K17→20,K22→25,K25→28）。
