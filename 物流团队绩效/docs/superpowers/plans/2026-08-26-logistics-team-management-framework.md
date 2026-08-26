# 物流团队管理体系（基准框架 + 卡结构调整）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 7 份单战役定稿重构为一套"基准框架 + 战役插件"团队管理体系：产出 8 章一体化主文档、管控节奏打卡工具，并同步把 KPI V1 卡结构从 6 人调整为 5 人（雨洁卡撤销，K23/K24/K25 并入郑舒漫）。

**Architecture:** 三个交付物互不依赖、可独立测试：(1) `物流团队管理体系-基准框架.md` 一体化主文档，内容=设计文档 §2 八章定稿转"体系文件"语气；(2) KPI 卡结构调整，改 `scripts/kpi_model.py`（PEOPLE 6→5、K23/K24/K25 改郑舒漫并全部×0.5 重新配权）→ 模板生成器 → 看板生成器，沿既有"模型→模板→看板→测试"链路传播；(3) 管控节奏打卡工具 `scripts/build_rhythm_checklist.py`，控制点 JSON → 单文件 HTML 打卡看板，使基准第7章机制可复用。

**Tech Stack:** Python 3 + openpyxl（既有）；pytest（既有）；单文件 HTML 生成（既有模式）。

**Spec:** `docs/superpowers/specs/2026-08-26-logistics-team-management-framework-design.md`（计划从 spec 论证，执行者同时读两者）

## Global Constraints

- **卡结构调整与基准框架同步实施**（spec §5 决议3）：本文档两个交付物都必须完成，不后补。
- **红线三值 ≥98% / ≥90% / ≥80% 固化为战役下限**（spec §5 决议2）：主文档中作为基准级硬下限表述，战役不得低于。
- **郑舒漫承接工作降本贡献并入三段线池段归属**（spec §5 决议1）：主文档第6章按此表述。
- **命名统一**：一律写"吴佳钒"；郑舒漫为雨洁（张雨洁）全部工作的承接人。主文档与生成的 xlsx/HTML **任何地方不得再出现"张雨洁"作为岗位/人员卡**（只允许出现在交接/承接的语境说明）。
- **插件不得改写基准的 KPI 卡结构、红线三值、激励结构**（spec §1）：主文档总则按此表述。
- **权重固定至 2027-02 复盘**：本次 KPI 权重调整后，2027-02 前不再变。
- 测试基线：`python -X utf8 -m pytest tests/ -v` 当前 20 passed。任何任务不得让其回归。

---

### Task 1: 基准框架一体化主文档

**Files:**
- Create: `物流团队管理体系-基准框架.md`
- Test: `tests/test_framework_doc.py`

**Interfaces:**
- Consumes: 设计文档 `docs/superpowers/specs/2026-08-26-logistics-team-management-framework-design.md` 的全部 §2 内容（八章定稿）与 §5 定稿决议。
- Produces: 主文档 —— 后续所有插件（Q4-2026 / 2027旺季）都以它为基座；Task 5 的打卡工具在文档第7章被引用。

- [ ] **Step 1: 写文档结构测试（先红）**

```python
# tests/test_framework_doc.py
# -*- coding: utf-8 -*-
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "物流团队管理体系-基准框架.md"

def test_doc_exists():
    assert DOC.exists()

def test_all_8_chapters_present():
    text = DOC.read_text(encoding="utf-8")
    for ch in ["第1章 总则", "第2章 组织与分工", "第3章 目标体系", "第4章 绩效体系",
               "第5章 运营规则", "第6章 激励体系", "第7章 管控节奏", "第8章 保障诉求模板"]:
        assert ch in text

def test_key_mechanisms_present():
    text = DOC.read_text(encoding="utf-8")
    for kw in ["5 稳定岗", "其他项槽位", "纯管理", "KPI = 分钱依据",
               "≥98%", "≥90%", "≥80%", "A/B/C", "L1/L2/L3", "36 欧",
               "复盘总闸", "必保·合规", "必保·风险", "争取·激励", "战役插件"]:
        assert kw in text

def test_no_stale_intern_as_stable_post():
    text = DOC.read_text(encoding="utf-8")
    assert "物流实习生" not in text          # 稳定岗口径不得含实习生岗位
    assert "张雨洁" not in text              # 命名统一：只认郑舒漫承接，不出现旧人名
```

- [ ] **Step 2: 运行确认失败**

Run: `python -X utf8 -m pytest tests/test_framework_doc.py -v`
Expected: FAIL（文件不存在）

- [ ] **Step 3: 写主文档**

创建 `物流团队管理体系-基准框架.md`。文档骨架与关键内容块如下（**详细论证内容一律照抄 spec §2 各章**，转"体系文件"语气：把"设计/拟确认"改为"本体系规定"，把 spec 的 §5 三项定稿决议作为第9章"定稿决议"落底）。

文档必须包含以下章节标题与关键块（内容取自 spec，本章节只给结构约束）：

```
# 物流团队管理体系 · 基准框架
> 版本 v1.0 定稿 · 形态：基准框架 + 战役插件 · 用途：四合一
> 关联：KPI V1 绩效体系 · 2026Q4 目标分解承接表/物流动员方案/管理节奏控制图 · 2027旺季运营/保障方案 · 物流降本提成方案-H2

## 第1章 总则
  定位：基准=一套稳定规则，适用所有战役与常态；战役=基准+插件。
  适用规则：常态期直接启用基准；插件与基准冲突时插件优先，但插件不得改写
  基准的 KPI 卡结构、红线三值、激励结构。
  队伍口径：5 稳定岗 + 其他项槽位。命名统一：吴佳钒；郑舒漫为雨洁全部工作承接人。

## 第2章 组织与分工
  表：5 稳定岗 + 其他项槽位
    管理岗 金炜铮（纯管理：K26-K29+管理动作，不设业务线量能，不参与备岗轮换，回报走统筹费）
    专员·头程 吴佳钒（DDP头程，柜数）
    专员·综合 郑舒漫（FOB+特殊发运+进口+单据，单数，接雨洁全部工作 K23/K24/K25）
    专员·海外仓 黄婷（海外仓大货+调拨，车数）
    专员·件代发 吴定佳（一件代发+退件，单数）
    其他项槽位（机动支援：实习/临时/外包，不设独立卡，任务块月度考核，不占提成线池）
  关键规则：实习生岗位不稳定→战略上作为其他项；郑舒漫承接以 9/7 交接验收为完成标志；
  70/20/10 综合岗矩阵机制进基准，具体人员进插件。

## 第3章 目标体系
  三层对齐：销售→团队(G1-G9)→个人(量能+质量+任务块)，月度 KPI 打分承接。
  量能承接：台→柜/车/单，系数暂定按基线观测月复盘校准；件代发不随台数系数换算。
  红线三值 ⭐（基准级硬下限，战役不得低于）：发货达成率≥98% / 时效达标率≥90% / 数据覆盖率≥80%/月。
  NA 降级归一化；数据覆盖率连续两月<60%的线，数据管道建设进下月任务块。

## 第4章 绩效体系
  指标 K01-K29 沿用 KPI V1；卡结构 5 人（雨洁卡撤销，K23/K24/K25 并入郑舒漫并重新配权）。
  结构：量化70%+任务块30%；月度打分；9 类公式类型。
  金炜铮卡：K26/K27/K28/K29 + 管理动作任务块。
  其他项槽位：任务块月度考核，权重与 5 稳定岗无关，产出计入承接人降本贡献。

## 第5章 运营规则
  截单三级口径 A/B/C（A=完全不可承接中国端停 / B=可接·海外仓顺延德国端停 / C=可接·需求侧停美国端停）。
  硬性截单指标机制进基准、具体时间进插件。舱位提前一月锁。
  L1/L2/L3 补能；负荷红线 >150% 连续 2 周触发上报。排班值守机制进基准、排班表进插件。

## 第6章 激励体系
  目标单台 36 欧（头程15/尾程15/仓储6）。s=36−C；S=s×N×R。
  提成池 P=S×40%。质检门槛（任一不达标×90%，均不达标×80%）。
  三段线池：管理岗统筹费 M=P×10%；段权重 w=max(0,预算单台−实际单台)；超支段 w=0 主责拿0。
  个人分配=线池×KPI系数（基础系数夹[0.8,1.2]×门槛≥70/≥60/<60→×1/×0.5/×0），归一化分完。
  KPI=分钱依据：配三重保护（数据覆盖门槛、NA降级、打分月<2不预发）。
  段→主责/备岗矩阵进插件。郑舒漫承接工作降本贡献并入三段线池段归属（spec §5 决议1）。

## 第7章 管控节奏
  核心逻辑：管理控节奏=控 决策门+窗口期+硬性循环；风险高峰是值守，不是决策。
  四类机制表：决策门(拍板/错过不可逆) / 窗口期(错过即失效) / 硬性循环(每月自动转) / 风险值守(人在即可)。
  ⭐复盘总闸机制：战役中期一次会议锁多事（校准系数·回填量能·定L3·锁下期舱位）。
  打卡工具模式：`python -X utf8 scripts/build_rhythm_checklist.py` 生成逐控点打卡 HTML 看板
  （进度实时计数、打印 A4 管理日历）；具体控点清单/日期/看板实例进插件。

## 第8章 保障诉求模板
  三层诉求模板：必保·合规（周末调休/加班补助 法定1.5倍）· 必保·风险（人员补充 临时/外包岗）
  · 争取·激励（旺季奖金/团建经费/绩效评优）。
  机制：从0→1（先PPT后邮件）；分层要价；成本测算；审批路径 HR审合规→领导层批预算。
  具体盘子/条数/金额进插件。

## 第9章 定稿决议（2026-08-26 评审通过）
  1) 郑舒漫承接贡献并入三段线池段归属；2) 红线三值固化为战役下限；3) 卡结构调整与基准同步实施。

## 附：战役插件与修正点
  Q4-2026 插件 / 2027旺季插件 / 常态期插件 三栏引用章号。
  修正点：2027旺季矩阵"特殊发运+进口"主责 雨洁→郑舒漫；H2提成矩阵补郑舒漫承接贡献归属；
  人员口径统一为 5 稳定岗+其他项槽位。
```

- [ ] **Step 4: 运行确认通过**

Run: `python -X utf8 -m pytest tests/test_framework_doc.py -v`
Expected: PASS（4 个测试全过）

- [ ] **Step 5: 跑全量回归**

Run: `python -X utf8 -m pytest tests/ -q`
Expected: 20 passed（原测试不受影响，新文档测试计入，应为 20 + 4 = 24 passed）

- [ ] **Step 6: 提交**

```bash
git add "物流团队管理体系-基准框架.md" tests/test_framework_doc.py
git commit -m "docs: 物流团队管理体系基准框架 v1.0 — 8章一体化主文档（5稳定岗+其他项槽位/红线三值/KPI=分钱依据/复盘总闸/三层诉求）+结构测试"
```

---

### Task 2: KPI 模型卡结构调整（6→5 人）

**Files:**
- Modify: `scripts/kpi_model.py:11-59`（PEOPLE / SPECIALISTS / INDICATORS 顺序与权重）
- Test: `tests/test_kpi_model.py`（追加 3 个测试）

**Interfaces:**
- Consumes: 无（模型层是源头）。
- Produces: 新 `PEOPLE`（5 人）、新 `INDICATORS`（K23/K24/K25 person=郑舒漫、郑舒漫卡 7 项合计 70）。Task 3 的 `PERSON_RANGE`、Task 4 的 `ranked` 都依赖这里的行序。

- [ ] **Step 1: 先写失败测试（追加到 test_kpi_model.py）**

```python
def test_team_is_five_stable_posts():
    assert len(PEOPLE) == 5 and "张雨洁" not in PEOPLE

def test_intern_work_merged_into_zheng():
    for kid in ("K23", "K24", "K25"):
        ind = next(i for i in INDICATORS if i.id == kid)
        assert ind.person == "郑舒漫"
    assert len([i for i in INDICATORS if i.person == "郑舒漫"]) == 7

def test_zheng_weights_sum_70():
    assert sum(i.weight for i in INDICATORS if i.person == "郑舒漫") == 70
```

- [ ] **Step 2: 运行确认失败**

Run: `python -X utf8 -m pytest tests/test_kpi_model.py -v`
Expected: FAIL（新 3 测试：PEOPLE 长度 6、K23 person 为张雨洁）

- [ ] **Step 3: 改 kpi_model.py**

① PEOPLE 与 SPECIALISTS（第 11-12 行）：
```python
PEOPLE = ["吴佳钒", "郑舒漫", "黄婷", "吴定佳", "金炜铮"]
SPECIALISTS = PEOPLE[:4]          # 4 位专员（K29 专员均分）
```

② INDICATORS 重排 + 重新配权（第 24-60 行整体替换）。**原则：郑舒漫原 4 项（K07-K10）与雨洁原 3 项（K23-K25）各 ×0.5**，两块各 35 分合成 70 分卡。K23/K24/K25 移到郑舒漫块内（K10 之后），保证 `PERSON_RANGE` 连续。新顺序（行号=FIRST_ROW+下标）：

```python
INDICATORS = [
 # 吴佳钒 rows 4-9
 Indicator("K01","吴佳钒","DDP头程","成本","成本-计算",15,"欧/台",27,("发货数量A","运费折欧B"),"头程大表；长期易仓","当月签收订单"),
 Indicator("K02","吴佳钒","DDP头程","时效","达标率",None,"%",18,("达标单数","总单数"),"头程大表；长期易仓","当月签收订单，标准时效"),
 Indicator("K03","吴佳钒","始发计划","缺货率","上限",0.05,"%",5,("实际缺货率(小数)",),"库内MES+排产表","每周一交付计划"),
 Indicator("K04","吴佳钒","始发计划","缺货时间","上限",7,"天",5,("实际缺货天数",),"库内MES+排产表","缺货持续≤7天"),
 Indicator("K05","吴佳钒","在途库存","上架准确率","下限",0.95,"%",5,("实际上架准确率(小数)",),"各仓入库单上架情况",""),
 Indicator("K06","吴佳钒","财务","请款-DDP","请款",None,"",10,("迟报工作日数","请款金额占比(小数)"),"请款记录","10号前，≥90%"),
 # 郑舒漫 rows 10-16（原4项 + 承接雨洁3项，各×0.5）
 Indicator("K07","郑舒漫","FOB","单证准确率","下限",1.0,"%",7.5,("单证准确率(小数)",),"货代台账","我方单证零差错"),
 Indicator("K08","郑舒漫","FOB","订舱及时率","达标率",None,"%",5,("按时回传S/O单数","总单数"),"货代台账","OA审单→S/O≤1个工作日"),
 Indicator("K09","郑舒漫","FCA","执行时效","达标率",None,"%",12.5,("48h内达标单数","总单数"),"OA订单数据","OA申请→工厂发出≤48h"),
 Indicator("K10","郑舒漫","财务","请款-FOB","请款",None,"",10,("迟报工作日数","请款金额占比(小数)"),"请款记录","10号前，≥90%"),
 Indicator("K23","郑舒漫","特殊发运","时效","达标率",None,"%",20,("达标单数","总单数"),"头程大表；长期易仓","当月签收，按运输方式分段"),
 Indicator("K24","郑舒漫","进口业务","时效","达标率",None,"%",10,("达标单数","总单数"),"待定","分段标准8月底前定，否则首月NA"),
 Indicator("K25","郑舒漫","财务","账单协同-请款","请款",None,"",5,("迟报工作日数","请款金额占比(小数)"),"请款记录","账单协同表"),
 # 黄婷 rows 17-23
 Indicator("K11","黄婷","B端中转","成本","成本-计算",15,"欧/台",21,("签收数量A","运费折欧B"),"当月核对账单","当月签收"),
 Indicator("K12","黄婷","B端中转","时效","达标率",None,"%",14,("达标单数","总单数"),"签收单+分段标准","DE1/DK2/AT2/SE1/SI2工作日；旺3-6淡7-2"),
 Indicator("K13","黄婷","目的国计划","缺货率","上限",0.05,"%",5,("实际缺货率(小数)",),"在库+待发+在途表","每周一交付计划"),
 Indicator("K14","黄婷","目的国计划","缺货时间","上限",7,"天",5,("实际缺货天数",),"在库+待发+在途表","缺货持续≤7天"),
 Indicator("K15","黄婷","B端库存","综合","库存综合",None,"",10,("长周期占比(小数)","平均库龄(天)","单台库内成本(欧)"),"各仓库存表+账单","≤3%/≤120天/≤5欧"),
 Indicator("K16","黄婷","财务","请款-B端仓库内","请款",None,"",7.5,("迟报工作日数","请款金额占比(小数)"),"请款记录","10号前，≥90%"),
 Indicator("K17","黄婷","财务","请款-海外仓调拨","请款",None,"",7.5,("迟报工作日数","请款金额占比(小数)"),"请款记录","10号前，≥90%"),
 # 吴定佳 rows 24-28
 Indicator("K18","吴定佳","一件代发","成本","成本-计算",15,"欧/台",24,("出库数量A","运费折欧B"),"正向仓账单+领星/易仓","当月出库"),
 Indicator("K19","吴定佳","一件代发","时效","达标率",None,"%",16,("达标单数","总单数"),"渠道承诺时效","出库单生成→签收；分段标准任务块定稿"),
 Indicator("K20","吴定佳","售后物流","退件率","上限",0.02,"%",10,("物流因素退件率(小数)",),"客服数据","≤2%"),
 Indicator("K21","吴定佳","C端库存","综合","库存综合",None,"",10,("长周期占比(小数)","平均库龄(天)","单台库内成本(欧)"),"各仓库存表+账单","≤3%/≤120天/≤5欧"),
 Indicator("K22","吴定佳","财务","请款-C端仓库内","请款",None,"",10,("迟报工作日数","请款金额占比(小数)"),"请款记录","10号前，≥90%"),
 # 金炜铮 rows 29-32
 Indicator("K26","金炜铮","团队","单台总成本","成本-直填",36,"欧/台",30,("当月实际单台总成本",),"财务核算","对齐降本分成方案结算线"),
 Indicator("K27","金炜铮","团队","三段结构","三段综合",None,"",20,("头程实际","尾程实际","仓储实际"),"财务核算","15/15/6，各段得分平均"),
 Indicator("K28","金炜铮","团队","团队请款及时率","引用-请款均",None,"",10,(),"全员请款线平均","打分表内自动引用"),
 Indicator("K29","金炜铮","团队","专员均分","引用-专员均分",None,"",10,(),"4位专员总分平均","打分表内自动引用"),
]
```

- [ ] **Step 4: 运行确认通过**

Run: `python -X utf8 -m pytest tests/test_kpi_model.py -v`
Expected: PASS（原 4 测试 + 新 3 测试全过）

- [ ] **Step 5: 提交**

```bash
git add scripts/kpi_model.py tests/test_kpi_model.py
git commit -m "refactor: KPI 卡结构 6→5 — 雨洁卡撤销，K23/K24/K25 并入郑舒漫（全部×0.5 配权至70）"
```

---

### Task 3: Excel 模板生成器调整

**Files:**
- Modify: `scripts/build_kpi_template.py`（`_guide` 红绿灯行/版本行、`_weights` team 列表、`PERSON_RANGE`、`SEED_TASKS`）
- Test: `tests/test_kpi_template.py`（3 处断言更新）
- Output: 重新生成 `物流团队绩效V1.xlsx`

**Interfaces:**
- Consumes: Task 2 的新 `INDICATORS`/`PEOPLE`（行序自动由 `ROW_OF`/`enumerate(INDICATORS)` 传播）。
- Produces: 新 `物流团队绩效V1.xlsx`（5 人卡、K29 引用 `$F$39:$F$42` 不变）。Task 4 与 CLI 端到端测试都读它。

- [ ] **Step 1: 先改失败测试（更新 test_kpi_template.py 3 处断言）**

```python
def test_weights_sheet_lists_all_people():
    wb = build_workbook()
    ws = wb[SHEET_WEIGHTS]
    text = "\n".join(str(c.value) for row in ws.iter_rows() for c in row if c.value)
    for p in ["吴佳钒", "郑舒漫", "黄婷", "吴定佳", "金炜铮", "任务块", "30"]:
        assert p in text
    assert "张雨洁" not in text            # 卡结构 6→5，无实习生行
    assert "特殊发运" in text              # 郑舒漫分工含承接雨洁的线
```

在 `test_score_formulas_present` 中，K28 引用行改为新行号（K25 移到行16）：
```python
    assert 'AVERAGE($M$9,$M$13,$M$22,$M$23,$M$28,$M$16)' in ws["M31"].value  # K28
    assert 'AVERAGE($F$39:$F$42)' in ws["M32"].value               # K29 专员均分（不变）
```

在 `test_total_block_formulas` 中，郑舒漫总分区 C40 改含新区间：
```python
    assert ws["C40"].value == "=SUM($P$10:$P$16)"      # 郑舒漫（含 K23-25）
```

- [ ] **Step 2: 运行确认失败**

Run: `python -X utf8 -m pytest tests/test_kpi_template.py -v`
Expected: FAIL（张雨洁 仍在 weights、K28/C40 公式行号不符）

- [ ] **Step 3: 改 build_kpi_template.py**

① `_guide`（第 47-50 行）红绿灯与版本行：
```python
        ("五、看板红绿灯", ""),
        ("阈值", "绿≥85 / 黄70-84.9 / 红<70 / NA灰；其他项（机动支援）不设卡，只任务块月度考核"),
        ("六、版本", ""),
        ("V1.1", "2026-08-26 定稿：卡结构 6→5（雨洁卡撤销，K23/K24/K25 并入郑舒漫并重新配权）；权重固定，2027-02 复盘"),
```

② `_weights` team 列表（第 61-68 行，删张雨洁行、改郑舒漫行）：
```python
    team = [
        ("金炜铮", "物流中心主管", "物流中心全范围", "团队单台成本30 · 三段结构20 · 团队请款10 · 专员均分10", "管理任务"),
        ("郑舒漫", "物流专员", "FOB · 特殊发运 · 进口 · 单据（接雨洁）", "FOB(单证7.5+订舱5) · FCA执行12.5 · 请款10 · 特殊发运20 · 进口时效10 · 账单协同5", "30"),
        ("吴佳钒", "物流专员", "头程DDP", "DDP成本27+时效18 · 始发计划10 · 在途库存5 · 请款10", "30"),
        ("黄婷", "物流专员", "目的国大货中转、B端运输", "B端成本21+时效14 · 目的国计划10 · B端库存10 · 请款15", "30"),
        ("吴定佳", "物流专员", "一件代发、C端履约、售后退货", "一件代发成本24+时效16 · 退件率10 · C端库存10 · 请款10", "30"),
    ]
```

③ `PERSON_RANGE`（第 93-96 行）：
```python
PERSON_RANGE = {  # 每人指标行区间（含端点）
    "吴佳钒": (4, 9), "郑舒漫": (10, 16), "黄婷": (17, 23),
    "吴定佳": (24, 28), "金炜铮": (29, 32),
}
```

④ `SEED_TASKS`（第 184-192 行）：把张雨洁行 `("2026-09", "张雨洁", "进口时效分段标准整理", ...)` 替换为郑舒漫两条（承接 + 分段标准）：
```python
    ("2026-09", "郑舒漫", "雨洁工作交接验收（9/7）", "交接文档+实单演练，特殊发运/进口/单据可独立跑"),
    ("2026-09", "郑舒漫", "特殊发运时效分段标准", "分段标准表（无现成标准则注明NA）"),
```

> 注意：`PAY_ROWS`、`ROW_OF`、K29 `$F$39:$F$42`、监控区行 34-35、总分区 39-43 均**不需要改**（已按新行序核对：PAY_ROWS 各行 K06→9/K10→13/K16→22/K17→23/K22→28/K25→16；5 人总分区 39-43，专员 39-42）。

- [ ] **Step 4: 运行确认通过**

Run: `python -X utf8 -m pytest tests/test_kpi_template.py -v`
Expected: PASS

- [ ] **Step 5: 全量回归**

Run: `python -X utf8 -m pytest tests/ -q`
Expected: 全部 passed（含 Task 4 之前的状态；test_kpi_dashboard 依赖的 sample_xlsx 走 build_workbook，自动适配新顺序，暂不红）

- [ ] **Step 6: 重新生成模板并提交**

```bash
python -X utf8 scripts/build_kpi_template.py
git add scripts/build_kpi_template.py tests/test_kpi_template.py 物流团队绩效V1.xlsx
git commit -m "feat: 模板生成器 6→5 卡 — weights/guide/PERSON_RANGE/SEED_TASKS 更新，重新生成 物流团队绩效V1.xlsx"
```

---

### Task 4: 看板生成器调整

**Files:**
- Modify: `scripts/build_kpi_dashboard.py`（`render` 的 ranked/tag/副标题）
- Test: `tests/test_kpi_dashboard.py`（`test_render_html` 断言去张雨洁/不排名）

**Interfaces:**
- Consumes: Task 2 的新 `PEOPLE`（5 人）；`SPECIALISTS` 自动为 4 专员。
- Produces: `output/kpi_dashboard_<month>.html`（5 人卡、无实习生标签）。

- [ ] **Step 1: 先改失败测试（test_kpi_dashboard.py `test_render_html`）**

把 kw 列表：
```python
    for kw in ["2026-09", "吴佳钒", "91.0", "红绿灯", "监控区", "任务块公示",
               "截关装船"]:
        assert kw in html
    assert html.count('class="card light-green"') + \
           html.count('class="card light-amber"') + \
           html.count('class="card light-red"') >= 5
```
（删除 "张雨洁"、"不排名" 两个断言；卡数 ≥5 保留——5 人卡恒成立）

- [ ] **Step 2: 运行确认失败**

Run: `python -X utf8 -m pytest tests/test_kpi_dashboard.py -v`
Expected: FAIL（render 仍输出 张雨洁 标签与"实习生算分不排名"副标题）

- [ ] **Step 3: 改 build_kpi_dashboard.py**

① `render` 中 ranked（第 103 行）——去掉排除张雨洁的硬编码：
```python
    ranked = [p for p in PEOPLE if cur["totals"].get(p) is not None]
```

② 卡片 tag（第 127-128 行）——只保留主管标签：
```python
        tag = ' <span class="tag">主管</span>' if p == "金炜铮" else ""
```

③ 副标题（第 167 行）：
```python
<div class="mut">绿≥85 · 黄70-84.9 · 红&lt;70 · NA灰（降级归一化）｜量化70+任务30｜其他项（机动支援）不设卡</div>
```

- [ ] **Step 4: 运行确认通过 + 全量回归**

Run: `python -X utf8 -m pytest tests/ -q`
Expected: 全部 passed（Task 1 后基线 24 + 本 Task 变动后仍全绿）

- [ ] **Step 5: 提交**

```bash
git add scripts/build_kpi_dashboard.py tests/test_kpi_dashboard.py
git commit -m "refactor: 看板 6→5 — ranked 全 5 人、移除实习生标签与副标题，K29 引用自动指向 4 专员"
```

---

### Task 5: 管控节奏打卡工具（基准第7章机制工具）

**Files:**
- Create: `scripts/build_rhythm_checklist.py`
- Create: `scripts/control_points_default.json`（常态期控制点）
- Test: `tests/test_rhythm_checklist.py`

**Interfaces:**
- Consumes: 主文档第7章的四类控点框架（Task 1）；无 Python 依赖。
- Produces: `output/管理节奏控制图-常态期.html`。战役插件后续可提供自己的 JSON，输出各自战役的控制图（复用同一生成器）。

- [ ] **Step 1: 写失败测试**

```python
# tests/test_rhythm_checklist.py
# -*- coding: utf-8 -*-
import json, subprocess, sys
from pathlib import Path
from scripts.build_rhythm_checklist import render, DEFAULT_JSON

def test_render_contains_framework():
    cfg = json.loads(DEFAULT_JSON.read_text(encoding="utf-8"))
    html = render(cfg)
    for kw in ["决策门", "窗口期", "硬性循环", "风险值守", "复盘总闸",
               "localStorage", "@media print"]:
        assert kw in html
    n = sum(len(v) for v in cfg["groups"].values())
    assert html.count('type="checkbox"') == n

def test_cli_generates_html(tmp_path):
    out = tmp_path / "o"
    subprocess.run([sys.executable, "-X", "utf8", "scripts/build_rhythm_checklist.py",
                    "--out", str(out)], check=True,
                   cwd=str(Path(__file__).resolve().parent.parent))
    assert (out / "管理节奏控制图-常态期.html").exists()
```

- [ ] **Step 2: 运行确认失败**

Run: `python -X utf8 -m pytest tests/test_rhythm_checklist.py -v`
Expected: FAIL（模块不存在）

- [ ] **Step 3: 写默认控制点 JSON**

`scripts/control_points_default.json`（常态期 = 基准机制级控点，战役期由插件覆盖/增删）：
```json
{
  "title": "常态期管理节奏控制图",
  "file": "管理节奏控制图-常态期",
  "window": "常态期（无战役）· 基准机制 4 类控点",
  "groups": {
    "决策门": [
      {"node": "⭐复盘总闸", "time": "战役中期", "action": "一次会议定四事：校准系数·回填量能·定L3·锁下期舱位", "cost": "下期系数/量能失真两期", "star": true},
      {"node": "交接验收", "time": "人员变动后", "action": "验收交接文档+实单演练，确认可独立跑", "cost": "能力断层带病进入战役"},
      {"node": "锁舱位", "time": "提前一月", "action": "下锁舱指令，确认舱位+价格", "cost": "下期舱位/价格失控"},
      {"node": "L3 触发阀", "time": "观测触发", "action": "缺口 >2 人当量 → 提前启动临时外包岗", "cost": "峰值爆单无兜底"}
    ],
    "窗口期": [
      {"node": "装柜窗口", "time": "长假前", "action": "卡点放行装柜，A 级截单", "cost": "到仓延迟+长假断档"},
      {"node": "大促预案定稿", "time": "大促前", "action": "签认件代发大促预案", "cost": "爆单无人接"}
    ],
    "硬性循环": [
      {"node": "请款截止", "time": "每月10号前", "action": "盯全员请款金额≥90%，迟到每工作日-20", "cost": "资金流/口径失准"},
      {"node": "交付计划", "time": "每周一", "action": "确认缺货率≤5%、缺货时间≤7天", "cost": "缺货失控"},
      {"node": "打分+数据覆盖率", "time": "每月末", "action": "收原始数据、判NA、出分；覆盖率≥80%", "cost": "数据管道连续两月<60%进任务块"}
    ],
    "风险值守": [
      {"node": "长假值守", "time": "法定长假", "action": "A级截单，值班留守", "cost": "断档"},
      {"node": "大促值守", "time": "黑五/网一", "action": "C级需求侧停，值班", "cost": "爆单无人接"},
      {"node": "跨年值守", "time": "圣诞+跨年", "action": "B级顺延+收官复盘", "cost": "收官失控"}
    ]
  }
}
```

- [ ] **Step 4: 写生成器脚本**

`scripts/build_rhythm_checklist.py`（完整实现，控制点 JSON → 单文件 HTML，功能：四类分区 / 逐节点打卡 / 进度条 / 主题切换 / localStorage 持久 / A4 打印）：
```python
# scripts/build_rhythm_checklist.py
# -*- coding: utf-8 -*-
"""管控节奏打卡工具：控制点 JSON → 单文件 HTML 看板（打卡/进度/主题/打印）。
用法：python -X utf8 scripts/build_rhythm_checklist.py [--json scripts/control_points_default.json] [--out output/]"""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

DEFAULT_JSON = Path(__file__).resolve().parent / "control_points_default.json"
ROOT = Path(__file__).resolve().parent.parent
TYPES = ["决策门", "窗口期", "硬性循环", "风险值守"]
TYPE_NOTE = {
    "决策门": "管理拍板 · 错过不可逆",
    "窗口期": "错过即失效 · 不等人",
    "硬性循环": "每月自动转 · 盯执行",
    "风险值守": "人在即可 · 不做决策",
}

def render(cfg):
    gid = 0
    groups = ""
    for t in TYPES:
        items = cfg.get("groups", {}).get(t, [])
        if not items:
            continue
        rows = ""
        for it in items:
            gid += 1
            star = ' <span class="star">⭐</span>' if it.get("star") else ""
            rows += (f'<tr><td class="chk"><input type="checkbox" data-gid="{gid}">'
                     f'<span class="node">{it["node"]}{star}</span></td>'
                     f'<td>{it.get("time", "")}</td><td>{it["action"]}</td>'
                     f'<td class="cost">{it.get("cost", "")}</td></tr>')
        groups += (f'<section><h2>{t} <span class="note">{TYPE_NOTE[t]}</span></h2>'
                   f'<table><tr><th>节点</th><th>时间</th><th>管理动作</th><th>错过代价</th></tr>'
                   f'{rows}</table></section>')
    return f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<title>{cfg["title"]}</title><style>
:root{{--bg:#f6f7f9;--card:#fff;--ink:#1a1d21;--mut:#6b7280;--line:#e5e7eb;
--hdr:#1f4e79;--good:#0ca30c;--good-bg:#e7f8e7;--star:#b8860b}}
body{{background:var(--bg);color:var(--ink);font:14px/1.6 system-ui,-apple-system,"Segoe UI","Microsoft YaHei","PingFang SC",sans-serif;margin:0;padding:24px}}
.wrap{{max-width:920px;margin:0 auto}} h1{{font-size:20px;margin:0 0 4px}}
.mut{{color:var(--mut);font-size:12px}} .bar{{height:16px;background:var(--line);border-radius:8px;overflow:hidden;margin:10px 0 4px}}
.fill{{height:100%;background:var(--good);width:0}}
.prog{{font-weight:700}} section{{margin:18px 0}}
h2{{font-size:15px;margin:0 0 6px}} .note{{font-size:12px;color:var(--mut);font-weight:400}}
table{{border-collapse:collapse;width:100%;background:var(--card);border:1px solid var(--line);border-radius:8px}}
th,td{{padding:8px 10px;border-bottom:1px solid var(--line);text-align:left;font-size:13px;vertical-align:top}}
th{{background:var(--hdr);color:#fff}} .chk{{white-space:nowrap}} .node{{margin-left:6px}}
.star{{color:var(--star)}} .cost{{color:var(--mut);font-size:12px}}
button{{margin-left:8px;border:1px solid var(--line);background:var(--card);border-radius:6px;padding:3px 10px;cursor:pointer}}
@media (prefers-color-scheme: dark){{
:root:not([data-theme="light"]){{--bg:#0d0d0d;--card:#1a1a19;--ink:#fff;--mut:#c3c2b7;--line:#2c2c2a;--hdr:#123a5e;--good-bg:#0d2b0d}}}}
:root[data-theme="dark"]{{--bg:#0d0d0d;--card:#1a1a19;--ink:#fff;--mut:#c3c2b7;--line:#2c2c2a;--hdr:#123a5e;--good-bg:#0d2b0d}}
@media print{{.no-print{{display:none}} body{{background:#fff;color:#000;padding:0}}
table{{border:1px solid #000}} th{{background:#eee;color:#000}}
input[type=checkbox]{{accent-color:#000}}}}
</style></head><body><div class="wrap">
<h1>{cfg["title"]}</h1>
<div class="mut no-print">{cfg["window"]} ｜ 逐节点勾选打卡，进度存本浏览器</div>
<div class="no-print" style="margin:8px 0"><span class="prog" id="prog">0 / 0</span>
<button id="theme">主题</button></div>
<div class="bar no-print"><div class="fill" id="bar"></div></div>
{groups}
<script>
const KEY='rhythm:{cfg["title"]}';let st={{}};
try{{st=JSON.parse(localStorage.getItem(KEY)||'{{}}')}}catch(e){{}}
const cbs=[...document.querySelectorAll('input[type=checkbox]')];
function save(){{try{{localStorage.setItem(KEY,JSON.stringify(st))}}catch(e){{}}update()}}
function update(){{const n=cbs.filter(c=>c.checked).length;
document.getElementById('prog').textContent=n+' / '+cbs.length;
document.getElementById('bar').style.width=(n/cbs.length*100).toFixed(0)+'%'}}
cbs.forEach(cb=>{{cb.checked=!!st[cb.dataset.gid];
cb.addEventListener('change',()=>{{st[cb.dataset.gid]=cb.checked;save()}})}});
const th=['系统','浅色','深色'];let ti=0;
document.getElementById('theme').addEventListener('click',()=>{{
ti=(ti+1)%3;const v=th[ti];document.documentElement.dataset.theme=
v==='系统'?'':(v==='深色'?'dark':'light');document.getElementById('theme').textContent=v}});
update();
</script></div></body></html>"""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=str(DEFAULT_JSON))
    ap.add_argument("--out", default=str(ROOT / "output"))
    a = ap.parse_args()
    cfg = json.loads(Path(a.json).read_text(encoding="utf-8"))
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    f = out / f"{cfg['file']}.html"
    f.write_text(render(cfg), encoding="utf-8")
    print(f"saved: {f}")

if __name__ == "__main__":
    sys.exit(main())
```

> 注意：上段模板用 Python f-string，HTML 内所有字面花括号 `{` 须写成 `{{`、`}` 写成 `}}`（已按此写出）；`<script>` 内 `{{}}` 经 f-string 渲染后还原为 `{}`。

- [ ] **Step 5: 运行确认通过**

Run: `python -X utf8 -m pytest tests/test_rhythm_checklist.py -v`
Expected: PASS（2 测试全过）

- [ ] **Step 6: 全量回归 + 生成 + 提交**

```bash
python -X utf8 -m pytest tests/ -q          # 全绿
python -X utf8 scripts/build_rhythm_checklist.py   # 生成 output/管理节奏控制图-常态期.html
git add scripts/build_rhythm_checklist.py scripts/control_points_default.json tests/test_rhythm_checklist.py
git commit -m "feat: 管控节奏打卡工具 — 控制点JSON→HTML看板（四类控点/打卡/进度/主题/打印），常态期默认控点"
```

---

### Task 6: README 更新 + 交付封装

**Files:**
- Modify: `README.md`
- Create: `物流团队管理体系-基准框架-定稿-20260826.zip`（封装 主文档 + 打卡工具产物 + 更新后 xlsx）

**Interfaces:**
- Consumes: Task 1 主文档、Task 3 新 xlsx、Task 5 打卡产物。
- Produces: 交付包（用户既有模式）。

- [ ] **Step 1: 更新 README**

在 `README.md` 顶部"物流团队绩效 V1"标题下追加一段（不改既有内容）：
```markdown
> 本目录已并入《物流团队管理体系-基准框架 v1.0》：基准框架 + 战役插件，四合一承接组织/目标/绩效/激励。
> 主文档：`物流团队管理体系-基准框架.md`；管控节奏打卡工具：`python -X utf8 scripts/build_rhythm_checklist.py`。
> 绩效卡结构 2026-08-26 调整为 5 稳定岗（雨洁卡撤销，K23/K24/K25 并入郑舒漫并重新配权）。
```

- [ ] **Step 2: 验证交付物齐全**

Run: `python -X utf8 -m pytest tests/ -q`
Expected: 全绿（test_framework_doc 4 + test_kpi_model 8 + test_kpi_template 13 + test_kpi_dashboard 3 + test_rhythm_checklist 2 = **30 passed**；test_kpi_model 8 = 原4 + 简报3 + T2 审后补1 `test_zheng_merged_weights_halved_exact`）
核对存在：`物流团队管理体系-基准框架.md`、`物流团队绩效V1.xlsx`、`output/管理节奏控制图-常态期.html`。

- [ ] **Step 3: 打包 zip**

把 `物流团队管理体系-基准框架.md` + `output/管理节奏控制图-常态期.html` + `物流团队绩效V1.xlsx` 打进 `物流团队管理体系-基准框架-定稿-20260826.zip`（仓库根目录）。

- [ ] **Step 4: 提交**

```bash
git add README.md "物流团队管理体系-基准框架-定稿-20260826.zip"
git commit -m "docs: README 挂接基准框架 + 交付封装 zip（主文档/打卡工具/5人卡xlsx）"
```

---

## Self-Review

**1. Spec 覆盖**：§2 八章全部落进 Task 1 主文档骨架；§5 三项定稿决议进 Task 1 第9章；K23/K24/K25 并入郑舒漫并重新配权（spec §2 第4章）由 Task 2-4 实现；打卡工具模式（spec §2 第7章）由 Task 5 实现；插件修正点（spec §3.1）落进 Task 1"附：战役插件与修正点"。

**2. 占位符扫描**：所有步骤含真实代码/内容；无 TBD/TODO。

**3. 类型/行号一致性**：已按新 INDICATORS 顺序重推行号——郑舒漫 (10,16)、黄婷 (17,23)、吴定佳 (24,28)、金炜铮 (29,32)；PAY_ROWS→K28 公式 `$M$9,$M$13,$M$22,$M$23,$M$28,$M$16`；K29 `$F$39:$F$42` 与总分区 39-43 不变；Task 3 Step 4 注释已标注这些"不需改"项以防执行者误改。
