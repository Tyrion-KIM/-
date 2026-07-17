import dingtalk_sender as ds


class FakeResp:
    def __init__(self, status, payload):
        self.status_code = status
        self._p = payload

    def json(self):
        return self._p


class FakePoster:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def post(self, url, json=None, timeout=None):
        self.calls.append((url, json, timeout))
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


WEBHOOK = "https://oapi.dingtalk.com/robot/send?access_token=abc"
SECRET = "SEC000test"
TS = 1700000000000


def test_send_success():
    poster = FakePoster([FakeResp(200, {"errcode": 0, "errmsg": "ok"})])
    ok = ds.send_action_card(WEBHOOK, SECRET, "标题", "**正文**",
                             "查看后台", "https://www.56yorky.com",
                             now_ms=TS, poster=poster, sleeper=lambda s: None)
    assert ok is True
    assert len(poster.calls) == 1
    url, body, _ = poster.calls[0]
    assert "timestamp=1700000000000" in url
    assert body["msgtype"] == "actionCard"
    assert body["actionCard"]["title"] == "标题"
    assert body["actionCard"]["btns"][0]["title"] == "查看后台"


def test_send_retries_then_success():
    poster = FakePoster([
        FakeResp(200, {"errcode": 130101, "errmsg": "rate limited"}),
        FakeResp(200, {"errcode": 0, "errmsg": "ok"}),
    ])
    ok = ds.send_action_card(WEBHOOK, SECRET, "t", "m", "b", "u",
                             now_ms=TS, poster=poster, retries=2, sleeper=lambda s: None)
    assert ok is True
    assert len(poster.calls) == 2


def test_send_all_fail_returns_false():
    poster = FakePoster([
        ConnectionError("boom"),
        ConnectionError("boom"),
        ConnectionError("boom"),
    ])
    ok = ds.send_action_card(WEBHOOK, SECRET, "t", "m", "b", "u",
                             now_ms=TS, poster=poster, retries=2, sleeper=lambda s: None)
    assert ok is False
    assert len(poster.calls) == 3  # 1 初次 + 2 重试
