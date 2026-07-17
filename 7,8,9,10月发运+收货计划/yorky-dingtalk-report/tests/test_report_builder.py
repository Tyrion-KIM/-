from report_builder import ReportBuilder, ReportData


def make_builder():
    return ReportBuilder(exclude_track_status=[2],
                         exclude_delivery_status=["C"],
                         long_tail_threshold=50,
                         today="2026-07-17")


def test_filters_out_delivered(sample_tracks):
    rb = make_builder()
    rep = rb.build(sample_tracks)
    # 样本4条，1条已送达(trackStatus=2)被排除 → 3条在途
    assert rep.in_transit_count == 3
    assert rep.is_empty is False


def test_problem_shipment_grouped_first(sample_tracks):
    rb = make_builder()
    rep = rb.build(sample_tracks)
    idx_problem = rep.markdown.find("问题件")
    idx_transit = rep.markdown.find("转运中")
    assert idx_problem != -1 and idx_problem < idx_transit


def test_empty_when_all_delivered():
    rb = make_builder()
    rep = rb.build([{"inputId": 1, "trackStatus": 2, "trackStatusText": "已送达",
                     "deliveryStatus": "C", "userNo": "X", "serviceName": "s",
                     "countryText": "c", "trackDesc": "d", "trackTime": "t"}])
    assert rep.is_empty is True
    assert "全部已送达" in rep.markdown


def test_long_desc_truncated():
    rb = make_builder()
    long_desc = "字" * 100
    rep = rb.build([{"inputId": 1, "trackStatus": 1, "trackStatusText": "转运中",
                     "deliveryStatus": "P", "userNo": "U", "serviceName": "s",
                     "countryText": "c", "trackDesc": long_desc, "trackTime": "t"}])
    assert "…" in rep.markdown
    assert long_desc not in rep.markdown


def test_long_tail_only_summary():
    rb = make_builder()
    many = [{"inputId": i, "trackStatus": 1, "trackStatusText": "转运中",
             "deliveryStatus": "P", "userNo": f"U{i}", "serviceName": "s",
             "countryText": "c", "trackDesc": "d", "trackTime": "t"} for i in range(60)]
    rep = rb.build(many)
    assert "| 客户单号 |" not in rep.markdown  # 不渲染明细表格
    assert "转运中" in rep.markdown  # 仅概要计数


def test_title_contains_today():
    rb = make_builder()
    rep = rb.build([])
    assert "2026-07-17" in rep.title
