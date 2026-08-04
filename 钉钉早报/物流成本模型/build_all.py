# -*- coding: utf-8 -*-
"""
物流中心 DAP 成本模型生成器
============================
数据源: full_table.json (从物流中心费用汇总表导出)
输出:
  - 成本云图_G系列_M系列.html    (G/M/N系列气泡云图 + 德/美分线卡片)
  - 物流中心费用_汇报.html        (DAP德国路线单台成本汇总)

使用方法:
  1. 更新 full_table.json (从在线表格导出)
  2. 运行: python build_all.py
  3. 打开生成的 HTML 文件查看

数据映射规则 (2026-08-04 确认):
  A(头程) = col[7] + col[8] + col[11]    (内陆+报关 + 主运费 + 目的港)
  B(上架) = C端:col[13]  /  B端:col[15]
  C(仓储) = C端:col[17]  /  B端:col[18]
  D(出库) = C端:col[20]  /  B端:col[19]
  E(尾程) = C端:col[21](快递)  /  B端:col[24](卡车)
"""

import json, sys, os

# ---- config ----
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, 'full_table.json')
OUT_CLOUD = os.path.join(BASE_DIR, '成本云图_G系列_M系列.html')
OUT_REPORT = os.path.join(BASE_DIR, '物流中心费用_汇报.html')

# ---- helpers ----
def num(v):
    if v is None or v == '' or v == '/': return 0
    try: return float(str(v).replace(',', ''))
    except: return 0

def load_data():
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        raw = json.load(f)
    cells = raw['cells']
    rows = []
    for i in range(4, len(cells)):
        row = cells[i]
        if len(row) < 26: continue
        vals = [c.get('value', '') for c in row]
        clause = str(vals[0]).strip()
        unit   = str(vals[1]).strip()
        if clause != 'DAP': continue
        origin = str(vals[3]).strip()
        dest   = str(vals[4]).strip()
        area   = str(vals[5]).strip()
        model  = str(vals[6]).strip()

        A = num(vals[7]) + num(vals[8]) + num(vals[11])
        if 'C端' in area:
            B = num(vals[13]); C = num(vals[17]); D = num(vals[20]); E = num(vals[21])
        elif 'B端' in area:
            B = num(vals[15]); C = num(vals[18]); D = num(vals[19]); E = num(vals[24])
        else:  # 美东/美西
            B = num(vals[13]) if num(vals[13]) else num(vals[15])
            C = num(vals[17]) if num(vals[17]) else num(vals[18])
            D = num(vals[20]) if num(vals[20]) else num(vals[19])
            E = num(vals[21]) if num(vals[21]) else num(vals[24])

        total = A + B + C + D + E
        pcs = 1
        if 'pcs' in unit:
            try: pcs = int(unit.split('（')[1].split('pcs')[0])
            except: pcs = 1

        per_unit = num(vals[25]) if vals[25] else total
        rows.append({
            'clause': clause, 'unit': unit, 'origin': origin, 'dest': dest,
            'area': area, 'model': model, 'pcs': pcs,
            'A': round(A), 'B': round(B), 'C': round(C), 'D': round(D), 'E': round(E),
            'total': round(total), 'per_unit': round(per_unit),
        })
    return rows

def per_unit_rows(rows):
    return [r for r in rows if '单产品' in r['unit']]

# ---- build cloud chart HTML ----
def build_cloud(rows):
    pu = per_unit_rows(rows)
    series_data = {}
    for model in ['G系列', 'M系列', 'N系列']:
        mr = [r for r in pu if r['model'] == model]
        routes_js = ',\n    '.join(
            f"{{label:'{r['origin']}→{r['dest']} {r['area']}', A:{r['A']},B:{r['B']},C:{r['C']},D:{r['D']},E:{r['E']}}}"
            for r in mr
        )
        series_data[model] = routes_js

    # Get pcs info
    pcs_map = {'G系列': '462', 'M系列': '574', 'N系列': '330'}
    color_map = {'G系列': '#059669', 'M系列': '#2563eb', 'N系列': '#7c3aed'}

    html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>成本云图 · G / M / N系列</title>
<style>
  :root { --bg:#f0f2f5;--card:#fff;--text:#1a1a2e;--muted:#6b7280;--shadow:0 1px 3px rgba(0,0,0,0.06); }
  * { box-sizing:border-box;margin:0;padding:0; }
  body { font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;background:var(--bg);color:var(--text);line-height:1.5; }
  .container { max-width:1440px;margin:0 auto;padding:28px 24px; }
  .header { text-align:center;margin-bottom:32px; }
  .header h1 { font-size:26px;font-weight:700;margin-bottom:6px; }
  .header .meta { font-size:13px;color:var(--muted); }
  .clouds { display:grid;grid-template-columns:repeat(3,1fr);gap:20px; }
  @media(max-width:1200px){.clouds{grid-template-columns:1fr 1fr;}}
  @media(max-width:750px){.clouds{grid-template-columns:1fr;}}
  .cloud-card { background:var(--card);border-radius:14px;padding:24px;box-shadow:var(--shadow); }
  .cloud-card h2 { font-size:20px;text-align:center;margin-bottom:4px; }
  .cloud-card .sub { text-align:center;font-size:12px;color:var(--muted);margin-bottom:16px; }
  .cloud-area { position:relative;width:100%;height:500px; }
  .cloud-area svg { width:100%;height:100%; }
  .legend { display:flex;justify-content:center;gap:20px;margin-top:16px;flex-wrap:wrap; }
  .legend-item { display:flex;align-items:center;gap:6px;font-size:12px; }
  .legend-dot { width:12px;height:12px;border-radius:50%; }
  .route-group { margin-top:18px; }
  .route-group-label { font-size:12px;font-weight:700;padding:5px 10px;border-radius:5px;display:inline-block;margin-bottom:8px; }
  .route-group-label.de { background:#dcfce7;color:#166534; }
  .route-group-label.us { background:#fee2e7;color:#991b1b; }
  .route-cards { display:grid;grid-template-columns:repeat(auto-fit,minmax(155px,1fr));gap:8px; }
  .route-item { background:#f9fafb;border-radius:8px;padding:8px 10px;text-align:center; }
  .route-item .route-label { font-size:10px;color:var(--muted);margin-bottom:2px; }
  .route-item .route-value { font-size:17px;font-weight:700; }
  .route-item .route-sub { font-size:10px;color:var(--muted); }
  .route-item.de { border-left:3px solid #86efac; }
  .route-item.us { border-left:3px solid #fca5a5; }
  footer { text-align:center;color:#aaa;font-size:11px;margin-top:32px; }
</style>
</head>
<body>
<div class="container">
<div class="header">
  <h1>物流中心 DAP 成本云图</h1>
  <div class="meta">按产品系列 · 单台成本结构可视化 · 2026年8月</div>
</div>
<div class="clouds">
'''

    for model in ['G系列', 'M系列', 'N系列']:
        html += f'''
<div class="cloud-card">
  <h2 style="color:{color_map[model]}">{model}</h2>
  <div class="sub">单柜{pcs_map[model]}pcs · 各路线单台成本结构均值</div>
  <div class="cloud-area" id="{model[0].lower()}cloud"></div>
  <div class="legend">
    <div class="legend-item"><span class="legend-dot" style="background:#86efac"></span>A 头程费用</div>
    <div class="legend-item"><span class="legend-dot" style="background:#93c5fd"></span>B 上架操作</div>
    <div class="legend-item"><span class="legend-dot" style="background:#fde68a"></span>C 仓储费</div>
    <div class="legend-item"><span class="legend-dot" style="background:#fdba74"></span>D 出库操作</div>
    <div class="legend-item"><span class="legend-dot" style="background:#c4b5fd"></span>E 尾程运费</div>
  </div>
  <div id="{model[0].lower()}-routes"></div>
</div>'''

    html += '''
</div>
<footer>物流中心 · DAP成本云图 · 2026-08-04</footer>
</div>
<script>
'''

    for model in ['G系列', 'M系列', 'N系列']:
        key = model[0].lower()
        html += f"const {key}Data={{name:'{model}',routes:[\n    {series_data[model]}\n]}};\n"

    html += '''
const colors={A:'#86efac',B:'#93c5fd',C:'#fde68a',D:'#fdba74',E:'#c4b5fd'};
const colorDark={A:'#16a34a',B:'#2563eb',C:'#ca8a04',D:'#ea580c',E:'#7c3aed'};
const keys=['A','B','C','D','E'];
const labels={A:'头程费用',B:'上架操作',C:'仓储费',D:'出库操作',E:'尾程运费'};

function avgCosts(routes){
  const sums={A:0,B:0,C:0,D:0,E:0};
  routes.forEach(r=>{keys.forEach(k=>sums[k]+=r[k]);});
  const total=keys.reduce((s,k)=>s+sums[k],0);
  const result={};
  keys.forEach(k=>{result[k]={val:Math.round(sums[k]/routes.length),pct:Math.round(sums[k]/total*100)};});
  return result;
}

function drawCloud(containerId,routes){
  const container=document.getElementById(containerId);
  const W=container.clientWidth||600,H=500,cx=W/2,cy=H/2;
  const avg=avgCosts(routes);
  const items=keys.map(k=>({key:k,val:avg[k].val,pct:avg[k].pct,label:labels[k]})).sort((a,b)=>b.val-a.val);
  const maxVal=items[0].val,maxR=110,minR=35;
  const bubbles=items.map((it,i)=>{
    const r=minR+Math.sqrt(it.val/maxVal)*(maxR-minR);
    return{...it,r};
  });
  bubbles[0].x=cx;bubbles[0].y=cy;
  const pos=[{dx:-120,dy:-80},{dx:130,dy:-50},{dx:-100,dy:100},{dx:110,dy:90}];
  for(let i=1;i<bubbles.length;i++){bubbles[i].x=cx+pos[i-1].dx;bubbles[i].y=cy+pos[i-1].dy;}

  let svg=`<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">`;
  for(let i=1;i<bubbles.length;i++){
    svg+=`<line x1="${bubbles[0].x}" y1="${bubbles[0].y}" x2="${bubbles[i].x}" y2="${bubbles[i].y}" stroke="#e5e7eb" stroke-width="1.5" stroke-dasharray="4,3"/>`;
  }
  bubbles.forEach(b=>{
    const gid=`grad-${containerId}-${b.key}`;
    svg+=`<defs><radialGradient id="${gid}" cx="35%" cy="30%"><stop offset="0%" stop-color="${colors[b.key]}" stop-opacity="0.95"/><stop offset="100%" stop-color="${colorDark[b.key]}" stop-opacity="0.9"/></radialGradient></defs>`;
    svg+=`<circle cx="${b.x+2}" cy="${b.y+3}" r="${b.r}" fill="rgba(0,0,0,0.06)"/>`;
    svg+=`<circle cx="${b.x}" cy="${b.y}" r="${b.r}" fill="url(#${gid})" stroke="${colorDark[b.key]}" stroke-width="1.5"/>`;
    const fs=Math.max(10,b.r*0.22);
    svg+=`<text x="${b.x}" y="${b.y-b.r*0.12}" text-anchor="middle" fill="#fff" font-size="${fs+2}" font-weight="700">${b.label}</text>`;
    svg+=`<text x="${b.x}" y="${b.y+b.r*0.2}" text-anchor="middle" fill="rgba(255,255,255,0.9)" font-size="${fs-2}" font-weight="600">¥${b.val}</text>`;
    svg+=`<text x="${b.x}" y="${b.y+b.r*0.42}" text-anchor="middle" fill="rgba(255,255,255,0.8)" font-size="${Math.max(9,fs-4)}">${b.pct}%</text>`;
  });
  svg+='</svg>';
  container.innerHTML=svg;
  return avg;
}

function drawRouteCards(containerId,routes){
  const container=document.getElementById(containerId);
  const deRoutes=routes.filter(r=>r.label.includes('德国'));
  const usRoutes=routes.filter(r=>r.label.includes('美东')||r.label.includes('美西'));

  function avgTotal(rs){
    if(!rs.length)return 0;
    return Math.round(rs.reduce((s,r)=>s+keys.reduce((a,k)=>a+r[k],0),0)/rs.length);
  }

  let html='';
  html+=`<div class="route-group"><span class="route-group-label de">德国</span><div class="route-cards">`;
  deRoutes.forEach(r=>{
    const total=keys.reduce((s,k)=>s+r[k],0);
    html+=`<div class="route-item de"><div class="route-label">${r.label.replace('深圳→德国 ','').replace('越南→德国 ','')}</div><div class="route-value">¥${total}</div><div class="route-sub">${r.label.startsWith('深圳')?'深圳':'越南'} · 头程${Math.round(r.A/total*100)}% · 尾程${Math.round(r.E/total*100)}%</div></div>`;
  });
  html+=`<div class="route-item" style="background:#f0fdf4;border:2px solid #bbf7d0;"><div class="route-label">德国 均值</div><div class="route-value" style="font-size:20px;">¥${avgTotal(deRoutes)}</div><div class="route-sub">${deRoutes.length}条路线</div></div>`;
  html+=`</div></div>`;

  html+=`<div class="route-group"><span class="route-group-label us">美国</span><div class="route-cards">`;
  usRoutes.forEach(r=>{
    const total=keys.reduce((s,k)=>s+r[k],0);
    const short=r.label.replace('深圳→美国 ','').replace('越南→美国 ','');
    html+=`<div class="route-item us"><div class="route-label">${short}</div><div class="route-value">¥${total}</div><div class="route-sub">${r.label.startsWith('深圳')?'深圳':'越南'} · 头程${Math.round(r.A/total*100)}% · 尾程${Math.round(r.E/total*100)}%</div></div>`;
  });
  html+=`<div class="route-item" style="background:#fef2f2;border:2px solid #fecaca;"><div class="route-label">美国 均值</div><div class="route-value" style="font-size:20px;">¥${avgTotal(usRoutes)}</div><div class="route-sub">${usRoutes.length}条路线</div></div>`;
  html+=`</div></div>`;

  container.innerHTML=html;
}
'''

    for model in ['G系列', 'M系列', 'N系列']:
        key = model[0].lower()
        html += f"drawCloud('{key}cloud',{key}Data.routes);\ndrawRouteCards('{key}-routes',{key}Data.routes);\n"

    html += '</script>\n</body>\n</html>'
    return html

# ---- build summary report HTML ----
def build_report(rows):
    pu = per_unit_rows(rows)
    dap_de = sorted(
        [r for r in pu if r['dest'] == '德国'],
        key=lambda r: (r['model'], r['origin'], r['area'])
    )

    def avg_pu(origin, dest):
        vals = [r['per_unit'] for r in pu if r['dest'] == dest and r['origin'] == origin and r['per_unit'] > 0]
        return sum(vals) / len(vals) if vals else 0

    sz_de_avg = avg_pu('深圳', '德国')
    vn_de_avg = avg_pu('越南', '德国')

    # Get C-warehouse cabinet rows for cost structure bars
    cab_de_c = [r for r in rows if r['dest'] == '德国' and '柜子' in r['unit'] and r['area'] == 'C端谷仓']

    html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>物流中心费用汇总 · 汇报看板</title>
<style>
  :root { --bg:#f0f2f5;--card:#fff;--text:#1a1a2e;--muted:#6b7280;--green:#059669;--green-bg:#ecfdf5;--red:#dc2626;--red-bg:#fef2f2;--amber:#d97706;--amber-bg:#fffbeb;--blue:#2563eb;--blue-bg:#eff6ff;--shadow:0 1px 3px rgba(0,0,0,0.06); }
  * { box-sizing:border-box;margin:0;padding:0; }
  body { font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;background:var(--bg);color:var(--text);line-height:1.5; }
  .container { max-width:1200px;margin:0 auto;padding:28px 24px; }
  .header { display:flex;align-items:flex-end;justify-content:space-between;margin-bottom:28px;flex-wrap:wrap;gap:12px; }
  .header h1 { font-size:24px;font-weight:700; }
  .header .meta { font-size:13px;color:var(--muted); }
  .tag { padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600; }
  .tag-green { background:var(--green-bg);color:var(--green); }
  .tag-blue { background:var(--blue-bg);color:var(--blue); }
  .kpi-grid { display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:24px; }
  .kpi { background:var(--card);border-radius:10px;padding:16px 18px;box-shadow:var(--shadow); }
  .kpi-label { font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px; }
  .kpi-value { font-size:28px;font-weight:700; }
  .kpi-sub { font-size:11px;color:var(--muted);margin-top:2px; }
  .kpi.green .kpi-value{color:var(--green);}
  .kpi.amber .kpi-value{color:var(--amber);}
  .kpi.blue .kpi-value{color:var(--blue);}
  .alert { border-radius:8px;padding:12px 16px;margin-bottom:20px;font-size:13px;background:var(--amber-bg);border:1px solid #fde68a;color:#92400e; }
  .card { background:var(--card);border-radius:10px;padding:20px 22px;margin-bottom:18px;box-shadow:var(--shadow); }
  .card-header { display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;flex-wrap:wrap;gap:8px; }
  .card-title { font-size:15px;font-weight:600; }
  .section-de { border-left:4px solid var(--green); }
  .table-wrap { overflow-x:auto; }
  table { width:100%;border-collapse:collapse;font-size:12px;min-width:700px; }
  th { padding:8px;text-align:center;font-weight:600;color:#555;background:#f9fafb;border-bottom:2px solid #e5e7eb;font-size:11px;white-space:nowrap; }
  td { padding:6px 8px;text-align:center;border-bottom:1px solid #f3f4f6;white-space:nowrap; }
  tr:hover td{background:#fafbfc;}
  .text-left{text-align:left;}
  .num{font-family:"SF Mono","Consolas",monospace;font-size:11px;}
  .strong{font-weight:600;}
  .bar-wrap{display:flex;align-items:center;gap:8px;margin:2px 0;font-size:11px;}
  .bar-label{width:48px;text-align:right;flex-shrink:0;color:#888;}
  .bar-track{flex:1;height:14px;background:#f3f4f6;border-radius:7px;overflow:hidden;}
  .bar-fill{height:100%;border-radius:7px;}
  .bar-fill.a{background:#86efac;}.bar-fill.b{background:#93c5fd;}.bar-fill.c{background:#fde68a;}.bar-fill.d{background:#fdba74;}.bar-fill.e{background:#c4b5fd;}
  .bar-val{width:80px;font-family:"SF Mono",monospace;font-size:10px;}
  .summary-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px;margin-top:12px;}
  .summary-item{padding:14px 16px;border-radius:8px;font-size:13px;line-height:1.7;}
  .summary-item.de{background:var(--green-bg);border:1px solid #a7f3d0;}
  .summary-item.us{background:var(--red-bg);border:1px solid #fecaca;}
  .summary-item h4{font-size:14px;margin-bottom:4px;}
  footer{text-align:center;color:#aaa;font-size:11px;margin-top:28px;}
</style>
</head>
<body>
<div class="container">
<div class="header">
  <div><h1>物流中心费用汇总 RMB</h1><div class="meta">DAP德国路线成本分析 · 2026年8月</div></div>
  <div class="tag tag-blue">DAP 条款</div>
</div>
'''

    html += f'''
<div class="kpi-grid">
  <div class="kpi green"><div class="kpi-label">深圳 → 德国 DAP</div><div class="kpi-value">{sz_de_avg:,.0f}</div><div class="kpi-sub">G/M/N系列单台均值 RMB</div></div>
  <div class="kpi amber"><div class="kpi-label">越南 → 德国 DAP</div><div class="kpi-value">{vn_de_avg:,.0f}</div><div class="kpi-sub">G/M/N系列单台均值 RMB</div></div>
  <div class="kpi blue"><div class="kpi-label">DDP 目标价</div><div class="kpi-value">15€</div><div class="kpi-sub">约 118 RMB/台 (7.85)</div></div>
</div>

<div class="alert"><strong>说明：</strong>以下为DAP德国路线数据。美国路线（美东/美西）详见成本云图。</div>
'''

    # DAP per-unit table
    html += '''
<div class="card section-de">
  <div class="card-header"><div class="card-title">DAP 德国路线 · 单台成本</div><span class="tag tag-green">RMB/台</span></div>
  <div class="table-wrap"><table>
    <thead><tr><th>产品</th><th>产地</th><th>区域</th><th>头程</th><th>上架</th><th>仓储</th><th>出库</th><th>尾程</th><th>合计</th></tr></thead>
    <tbody>
'''
    for r in dap_de:
        html += f'<tr><td class="text-left strong">{r["model"]}</td><td>{r["origin"]}</td><td>{r["area"]}</td><td class="num">{r["A"]}</td><td class="num">{r["B"]}</td><td class="num">{r["C"]}</td><td class="num">{r["D"]}</td><td class="num">{r["E"]}</td><td class="num strong">{r["A"]+r["B"]+r["C"]+r["D"]+r["E"]}</td></tr>\n'
    html += '</tbody></table></div></div>\n'

    # Cost structure bars
    html += '<div class="card"><div class="card-header"><div class="card-title">成本结构（C端谷仓 · 单柜）</div></div>'
    for r in cab_de_c:
        t = r['A'] + r['B'] + r['C'] + r['D'] + r['E']
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

    # Summary
    html += f'''
<div class="card"><div class="card-header"><div class="card-title">汇报结论</div></div>
<div class="summary-grid">
  <div class="summary-item de"><h4>德国路线（DAP）</h4><p>深圳→德国单台 <strong>{sz_de_avg:,.0f} RMB</strong>，越南→德国单台 <strong>{vn_de_avg:,.0f} RMB</strong>。深圳产地成本优于越南（内陆+头程差异显著）。头程费用为最大成本项，C端尾程次之。</p></div>
  <div class="summary-item us"><h4>美国路线（DAP）</h4><p>美东/美西数据详见成本云图。美国海运头程显著高于德国铁路头程，尾程快递费占比高。</p></div>
</div></div>

<footer>物流中心 · 成本分析 · 2026-08-04</footer>
</div></body></html>
'''
    return html

# ---- main ----
if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    print('Loading data...')
    rows = load_data()
    print(f'  Loaded {len(rows)} DAP rows')

    print('Building cloud chart...')
    cloud_html = build_cloud(rows)
    with open(OUT_CLOUD, 'w', encoding='utf-8') as f:
        f.write(cloud_html)
    print(f'  -> {OUT_CLOUD} ({len(cloud_html):,} chars)')

    print('Building summary report...')
    report_html = build_report(rows)
    with open(OUT_REPORT, 'w', encoding='utf-8') as f:
        f.write(report_html)
    print(f'  -> {OUT_REPORT} ({len(report_html):,} chars)')

    print('Done.')
