# -*- coding: utf-8 -*-
import json, sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'C:\Users\LD1621\Desktop\钉钉早报\full_table.json', 'r', encoding='utf-8') as f:
    raw = json.load(f)

cells = raw['cells']

def num(v):
    if v is None or v == '' or v == '/': return 0
    try: return float(str(v).replace(',', ''))
    except: return 0

rows = []
for i in range(4, len(cells)):
    row = cells[i]
    if len(row) < 26: continue
    vals = [c.get('value', '') for c in row]
    clause  = str(vals[0]).strip()
    unit    = str(vals[1]).strip()
    origin  = str(vals[3]).strip()
    dest    = str(vals[4]).strip()
    area    = str(vals[5]).strip()
    model   = str(vals[6]).strip()

    A = num(vals[7]) + num(vals[8]) + num(vals[9]) + num(vals[10]) + num(vals[11]) + num(vals[12])
    B = num(vals[13]) + num(vals[15]) + num(vals[16])
    C = num(vals[17]) + num(vals[18])
    D = num(vals[19]) + num(vals[20])
    E = num(vals[21]) + num(vals[22]) + num(vals[23]) + num(vals[24])
    total = A + B + C + D + E

    pcs = 1
    if 'pcs' in unit:
        try: pcs = int(unit.split('\uff08')[1].split('pcs')[0])
        except: pcs = 1

    per_unit = num(vals[25]) if vals[25] else (total / pcs if pcs > 1 else total)

    rows.append({
        'clause': clause, 'unit': unit, 'origin': origin, 'dest': dest,
        'area': area, 'model': model, 'pcs': pcs,
        'A': A, 'B': B, 'C': C, 'D': D, 'E': E,
        'total': total, 'per_unit': per_unit,
    })

# DAP Germany per-unit rows
dap_de = sorted(
    [r for r in rows if r['clause']=='DAP' and r['dest']=='德国' and '单产品' in r['unit']],
    key=lambda r: (r['model'], r['origin'], r['area'])
)

# DAP Germany cabinet rows (C warehouse only, for cost structure bars)
dap_de_c_cab = [r for r in rows if r['clause']=='DAP' and r['dest']=='德国' and '柜子' in r['unit'] and r['area']=='C端谷仓']

# KPI: average per-unit by route
def avg_pu(origin, dest):
    vals = [r['per_unit'] for r in rows if r['clause']=='DAP' and r['dest']==dest and r['origin']==origin and '单产品' in r['unit'] and r['per_unit']>0]
    return sum(vals)/len(vals) if vals else 0

sz_de_avg = avg_pu('深圳', '德国')
vn_de_avg = avg_pu('越南', '德国')

html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>物流中心费用汇总 · 汇报看板</title>
<style>
  :root {
    --bg: #f0f2f5; --card: #ffffff; --text: #1a1a2e; --muted: #6b7280;
    --green: #059669; --green-bg: #ecfdf5; --red: #dc2626; --red-bg: #fef2f2;
    --amber: #d97706; --amber-bg: #fffbeb; --blue: #2563eb; --blue-bg: #eff6ff;
    --shadow: 0 1px 3px rgba(0,0,0,0.06);
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif; background: var(--bg); color: var(--text); line-height: 1.5; }
  .container { max-width: 1200px; margin: 0 auto; padding: 28px 24px; }
  .header { display: flex; align-items: flex-end; justify-content: space-between; margin-bottom: 28px; flex-wrap: wrap; gap: 12px; }
  .header h1 { font-size: 24px; font-weight: 700; }
  .header .meta { font-size: 13px; color: var(--muted); }
  .tag { padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; white-space: nowrap; }
  .tag-green { background: var(--green-bg); color: var(--green); }
  .tag-blue { background: var(--blue-bg); color: var(--blue); }

  .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 24px; }
  .kpi { background: var(--card); border-radius: 10px; padding: 16px 18px; box-shadow: var(--shadow); }
  .kpi-label { font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }
  .kpi-value { font-size: 28px; font-weight: 700; }
  .kpi-sub { font-size: 11px; color: var(--muted); margin-top: 2px; }
  .kpi.green .kpi-value { color: var(--green); }
  .kpi.amber .kpi-value { color: var(--amber); }
  .kpi.blue .kpi-value { color: var(--blue); }

  .alert { border-radius: 8px; padding: 12px 16px; margin-bottom: 20px; font-size: 13px; background: var(--amber-bg); border: 1px solid #fde68a; color: #92400e; }

  .card { background: var(--card); border-radius: 10px; padding: 20px 22px; margin-bottom: 18px; box-shadow: var(--shadow); }
  .card-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; flex-wrap: wrap; gap: 8px; }
  .card-title { font-size: 15px; font-weight: 600; }

  .table-wrap { overflow-x: auto; }
  table { width: 100%; border-collapse: collapse; font-size: 12px; min-width: 700px; }
  th { padding: 8px; text-align: center; font-weight: 600; color: #555; background: #f9fafb; border-bottom: 2px solid #e5e7eb; font-size: 11px; white-space: nowrap; }
  td { padding: 6px 8px; text-align: center; border-bottom: 1px solid #f3f4f6; white-space: nowrap; }
  tr:hover td { background: #fafbfc; }
  .text-left { text-align: left; }
  .num { font-family: "SF Mono", "Consolas", monospace; font-size: 11px; }
  .strong { font-weight: 600; }

  .section-de { border-left: 4px solid var(--green); }

  .bar-wrap { display: flex; align-items: center; gap: 8px; margin: 2px 0; font-size: 11px; }
  .bar-label { width: 48px; text-align: right; flex-shrink: 0; color: #888; }
  .bar-track { flex: 1; height: 14px; background: #f3f4f6; border-radius: 7px; overflow: hidden; }
  .bar-fill { height: 100%; border-radius: 7px; }
  .bar-fill.a { background: #86efac; } .bar-fill.b { background: #93c5fd; } .bar-fill.c { background: #fde68a; } .bar-fill.d { background: #fdba74; } .bar-fill.e { background: #c4b5fd; }
  .bar-val { width: 80px; font-family: "SF Mono", monospace; font-size: 10px; }

  .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; margin-top: 12px; }
  .summary-item { padding: 14px 16px; border-radius: 8px; font-size: 13px; line-height: 1.7; }
  .summary-item.de { background: var(--green-bg); border: 1px solid #a7f3d0; }
  .summary-item.us { background: var(--red-bg); border: 1px solid #fecaca; }
  .summary-item h4 { font-size: 14px; margin-bottom: 4px; }

  footer { text-align: center; color: #aaa; font-size: 11px; margin-top: 28px; }
</style>
</head>
<body>
<div class="container">

<div class="header">
  <div>
    <h1>物流中心费用汇总 RMB</h1>
    <div class="meta">DAP德国路线成本分析 · 2026年8月3日</div>
  </div>
  <div class="tag tag-blue">DAP 条款</div>
</div>
'''

# KPI cards
html += f'''
<div class="kpi-grid">
  <div class="kpi green">
    <div class="kpi-label">深圳 → 德国 DAP</div>
    <div class="kpi-value">{sz_de_avg:,.0f}</div>
    <div class="kpi-sub">G/M/N系列单台均值 RMB</div>
  </div>
  <div class="kpi amber">
    <div class="kpi-label">越南 → 德国 DAP</div>
    <div class="kpi-value">{vn_de_avg:,.0f}</div>
    <div class="kpi-sub">G/M/N系列单台均值 RMB</div>
  </div>
  <div class="kpi blue">
    <div class="kpi-label">DDP 目标价</div>
    <div class="kpi-value">15€</div>
    <div class="kpi-sub">约 118 RMB/台 (7.85)</div>
  </div>
</div>

<div class="alert">
  <strong>说明：</strong>以下为DAP德国路线数据。美国路线（美东/美西）尾程费用待补充，暂不列入。
</div>
'''

# === DAP per-unit table (simplified) ===
html += '''
<div class="card section-de">
  <div class="card-header">
    <div class="card-title">DAP 德国路线 · 单台成本</div>
    <span class="tag tag-green">RMB/台</span>
  </div>
  <div class="table-wrap">
  <table>
    <thead>
      <tr><th>产品</th><th>产地</th><th>区域</th><th>头程</th><th>上架</th><th>仓储</th><th>出库</th><th>尾程</th><th>合计</th></tr>
    </thead>
    <tbody>
'''

for r in dap_de:
    html += f'<tr><td class="text-left strong">{r["model"]}</td><td>{r["origin"]}</td><td>{r["area"]}</td><td class="num">{r["A"]/r["pcs"]:,.0f}</td><td class="num">{r["B"]/r["pcs"]:,.0f}</td><td class="num">{r["C"]/r["pcs"]:,.0f}</td><td class="num">{r["D"]/r["pcs"]:,.0f}</td><td class="num">{r["E"]/r["pcs"]:,.0f}</td><td class="num strong">{r["per_unit"]:,.0f}</td></tr>\n'

html += '</tbody></table></div></div>\n'

# === Cost structure bars (C warehouse only) ===
html += '''
<div class="card">
  <div class="card-header"><div class="card-title">成本结构（C端谷仓 · 单柜）</div></div>
'''

for r in dap_de_c_cab:
    t = r['A']+r['B']+r['C']+r['D']+r['E']
    if t == 0: continue
    pa, pb, pc, pd, pe = r['A']/t*100, r['B']/t*100, r['C']/t*100, r['D']/t*100, r['E']/t*100
    html += f'''<div style="margin-bottom:10px;">
      <div style="font-size:12px;margin-bottom:3px;"><strong>{r["origin"]} · {r["model"]} ({r["pcs"]}pcs)</strong> <span style="color:#888;">单台 {r["per_unit"]:,.0f} RMB</span></div>
      <div class="bar-wrap"><span class="bar-label">头程</span><div class="bar-track"><div class="bar-fill a" style="width:{max(pa,1):.0f}%"></div></div><span class="bar-val">{r['A']:,.0f} ({pa:.0f}%)</span></div>
      <div class="bar-wrap"><span class="bar-label">上架</span><div class="bar-track"><div class="bar-fill b" style="width:{max(pb,1):.0f}%"></div></div><span class="bar-val">{r['B']:,.0f} ({pb:.0f}%)</span></div>
      <div class="bar-wrap"><span class="bar-label">仓储</span><div class="bar-track"><div class="bar-fill c" style="width:{max(pc,1):.0f}%"></div></div><span class="bar-val">{r['C']:,.0f} ({pc:.0f}%)</span></div>
      <div class="bar-wrap"><span class="bar-label">出库</span><div class="bar-track"><div class="bar-fill d" style="width:{max(pd,1):.0f}%"></div></div><span class="bar-val">{r['D']:,.0f} ({pd:.0f}%)</span></div>
      <div class="bar-wrap"><span class="bar-label">尾程</span><div class="bar-track"><div class="bar-fill e" style="width:{max(pe,1):.0f}%"></div></div><span class="bar-val">{r['E']:,.0f} ({pe:.0f}%)</span></div>
    </div>'''

html += '</div>\n'

# === Summary ===
html += f'''
<div class="card">
  <div class="card-header"><div class="card-title">汇报结论</div></div>
  <div class="summary-grid">
    <div class="summary-item de">
      <h4>德国路线（DAP）</h4>
      <p>
        深圳→德国单台 <strong>{sz_de_avg:,.0f} RMB</strong>，越南→德国单台 <strong>{vn_de_avg:,.0f} RMB</strong>。<br>
        深圳产地成本优于越南（内陆+头程差异显著）。头程费用为最大成本项，C端尾程次之。
      </p>
    </div>
    <div class="summary-item us">
      <h4>美国路线（DAP）</h4>
      <p>
        美东/美西尾程数据尚未完善。已知美国海运头程(¥124,000-145,000/柜)显著高于德国(¥38,000-45,850/柜)。<br>
        建议尽快补齐数据后补充分析。
      </p>
    </div>
  </div>
</div>

<footer>物流中心 · 成本分析 · 2026-08-03</footer>
</div>
</body>
</html>
'''

out = r'C:\Users\LD1621\Desktop\钉钉早报\物流中心费用_汇报.html'
with open(out, 'w', encoding='utf-8') as f:
    f.write(html)
print(f'Done: {out} ({len(html):,} chars)')
