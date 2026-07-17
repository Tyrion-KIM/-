import textwrap
import pytest
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
    bad = VALID.replace("  api_key: abc123\n", "")
    with pytest.raises(ValueError):
        load_config(write(tmp_path, bad))


def test_defaults_when_optional_missing(tmp_path):
    no_filter = VALID.replace(
        "  exclude_track_status: [2]\n  exclude_delivery_status: [\"C\"]\n  long_tail_threshold: 50\n",
        "")
    cfg = load_config(write(tmp_path, no_filter))
    assert cfg.filter.exclude_track_status == [2]
    assert cfg.filter.long_tail_threshold == 50
