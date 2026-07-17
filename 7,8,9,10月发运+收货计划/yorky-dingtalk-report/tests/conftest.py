import pytest


@pytest.fixture
def sample_tracks():
    """模拟 trackList/push 返回的 data.list 单页样本。"""
    return [
        {"inputId": 1001, "userNo": "U001", "serviceName": "FBA-UPS-DE",
         "countryText": "德国", "trackStatus": 1, "trackStatusText": "转运中",
         "deliveryStatus": "P", "trackDesc": "已到达中转仓", "trackTime": "2026-07-17 09:00"},
        {"inputId": 1002, "userNo": "U002", "serviceName": "FBA-DHL-PL",
         "countryText": "波兰", "trackStatus": 2, "trackStatusText": "已送达",
         "deliveryStatus": "C", "trackDesc": "签收完成", "trackTime": "2026-07-16 18:00"},
        {"inputId": 1003, "userNo": "U003", "serviceName": "FBA-UPS-DE",
         "countryText": "德国", "trackStatus": 0, "trackStatusText": "待转动",
         "deliveryStatus": "L", "trackDesc": "已下单待转运", "trackTime": "2026-07-17 08:00"},
        {"inputId": 1004, "userNo": "U004", "serviceName": "FBA-UPS-DE",
         "countryText": "德国", "trackStatus": 1, "trackStatusText": "转运中",
         "deliveryStatus": "W", "trackDesc": "问题件：地址异常", "trackTime": "2026-07-17 07:00"},
    ]
