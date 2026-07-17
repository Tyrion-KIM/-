from yorky_client import YorkyClient


class FakeResp:
    def __init__(self, payload):
        self.status_code = 200
        self._p = payload

    def json(self):
        return self._p

    def raise_for_status(self):
        pass


class FakePoster:
    def __init__(self, pages):
        self.pages = list(pages)
        self.sleeps = []

    def post(self, url, json=None, headers=None, timeout=None):
        p = self.pages.pop(0)
        return FakeResp({"code": 200, "data": {"list": p}})


def test_pagination_stops_when_short_page():
    sleeper = lambda s: None
    # page_size=2: 第1页2条、第2页1条(<2) → 停止
    poster = FakePoster([["a", "b"], ["c"]])
    c = YorkyClient("https://api", "key", page_size=2, page_sleep_seconds=0,
                    poster=poster, sleeper=sleeper)
    rows = c.fetch_all_tracks()
    assert rows == ["a", "b", "c"]
    assert len(poster.pages) == 0  # 两页都消费了


def test_sleep_between_pages():
    calls = []
    sleeper = lambda s: calls.append(s)
    poster = FakePoster([["a", "b"], ["c"]])
    c = YorkyClient("https://api", "key", page_size=2, page_sleep_seconds=2,
                    poster=poster, sleeper=sleeper)
    c.fetch_all_tracks()
    assert calls == [2, 2]  # 每页后各 sleep 一次


def test_empty_result():
    sleeper = lambda s: None
    poster = FakePoster([[]])
    c = YorkyClient("https://api", "key", page_size=2, page_sleep_seconds=0,
                    poster=poster, sleeper=sleeper)
    assert c.fetch_all_tracks() == []


def test_api_error_code_returns_empty_and_logs():
    sleeper = lambda s: None

    class ErrPoster:
        def post(self, *a, **k):
            return FakeResp({"code": 500, "message": "bad", "data": None})

    c = YorkyClient("https://api", "key", page_size=2, page_sleep_seconds=0,
                    poster=ErrPoster(), sleeper=sleeper)
    assert c.fetch_all_tracks() == []
    assert c.fetch_succeeded is False


def test_fetch_succeeded_true_when_ok():
    sleeper = lambda s: None
    poster = FakePoster([["a"]])
    c = YorkyClient("https://api", "key", page_size=2, page_sleep_seconds=0,
                    poster=poster, sleeper=sleeper)
    c.fetch_all_tracks()
    assert c.fetch_succeeded is True
