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
