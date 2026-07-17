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
