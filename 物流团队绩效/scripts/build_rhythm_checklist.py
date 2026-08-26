# scripts/build_rhythm_checklist.py
# -*- coding: utf-8 -*-
"""管控节奏打卡工具：控制点 JSON → 单文件 HTML 看板（打卡/进度/主题/打印）。
用法：python -X utf8 scripts/build_rhythm_checklist.py [--json scripts/control_points_default.json] [--out output/]"""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

DEFAULT_JSON = Path(__file__).resolve().parent / "control_points_default.json"
ROOT = Path(__file__).resolve().parent.parent
TYPES = ["决策门", "窗口期", "硬性循环", "风险值守"]
TYPE_NOTE = {
    "决策门": "管理拍板 · 错过不可逆",
    "窗口期": "错过即失效 · 不等人",
    "硬性循环": "每月自动转 · 盯执行",
    "风险值守": "人在即可 · 不做决策",
}

def render(cfg):
    gid = 0
    groups = ""
    for t in TYPES:
        items = cfg.get("groups", {}).get(t, [])
        if not items:
            continue
        rows = ""
        for it in items:
            gid += 1
            star = ' <span class="star">⭐</span>' if it.get("star") else ""
            rows += (f'<tr><td class="chk"><input type="checkbox" data-gid="{gid}">'
                     f'<span class="node">{it["node"]}{star}</span></td>'
                     f'<td>{it.get("time", "")}</td><td>{it["action"]}</td>'
                     f'<td class="cost">{it.get("cost", "")}</td></tr>')
        groups += (f'<section><h2>{t} <span class="note">{TYPE_NOTE[t]}</span></h2>'
                   f'<table><tr><th>节点</th><th>时间</th><th>管理动作</th><th>错过代价</th></tr>'
                   f'{rows}</table></section>')
    return f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<title>{cfg["title"]}</title><style>
:root{{--bg:#f6f7f9;--card:#fff;--ink:#1a1d21;--mut:#6b7280;--line:#e5e7eb;
--hdr:#1f4e79;--good:#0ca30c;--good-bg:#e7f8e7;--star:#b8860b}}
body{{background:var(--bg);color:var(--ink);font:14px/1.6 system-ui,-apple-system,"Segoe UI","Microsoft YaHei","PingFang SC",sans-serif;margin:0;padding:24px}}
.wrap{{max-width:920px;margin:0 auto}} h1{{font-size:20px;margin:0 0 4px}}
.mut{{color:var(--mut);font-size:12px}} .bar{{height:16px;background:var(--line);border-radius:8px;overflow:hidden;margin:10px 0 4px}}
.fill{{height:100%;background:var(--good);width:0}}
.prog{{font-weight:700}} section{{margin:18px 0}}
h2{{font-size:15px;margin:0 0 6px}} .note{{font-size:12px;color:var(--mut);font-weight:400}}
table{{border-collapse:collapse;width:100%;background:var(--card);border:1px solid var(--line);border-radius:8px}}
th,td{{padding:8px 10px;border-bottom:1px solid var(--line);text-align:left;font-size:13px;vertical-align:top}}
th{{background:var(--hdr);color:#fff}} .chk{{white-space:nowrap}} .node{{margin-left:6px}}
.star{{color:var(--star)}} .cost{{color:var(--mut);font-size:12px}}
button{{margin-left:8px;border:1px solid var(--line);background:var(--card);border-radius:6px;padding:3px 10px;cursor:pointer}}
@media (prefers-color-scheme: dark){{
:root:not([data-theme="light"]){{--bg:#0d0d0d;--card:#1a1a19;--ink:#fff;--mut:#c3c2b7;--line:#2c2c2a;--hdr:#123a5e;--good-bg:#0d2b0d}}}}
:root[data-theme="dark"]{{--bg:#0d0d0d;--card:#1a1a19;--ink:#fff;--mut:#c3c2b7;--line:#2c2c2a;--hdr:#123a5e;--good-bg:#0d2b0d}}
@media print{{.no-print{{display:none}} body{{background:#fff;color:#000;padding:0}}
table{{border:1px solid #000}} th{{background:#eee;color:#000}}
input[type=checkbox]{{accent-color:#000}}}}
</style></head><body><div class="wrap">
<h1>{cfg["title"]}</h1>
<div class="mut no-print">{cfg["window"]} ｜ 逐节点勾选打卡，进度存本浏览器</div>
<div class="no-print" style="margin:8px 0"><span class="prog" id="prog">0 / 0</span>
<button id="theme">主题</button></div>
<div class="bar no-print"><div class="fill" id="bar"></div></div>
{groups}
<script>
const KEY='rhythm:{cfg["title"]}';let st={{}};
try{{st=JSON.parse(localStorage.getItem(KEY)||'{{}}')}}catch(e){{}}
const cbs=[...document.querySelectorAll('input[type=checkbox]')];
function save(){{try{{localStorage.setItem(KEY,JSON.stringify(st))}}catch(e){{}}update()}}
function update(){{const n=cbs.filter(c=>c.checked).length;
document.getElementById('prog').textContent=n+' / '+cbs.length;
document.getElementById('bar').style.width=(n/cbs.length*100).toFixed(0)+'%'}}
cbs.forEach(cb=>{{cb.checked=!!st[cb.dataset.gid];
cb.addEventListener('change',()=>{{st[cb.dataset.gid]=cb.checked;save()}})}});
const th=['系统','浅色','深色'];let ti=0;
document.getElementById('theme').addEventListener('click',()=>{{
ti=(ti+1)%3;const v=th[ti];document.documentElement.dataset.theme=
v==='系统'?'':(v==='深色'?'dark':'light');document.getElementById('theme').textContent=v}});
update();
</script></div></body></html>"""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=str(DEFAULT_JSON))
    ap.add_argument("--out", default=str(ROOT / "output"))
    a = ap.parse_args()
    cfg = json.loads(Path(a.json).read_text(encoding="utf-8"))
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    f = out / f"{cfg['file']}.html"
    f.write_text(render(cfg), encoding="utf-8")
    print(f"saved: {f}")

if __name__ == "__main__":
    sys.exit(main())
