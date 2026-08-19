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
    ids = [str(r[0].value) for r in ws.iter_rows(min_row=4) if r[0].value]
    assert len(ids) == 29 and ids[0] == "K01" and ids[-1] == "K29"
