# 56yorky 转运状态日报 → 钉钉推送 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 每天定时从 56yorky 拉取全部入仓单轨迹、过滤出"在途"单、生成钉钉 ActionCard 报表并推送。

**Architecture:** 单进程 Python 脚本，5 个职责单一的模块（client / report / sender / config / main），由 Windows 任务计划程序每日 10:00 触发。模块间通过 `list[dict]` 与 `ReportData` 数据结构解耦，全部可独立单测。

**Tech Stack:** Python 3.12、`requests`（HTTP）、`pyyaml`（配置）、`pytest`（测试）。钉钉加签用标准库 `hmac/hashlib/base64/urllib`。

## Global Constraints

- 上游 base：`https://api.56yorky.com`，鉴权头 `apiKey`，**全局限速 2 秒/次**。
- 主接口：`POST /api/depot/expand/trackList/push`，分页 `limit/offset`，返回 `data.list`。
- "在途"过滤：排除 `trackStatus==2`（已送达）与 `deliveryStatus=="C"`（签收）；规则按字段存在才应用。
- 钉钉安全方式：**加签**（timestamp 毫秒 + secret，HMAC-SHA256 → base64 → quote_plus）。
- 真实密钥只放 `config.yaml`（已 gitignore）；仓库只留 `config.example.yaml`。
- 所有代码与提交信息中文注释可读；提交信息格式 `feat/fix/chore: 描述`。
- Python 文件 UTF-8；Windows 环境运行，路径用 `pathlib.Path`。

参考规格：`docs/superpowers/specs/2026-07-17-yorky-dingtalk-track-report-design.md`

---

## File Structure

| 文件 | 职责 |
|---|---|
| `requirements.txt` | 依赖：requests, pyyaml, pytest |
| `config.example.yaml` | 配置模板（无真实密钥） |
| `config.yaml` | 真实配置（gitignore，用户填写） |
| `config.py` | 加载并校验 yaml → `Config` dataclass |
| `yorky_client.py` | 56yorky API 封装：分页、2s sleep、重试 |
| `report_builder.py` | 在途过滤 + 分组 + Markdown 生成 |
| `dingtalk_sender.py` | ActionCard 拼装 + 加签 + 推送 + 重试 |
| `main.py` | 编排入口，支持 `--dry-run` |
| `run_daily.bat` | Task Scheduler 入口批处理 |
| `install_task.ps1` | 一键注册 Windows 每日 10:00 任务 |
| `tests/test_config.py` | 配置加载校验测试 |
| `tests/test_dingtalk_sign.py` | 加签算法测试（golden vector） |
| `tests/test_dingtalk_sender.py` | 推送测试（mock requests） |
| `tests/test_yorky_client.py` | 分页/限速/重试测试（mock requests） |
| `tests/test_report_builder.py` | 过滤/分组/Markdown 测试 |
| `tests/conftest.py` | 共享 fixtures（样本数据） |

---

## Task 1: 项目脚手架与依赖

**Files:**
- Create: `requirements.txt`
- Create: `config.example.yaml`
- Create: `tests/__init__.py`（空文件）
- Create: `tests/conftest.py`

**Interfaces:**
- Produces: 依赖清单与样本数据 fixtures，供后续测试复用。

- [ ] **Step 1: 创建 requirements.txt**

```
requests>=2.31.0
pyyaml>=6.0
pytest>=7.4.0
```

- [ ] **Step 2: 创建 config.example.yaml**

```yaml
yorky:
  base_url: https://api.56yorky.com
  api_key: REPLACE_WITH_YOUR_APIKEY
  page_size: 100
  page_sleep_seconds: 2

dingtalk:
  webhook: https://oapi.dingtalk.com/robot/send?access_token=REPLACE
  secret: REPLACE_WITH_YOUR_SECRET
  backend_url: https://www.56yorky.com

filter:
  exclude_track_status: [2]
  exclude_delivery_status: ["C"]
  long_tail_threshold: 50

logging:
  dir: logs
```

- [ ] **Step 3: 创建 tests/__init__.py（空）与 tests/conftest.py**

`tests/conftest.py`:
```python
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
```

- [ ] **Step 4: 安装依赖并验证 pytest 可运行**

Run: `python -m pip install -r requirements.txt`
Run: `python -m pytest tests/ -v`
Expected: `no tests ran`（ collectors 通过即可，无报错）

- [ ] **Step 5: Commit**

```bash
git add requirements.txt config.example.yaml tests/__init__.py tests/conftest.py
git commit -m "chore: 项目脚手架、依赖与测试样本"
```

---

## Task 2: 配置加载 config.py

**Files:**
- Create: `config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `load_config(path: str | Path) -> Config`，`Config` 为 dataclass，
  含 `.yorky.base_url/api_key/page_size/page_sleep_seconds`、`.dingtalk.webhook/secret/backend_url`、
  `.filter.exclude_track_status/exclude_delivery_status/long_tail_threshold`、`.logging.dir`。
  缺失必填项抛 `ValueError`。

- [ ] **Step 1: 写失败测试 tests/test_config.py**

```python
import textwrap
from config import load_config, Config

VALID = textwrap.dedent("""
yorky:
  base_url: https://api.56yorky.com
  api_key: abc123
  page_size: 100
  page_sleep_seconds: 2
dingtalk:
  webhook: https://oapi.dingtalk.com/robot/send?access_token=x
  secret: SEC
  backend_url: https://www.56yorky.com
filter:
  exclude_track_status: [2]
  exclude_delivery_status: ["C"]
  long_tail_threshold: 50
logging:
  dir: logs
""")

def write(tmp_path, text):
    p = tmp_path / "config.yaml"
    p.write_text(text, encoding="utf-8")
    return p

def test_load_valid_config(tmp_path):
    cfg = load_config(write(tmp_path, VALID))
    assert isinstance(cfg, Config)
    assert cfg.yorky.api_key == "abc123"
    assert cfg.yorky.page_size == 100
    assert cfg.dingtalk.secret == "SEC"
    assert cfg.filter.exclude_track_status == [2]
    assert cfg.filter.long_tail_threshold == 50

def test_missing_apikey_raises(tmp_path):
    bad = VALID.replace("api_key: abc123\n", "")
    import pytest
    with pytest.raises(ValueError):
        load_config(write(tmp_path, bad))

def test_defaults_when_optional_missing(tmp_path):
    no_filter = VALID.replace(
        "  exclude_track_status: [2]\n  exclude_delivery_status: [\"C\"]\n  long_tail_threshold: 50\n",
        "")
    cfg = load_config(write(tmp_path, no_filter))
    assert cfg.filter.exclude_track_status == [2]
    assert cfg.filter.long_tail_threshold == 50
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'config'`）

- [ ] **Step 3: 实现 config.py**

```python
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import yaml


@dataclass
class YorkyCfg:
    base_url: str
    api_key: str
    page_size: int = 100
    page_sleep_seconds: float = 2.0


@dataclass
class DingTalkCfg:
    webhook: str
    secret: str
    backend_url: str = "https://www.56yorky.com"


@dataclass
class FilterCfg:
    exclude_track_status: list[int] = field(default_factory=lambda: [2])
    exclude_delivery_status: list[str] = field(default_factory=lambda: ["C"])
    long_tail_threshold: int = 50


@dataclass
class LoggingCfg:
    dir: str = "logs"


@dataclass
class Config:
    yorky: YorkyCfg
    dingtalk: DingTalkCfg
    filter: FilterCfg = field(default_factory=FilterCfg)
    logging: LoggingCfg = field(default_factory=LoggingCfg)


def _require(d: dict, key: str, section: str):
    if not d.get(key):
        raise ValueError(f"配置缺失必填项: {section}.{key}")
    return d[key]


def load_config(path: str | Path) -> Config:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    y = raw.get("yorky") or {}
    dt = raw.get("dingtalk") or {}
    fl = raw.get("filter") or {}
    lg = raw.get("logging") or {}

    yorky = YorkyCfg(
        base_url=_require(y, "base_url", "yorky"),
        api_key=_require(y, "api_key", "yorky"),
        page_size=int(y.get("page_size", 100)),
        page_sleep_seconds=float(y.get("page_sleep_seconds", 2.0)),
    )
    dingtalk = DingTalkCfg(
        webhook=_require(dt, "webhook", "dingtalk"),
        secret=_require(dt, "secret", "dingtalk"),
        backend_url=dt.get("backend_url", "https://www.56yorky.com"),
    )
    filt = FilterCfg(
        exclude_track_status=list(fl.get("exclude_track_status", [2])),
        exclude_delivery_status=list(fl.get("exclude_delivery_status", ["C"])),
        long_tail_threshold=int(fl.get("long_tail_threshold", 50)),
    )
    logging_cfg = LoggingCfg(dir=lg.get("dir", "logs"))
    return Config(yorky=yorky, dingtalk=dingtalk, filter=filt, logging=logging_cfg)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/test_config.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add config.py tests/test_config.py
git commit -m "feat: 配置加载与校验"
```

---

## Task 3: 钉钉加签 dingtalk_sender.py（sign 部分）

**Files:**
- Create: `dingtalk_sender.py`
- Test: `tests/test_dingtalk_sign.py`

**Interfaces:**
- Produces: `sign_dingtalk(secret: str, timestamp: int) -> str`（返回 urlencoded 的 base64 签名）。
- Produces: `build_signed_webhook(webhook: str, secret: str, timestamp: int) -> str`。

- [ ] **Step 1: 写失败测试 tests/test_dingtalk_sign.py（golden vector）**

```python
from dingtalk_sender import sign_dingtalk, build_signed_webhook

# golden vector：由官方算法计算的确定值（secret=SEC000test, ts=1700000000000）
SECRET = "SEC000test"
TS = 1700000000000
EXPECTED_SIGN_URL = "1hLl2KkRX3rps9FaitIUwaac%2BCtAFEaP345jvdrTL7c%3D"

def test_sign_matches_golden_vector():
    assert sign_dingtalk(SECRET, TS) == EXPECTED_SIGN_URL

def test_sign_is_deterministic():
    assert sign_dingtalk(SECRET, TS) == sign_dingtalk(SECRET, TS)

def test_build_signed_webhook():
    base = "https://oapi.dingtalk.com/robot/send?access_token=abc"
    url = build_signed_webhook(base, SECRET, TS)
    assert "timestamp=1700000000000" in url
    assert f"sign={EXPECTED_SIGN_URL}" in url
    assert url.startswith(base)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_dingtalk_sign.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'dingtalk_sender'`）

- [ ] **Step 3: 实现 dingtalk_sender.py 的加签部分**

```python
from __future__ import annotations
import hmac
import hashlib
import base64
import urllib.parse


def sign_dingtalk(secret: str, timestamp: int) -> str:
    """钉钉机器人加签：返回 urlencoded 的 base64 签名串。"""
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        secret.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    sign = base64.b64encode(hmac_code).decode("utf-8")
    return urllib.parse.quote_plus(sign)


def build_signed_webhook(webhook: str, secret: str, timestamp: int) -> str:
    sign = sign_dingtalk(secret, timestamp)
    sep = "&" if "?" in webhook else "?"
    return f"{webhook}{sep}timestamp={timestamp}&sign={sign}"
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/test_dingtalk_sign.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add dingtalk_sender.py tests/test_dingtalk_sign.py
git commit -m "feat: 钉钉加签算法"
```

---

## Task 4: 钉钉 ActionCard 推送 dingtalk_sender.py（send 部分）

**Files:**
- Modify: `dingtalk_sender.py`（追加 send_action_card）
- Test: `tests/test_dingtalk_sender.py`

**Interfaces:**
- Consumes: `build_signed_webhook`（Task 3）
- Produces: `send_action_card(webhook: str, secret: str, title: str, markdown: str, btn_title: str, btn_url: str, timeout: int=10, retries: int=2, now_ms: int|None=None, poster=requests, sleeper=time.sleep) -> bool`。
  `poster` 与 `sleeper` 注入便于测试；`now_ms` 注入便于确定性测试。

- [ ] **Step 1: 写失败测试 tests/test_dingtalk_sender.py**

```python
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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_dingtalk_sender.py -v`
Expected: FAIL（`AttributeError: module 'dingtalk_sender' has no attribute 'send_action_card'`）

- [ ] **Step 3: 追加实现 dingtalk_sender.py**

在文件顶部 `import` 区追加 `import time` 与 `import requests`，文件末尾追加：

```python
def send_action_card(webhook: str, secret: str, title: str, markdown: str,
                     btn_title: str, btn_url: str, timeout: int = 10,
                     retries: int = 2, now_ms: int | None = None,
                     poster=requests, sleeper=time.sleep) -> bool:
    """推送 ActionCard。成功（errcode==0）返回 True；耗尽重试返回 False。"""
    ts = now_ms if now_ms is not None else int(time.time() * 1000)
    url = build_signed_webhook(webhook, secret, ts)
    payload = {
        "msgtype": "actionCard",
        "actionCard": {
            "title": title,
            "text": markdown,
            "btnOrientation": "0",
            "btns": [{"title": btn_title, "actionURL": btn_url}],
        },
    }
    attempts = retries + 1
    for i in range(attempts):
        try:
            resp = poster.post(url, json=payload, timeout=timeout)
            data = resp.json()
            if data.get("errcode") == 0:
                return True
        except Exception:
            pass
        if i < attempts - 1:
            sleeper(1)
    return False
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/test_dingtalk_sender.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add dingtalk_sender.py tests/test_dingtalk_sender.py
git commit -m "feat: 钉钉 ActionCard 推送（含重试）"
```

---

## Task 5: 56yorky 客户端 yorky_client.py

**Files:**
- Create: `yorky_client.py`
- Test: `tests/test_yorky_client.py`

**Interfaces:**
- Consumes: `Config.yorky`（base_url/api_key/page_size/page_sleep_seconds）
- Produces: `class YorkyClient`，构造 `YorkyClient(base_url, api_key, page_size, page_sleep_seconds, poster=requests, sleeper=time.sleep)`；
  方法 `fetch_all_tracks() -> list[dict]`，内部 `offset` 递增、每页后 `sleeper(sleep)`、返回 < page_size 时停止；
  属性 `self.fetch_succeeded: bool` —— 仅当至少一页返回 `code==200` 时为 True（用于区分"API 全挂"与"确实无在途单"）。

- [ ] **Step 1: 写失败测试 tests/test_yorky_client.py**

```python
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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_yorky_client.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'yorky_client'`）

- [ ] **Step 3: 实现 yorky_client.py**

```python
from __future__ import annotations
import logging
import requests
import time

log = logging.getLogger(__name__)


class YorkyClient:
    def __init__(self, base_url: str, api_key: str, page_size: int = 100,
                 page_sleep_seconds: float = 2.0, poster=requests,
                 sleeper=time.sleep, max_pages: int = 1000):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.page_size = page_size
        self.page_sleep_seconds = page_sleep_seconds
        self.poster = poster
        self.sleeper = sleeper
        self.max_pages = max_pages
        self.fetch_succeeded = False

    def _fetch_page(self, offset: int) -> tuple[list[dict], bool]:
        url = f"{self.base_url}/api/depot/expand/trackList/push"
        headers = {"apiKey": self.api_key, "Content-Type": "application/json"}
        body = {"limit": self.page_size, "offset": offset}
        resp = self.poster.post(url, json=body, headers=headers, timeout=30)
        data = resp.json()
        if data.get("code") != 200:
            log.error("56yorky 返回非200: %s", data.get("message"))
            return [], False
        return (data.get("data") or {}).get("list") or [], True

    def fetch_all_tracks(self) -> list[dict]:
        all_rows: list[dict] = []
        offset = 0
        for _ in range(self.max_pages):
            rows, ok = self._fetch_page(offset)
            if ok:
                self.fetch_succeeded = True
            if not rows:
                break
            all_rows.extend(rows)
            self.sleeper(self.page_sleep_seconds)  # 遵守 2 秒/次限速
            if len(rows) < self.page_size:
                break
            offset += self.page_size
        return all_rows
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/test_yorky_client.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add yorky_client.py tests/test_yorky_client.py
git commit -m "feat: 56yorky 分页拉取客户端（含限速）"
```

---

## Task 6: 报表生成 report_builder.py

**Files:**
- Create: `report_builder.py`
- Test: `tests/test_report_builder.py`

**Interfaces:**
- Consumes: `Config.filter`
- Produces: `@dataclass ReportData`（`title:str, markdown:str, in_transit_count:int, is_empty:bool`）；
  `class ReportBuilder`，构造 `ReportBuilder(exclude_track_status, exclude_delivery_status, long_tail_threshold, today=...)`，
  方法 `build(records: list[dict]) -> ReportData`。

- [ ] **Step 1: 写失败测试 tests/test_report_builder.py**

```python
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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_report_builder.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'report_builder'`）

- [ ] **Step 3: 实现 report_builder.py**

```python
from __future__ import annotations
from dataclasses import dataclass

PROBLEM_KEYWORDS = ("问题", "异常")


@dataclass
class ReportData:
    title: str
    markdown: str
    in_transit_count: int
    is_empty: bool


class ReportBuilder:
    def __init__(self, exclude_track_status: list[int], exclude_delivery_status: list[str],
                 long_tail_threshold: int = 50, today: str = ""):
        self.exclude_track_status = set(exclude_track_status)
        self.exclude_delivery_status = set(exclude_delivery_status)
        self.long_tail_threshold = long_tail_threshold
        self.today = today

    def _is_problem(self, r: dict) -> bool:
        if r.get("deliveryStatus") == "W":
            return True
        text = f"{r.get('trackStatusText', '')} {r.get('trackDesc', '')}"
        return any(k in text for k in PROBLEM_KEYWORDS)

    def _is_excluded(self, r: dict) -> bool:
        if r.get("trackStatus") in self.exclude_track_status:
            return True
        if r.get("deliveryStatus") in self.exclude_delivery_status:
            return True
        return False

    def _truncate(self, s: str, n: int = 40) -> str:
        s = (s or "").replace("\n", " ").strip()
        return s if len(s) <= n else s[:n] + "…"

    def build(self, records: list[dict]) -> ReportData:
        in_transit = [r for r in records if not self._is_excluded(r)]
        title = f"📦 每日转运状态报表（{self.today}）"

        if not in_transit:
            return ReportData(title=title, markdown="✅ 今日全部已送达，无在途单",
                              in_transit_count=0, is_empty=True)

        problem = [r for r in in_transit if self._is_problem(r)]
        normal = [r for r in in_transit if not self._is_problem(r)]

        # 普通组按 trackStatusText 聚合
        groups: dict[str, list[dict]] = {}
        for r in normal:
            key = r.get("trackStatusText") or "未知"
            groups.setdefault(key, []).append(r)

        # 超长只发概要
        if len(in_transit) > self.long_tail_threshold:
            md_parts = [f"> 共 **{len(in_transit)}** 单在途"]
            if problem:
                md_parts.append(f"\n\n**🔴 问题件（{len(problem)}）**")
            for gname, items in groups.items():
                md_parts.append(f"\n\n**{gname}（{len(items)}）**")
            md = "".join(md_parts)
            return ReportData(title=title, markdown=md,
                              in_transit_count=len(in_transit), is_empty=False)

        def table(items: list[dict]) -> str:
            rows = ["| 客户单号 | 渠道 | 国家 | 转运状态 | 最新轨迹 | 时间 |",
                    "|---|---|---|---|---|---|"]
            for r in items:
                rows.append("| {} | {} | {} | {} | {} | {} |".format(
                    r.get("userNo", ""), r.get("serviceName", ""),
                    r.get("countryText", ""), r.get("trackStatusText", ""),
                    self._truncate(r.get("trackDesc", "")), r.get("trackTime", "")))
            return "\n".join(rows)

        md_parts = [f"> 共 **{len(in_transit)}** 单在途"]
        if problem:
            md_parts.append(f"\n\n**🔴 问题件（{len(problem)}）**\n\n" + table(problem))
        for gname, items in groups.items():
            md_parts.append(f"\n\n**{gname}（{len(items)}）**\n\n" + table(items))

        return ReportData(title=title, markdown="".join(md_parts),
                          in_transit_count=len(in_transit), is_empty=False)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/test_report_builder.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add report_builder.py tests/test_report_builder.py
git commit -m "feat: 在途过滤、分组与 Markdown 报表生成"
```

---

## Task 7: 编排入口 main.py（含 --dry-run）

**Files:**
- Create: `main.py`

**Interfaces:**
- Consumes: `load_config`（Task 2）、`YorkyClient`（Task 5）、`ReportBuilder`（Task 6）、`send_action_card`（Task 4）。
- 退出码：成功 0；致命失败（配置/拉取/推送）非 0。

- [ ] **Step 1: 实现 main.py**

```python
from __future__ import annotations
import argparse
import logging
import sys
from datetime import date
from pathlib import Path

from config import load_config
from yorky_client import YorkyClient
from report_builder import ReportBuilder, ReportData
from dingtalk_sender import send_action_card


def setup_logging(log_dir: str):
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    log_file = Path(log_dir) / f"{date.today().isoformat()}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(log_file, encoding="utf-8"), logging.StreamHandler()],
    )


def run(config_path: str, dry_run: bool) -> int:
    log = logging.getLogger("main")
    try:
        cfg = load_config(config_path)
    except Exception as e:
        logging.error("配置加载失败: %s", e)
        return 2
    setup_logging(cfg.logging.dir)

    today = date.today().isoformat()
    client = YorkyClient(cfg.yorky.base_url, cfg.yorky.api_key,
                         cfg.yorky.page_size, cfg.yorky.page_sleep_seconds)
    records = client.fetch_all_tracks()
    log.info("共拉取 %d 条轨迹记录（fetch_succeeded=%s）",
             len(records), client.fetch_succeeded)

    rb = ReportBuilder(cfg.filter.exclude_track_status,
                       cfg.filter.exclude_delivery_status,
                       cfg.filter.long_tail_threshold, today=today)
    report = rb.build(records)

    # 区分"API 全挂"与"确实无在途单"
    if not records and not client.fetch_succeeded:
        report = ReportData(
            title=f"⚠️ 转运日报拉取失败（{today}）",
            markdown="⚠️ 56yorky 数据拉取失败，请检查 apiKey / 网络 / 接口状态。",
            in_transit_count=0, is_empty=True)

    log.info("在途 %d 单", report.in_transit_count)

    if dry_run:
        print(f"[DRY-RUN] title={report.title}")
        print(report.markdown)
        return 0

    ok = send_action_card(cfg.dingtalk.webhook, cfg.dingtalk.secret,
                          report.title, report.markdown,
                          "查看 56yorky 后台", cfg.dingtalk.backend_url)
    if ok:
        log.info("钉钉推送成功")
        return 0
    log.error("钉钉推送失败")
    return 1


def main():
    ap = argparse.ArgumentParser(description="56yorky 转运日报 → 钉钉")
    ap.add_argument("-c", "--config", default="config.yaml")
    ap.add_argument("--dry-run", action="store_true", help="不发钉钉、不调真实API的样本预览")
    args = ap.parse_args()
    sys.exit(run(args.config, args.dry_run))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 本地 dry-run 联调（不调真实API/钉钉）**

由于 `--dry-run` 仍会调用真实 API 拉取（仅不推送），做一次"无 config 时报错"冒烟：

Run: `python main.py --config does_not_exist.yaml`
Expected: 控制台输出 `配置加载失败: ...`，退出码 2。

Run: `echo "exit code:"; python main.py --config does_not_exist.yaml; echo $?`
Expected: `exit code:` 后跟 `2`

- [ ] **Step 3: 全量测试回归**

Run: `python -m pytest tests/ -v`
Expected: 全部通过（config 3 + sign 3 + sender 3 + yorky 4 + report 6 = 19）

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "feat: 编排入口 main.py 与 dry-run 开关"
```

---

## Task 8: Windows 定时任务脚本

**Files:**
- Create: `run_daily.bat`
- Create: `install_task.ps1`
- Create: `README.md`

**Interfaces:**
- `run_daily.bat`：切到脚本目录，运行 `python main.py`，写日志。
- `install_task.ps1`：用 `schtasks` 注册每日 10:00 任务，任务名 `YorkyDingTalkReport`。

- [ ] **Step 1: 创建 run_daily.bat**

```bat
@echo off
chcp 65001 >nul
cd /d "%~dp0"
python main.py -c config.yaml
exit /b %ERRORLEVEL%
```

- [ ] **Step 2: 创建 install_task.ps1**

```powershell
# 以当前用户身份注册每日 10:00 运行的计划任务
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Definition
$bat = Join-Path $here "run_daily.bat"
$taskName = "YorkyDingTalkReport"

# 若已存在先删除
schtasks /Query /TN $taskName >$null 2>&1
if ($?) {
    Write-Host "任务已存在，先删除..."
    schtasks /Delete /TN $taskName /F
}

schtasks /Create /TN $taskName /TR "\"$bat\"" /SC DAILY /ST 10:00 /F
Write-Host "已注册任务 $taskName，每日 10:00 运行 $bat"
Write-Host "查看: schtasks /Query /TN $taskName /V /FO LIST"
```

- [ ] **Step 3: 创建 README.md**

```markdown
# 56yorky 转运状态日报 → 钉钉

每天 10:00 拉取 56yorky 在途入仓单轨迹，生成 ActionCard 报表推送到钉钉群。

## 配置
1. 复制 `config.example.yaml` 为 `config.yaml`
2. 填入 `yorky.api_key`、`dingtalk.webhook`、`dingtalk.secret`
3. 安装依赖：`python -m pip install -r requirements.txt`

## 测试
`python -m pytest tests/ -v`

## 手动运行
- 本地预览（不发钉钉）：`python main.py --dry-run`
- 正式运行：`python main.py`

## 注册每日定时任务（Windows）
以管理员或当前用户运行 PowerShell：
`powershell -ExecutionPolicy Bypass -File install_task.ps1`
查看：`schtasks /Query /TN YorkyDingTalkReport /V /FO LIST`

## 钉钉机器人加签密钥获取
群设置 → 智能群助手 → 添加机器人 → 自定义 → 安全设置勾选"加签" → 复制 Secret 与 Webhook。
```

- [ ] **Step 4: 验证 bat 能找到 python 并报缺失配置（冒烟）**

Run: `cmd /c run_daily.bat`
Expected: 退出码 2，日志/控制台提示配置缺失（因为 config.yaml 不存在）。

Run: `echo exit=$?`（bash 下读取上一条退出码）
Expected: `exit=2`

- [ ] **Step 5: Commit**

```bash
git add run_daily.bat install_task.ps1 README.md
git commit -m "feat: Windows 定时任务脚本与说明文档"
```

---

## Task 9: 真实联调与验收

**Files:** 无新建（用户填 config.yaml 后联调）

**Interfaces:** 无

- [ ] **Step 1: 提示用户填写 config.yaml**

告知用户：复制 `config.example.yaml` → `config.yaml`，填入真实 apiKey、webhook、secret。

- [ ] **Step 2: dry-run 预览真实数据**

Run: `python main.py --dry-run`
Expected: 打印 title 与 Markdown，能看到在途单分组与表格。

- [ ] **Step 3: 正式推送一次**

Run: `python main.py`
Expected: 钉钉群收到 ActionCard；`logs/<今天>.log` 记录"钉钉推送成功"。

- [ ] **Step 4: 注册定时任务**

由用户在 PowerShell 运行：`powershell -ExecutionPolicy Bypass -File install_task.ps1`
Run（验证）: `schtasks /Query /TN YorkyDingTalkReport /V /FO LIST`
Expected: 显示任务 `YorkyDingTalkReport`，下次运行时间次日 10:00。

- [ ] **Step 5: 记录结果并提交（如有调整）**

```bash
git add -A
git commit -m "chore: 联调验收完成"  # 仅当有改动时
```
