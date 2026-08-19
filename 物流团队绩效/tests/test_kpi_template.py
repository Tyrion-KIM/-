# tests/test_kpi_template.py
# -*- coding: utf-8 -*-
import pytest
from scripts.build_kpi_template import (build_workbook, SHEET_GUIDE,
    SHEET_WEIGHTS, SHEET_STD, SHEET_SCORE, SHEET_TASK, SEED_TASKS)

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
    ids = [str(r[0].value) for r in ws.iter_rows(min_row=4) if r[0].value]
    assert len(ids) == 29 and ids[0] == "K01" and ids[-1] == "K29"

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
    assert any("是,NA" in dv.formula1 for dv in ws.data_validations.dataValidation)
    assert ws["A35"].value == "M01"
    assert "MIN(100,$I35/$J35*100)" in ws["M35"].value
    assert ws["N35"].value in (None, "—")

def test_rate_row_col9_general_and_m_iferror():
    ws = _score_ws()
    # K02 达标率（行5）：原始1=达标单数(计数)，列9 不加 % 格式
    assert ws.cell(row=5, column=9).number_format == "General"
    # K03 缺货率（行6，上限，%）：列9 保留 0.0%
    assert ws.cell(row=6, column=9).number_format == "0.0%"
    # M 列公式统一 IFERROR 包裹，避免半填时 #DIV/0!
    assert ws.cell(row=4, column=13).value.startswith("=IFERROR(")
    assert ws.cell(row=31, column=13).value.startswith("=IFERROR(")  # K28 引用类也包裹

# 模块常量 SEED_TASKS 为唯一数据源；此处转为 {姓名: [任务内容...]} 断言
_SEED_TASKS = {}
for _month, _person, _task, _accept in SEED_TASKS:
    _SEED_TASKS.setdefault(_person, []).append(_task)

def test_task_sheet_seeded_2026_09():
    ws = build_workbook()[SHEET_TASK]
    assert ws["A3"].value == "月份" and ws["E3"].value == "得分"
    seen = {}
    for row in ws.iter_rows(min_row=4, values_only=True):
        if row[0] == "2026-09":
            seen.setdefault(row[1], []).append(row[2])
    for p, tasks in _SEED_TASKS.items():
        for t in tasks:
            assert t in seen.get(p, []), f"{p} 缺任务: {t}"

def test_task_score_validation():
    ws = build_workbook()[SHEET_TASK]
    assert any("0,50,100" in dv.formula1 for dv in ws.data_validations.dataValidation)
