# tests/test_rhythm_checklist.py
# -*- coding: utf-8 -*-
import json, subprocess, sys
from pathlib import Path
from scripts.build_rhythm_checklist import render, DEFAULT_JSON

def test_render_contains_framework():
    cfg = json.loads(DEFAULT_JSON.read_text(encoding="utf-8"))
    html = render(cfg)
    for kw in ["决策门", "窗口期", "硬性循环", "风险值守", "复盘总闸",
               "localStorage", "@media print"]:
        assert kw in html
    n = sum(len(v) for v in cfg["groups"].values())
    assert html.count('type="checkbox"') == n

def test_cli_generates_html(tmp_path):
    out = tmp_path / "o"
    subprocess.run([sys.executable, "-X", "utf8", "scripts/build_rhythm_checklist.py",
                    "--out", str(out)], check=True,
                   cwd=str(Path(__file__).resolve().parent.parent))
    assert (out / "管理节奏控制图-常态期.html").exists()
