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

def test_team_is_five_stable_posts():
    assert len(PEOPLE) == 5 and "张雨洁" not in PEOPLE

def test_intern_work_merged_into_zheng():
    for kid in ("K23", "K24", "K25"):
        ind = next(i for i in INDICATORS if i.id == kid)
        assert ind.person == "郑舒漫"
    assert len([i for i in INDICATORS if i.person == "郑舒漫"]) == 7

def test_zheng_weights_sum_70():
    assert sum(i.weight for i in INDICATORS if i.person == "郑舒漫") == 70

def test_zheng_merged_weights_halved_exact():
    # 逐项钉死 ×0.5 配权（仅断言合计=70 防不住"忘乘0.5"，15/10/25/20+40/20/10 合计仍是70）
    expected = {"K07": 7.5, "K08": 5.0, "K09": 12.5, "K10": 10.0,
                "K23": 20.0, "K24": 10.0, "K25": 5.0}
    got = {i.id: i.weight for i in INDICATORS if i.person == "郑舒漫"}
    assert got == expected
