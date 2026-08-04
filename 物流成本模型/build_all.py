# -*- coding: utf-8 -*-
"""
物流中心 DAP 成本模型生成器
============================
数据源: full_table.json (从物流中心费用汇总表导出)
输出:
  - 物流成本全景.html             (★ 主输出: KPI + 目标对比 + 云图 + 结论)
  - 成本云图_G系列_M系列.html    (G/M/N系列气泡云图 + 德/美分线卡片)
  - 物流中心费用_汇报.html        (DAP全路线单台成本汇总 + 目标对比)

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
from build_panorama import build as build_panorama

# ---- config ----
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, 'data', 'full_table.json')
OUT_CLOUD = os.path.join(BASE_DIR, 'output', '成本云图_G系列_M系列.html')
OUT_REPORT = os.path.join(BASE_DIR, 'output', '物流中心费用_汇报.html')
OUT_PANORAMA = os.path.join(BASE_DIR, 'output', '物流成本全景.html')

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
            f"{{label:'{r['origin']}->{r['dest']} {r['area']}', A:{r['A']},B:{r['B']},C:{r['C']},D:{r['D']},E:{r['E']}}}"
            for r in mr
        )
        series_data[model] = routes_js

    pcs_map = {'G系列': '462', 'M系列': '574', 'N系列': '330'}
    color_map = {'G系列': '#2563eb', 'M系列': '#2563eb', 'N系列': '#7c3aed'}

    html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>成本云图 - G / M / N系列</title>
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
  <div class="meta">按产品系列 - 单台成本结构可视化 - 2026年8月</div>
</div>
<div class="clouds">
'''

    for model in ['G系列', 'M系列', 'N系列']:
        html += f'''
<div class="cloud-card">
  <h2 style="color:{color_map[model]}">{model}</h2>
  <div class="sub">单柜{pcs_map[model]}pcs - 各路线单台成本结构均值</div>
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
<footer>物流中心 - DAP成本云图 - 2026-08-04</footer>
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
    svg+=`<text x="${b.x}" y="${b.y+b.r*0.2}" text-anchor="middle" fill="rgba(255,255,255,0.9)" font-size="${fs-2}" font-weight="600">&yen;${b.val}</text>`;
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
    html+=`<div class="route-item de"><div class="route-label">${r.label.replace('深圳->德国 ','').replace('越南->德国 ','')}</div><div class="route-value">&yen;${total}</div><div class="route-sub">${r.label.startsWith('深圳')?'深圳':'越南'} - 头程${Math.round(r.A/total*100)}% - 尾程${Math.round(r.E/total*100)}%</div></div>`;
  });
  html+=`<div class="route-item" style="background:#f0fdf4;border:2px solid #bbf7d0;"><div class="route-label">德国 均值</div><div class="route-value" style="font-size:20px;">&yen;${avgTotal(deRoutes)}</div><div class="route-sub">${deRoutes.length}条路线</div></div>`;
  html+=`</div></div>`;

  html+=`<div class="route-group"><span class="route-group-label us">美国</span><div class="route-cards">`;
  usRoutes.forEach(r=>{
    const total=keys.reduce((s,k)=>s+r[k],0);
    const short=r.label.replace('深圳->美国 ','').replace('越南->美国 ','');
    html+=`<div class="route-item us"><div class="route-label">${short}</div><div class="route-value">&yen;${total}</div><div class="route-sub">${r.label.startsWith('深圳')?'深圳':'越南'} - 头程${Math.round(r.A/total*100)}% - 尾程${Math.round(r.E/total*100)}%</div></div>`;
  });
  html+=`<div class="route-item" style="background:#fef2f2;border:2px solid #fecaca;"><div class="route-label">美国 均值</div><div class="route-value" style="font-size:20px;">&yen;${avgTotal(usRoutes)}</div><div class="route-sub">${usRoutes.length}条路线</div></div>`;
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
        vals = [r['total'] for r in pu if r['dest'] == dest and r['origin'] == origin and r['total'] > 0]
        return sum(vals) / len(vals) if vals else 0

    sz_de_avg = avg_pu('深圳', '德国')
    vn_de_avg = avg_pu('越南', '德国')

    # Get C-warehouse cabinet rows for cost structure bars
    cab_de_c = [r for r in rows if r['dest'] == '德国' and '柜子' in r['unit'] and r['area'] == 'C端谷仓']

    # ---- target price config ----
    TARGET_EUR = 35
    EXCHANGE_RATE = 7.85
    TARGET_RMB = TARGET_EUR * EXCHANGE_RATE  # ~275 RMB

    # ---- per-product averages (ALL routes) for target comparison ----
    model_stats = {}
    for model in ['G系列', 'M系列', 'N系列']:
        mr = [r for r in pu if r['model'] == model]
        if not mr: continue
        n = len(mr)
        avgA = sum(r['A'] for r in mr) / n
        avgB = sum(r['B'] for r in mr) / n
        avgC = sum(r['C'] for r in mr) / n
        avgD = sum(r['D'] for r in mr) / n
        avgE = sum(r['E'] for r in mr) / n
        avgTotal = avgA + avgB + avgC + avgD + avgE
        model_stats[model] = {
            'n': n, 'avgA': avgA, 'avgB': avgB, 'avgC': avgC, 'avgD': avgD, 'avgE': avgE,
            'avgTotal': avgTotal, 'gap': avgTotal - TARGET_RMB,
            'gapPct': (avgTotal - TARGET_RMB) / TARGET_RMB * 100
        }

    # Sort models by gap for ranking
    model_rank = sorted(model_stats.items(), key=lambda x: x[1]['gap'], reverse=True)

    # ---- build target comparison table data (group by model x origin) ----
    compare_groups = {}
    for r in pu:
        key = (r['dest'], r['model'])
        if key not in compare_groups:
            compare_groups[key] = []
        compare_groups[key].append(r)

    compare_rows = []
    dest_order = {'德国': 0, '美国': 1}
    model_order = {'G系列': 0, 'M系列': 1, 'N系列': 2}
    for (dest, model), grp in sorted(compare_groups.items(), key=lambda x: (dest_order.get(x[0][0], 9), model_order.get(x[0][1], 9))):
        n = len(grp)
        avgTotal = sum(r['total'] for r in grp) / n
        compare_rows.append({
            'dest': dest, 'model': model,
            'total': round(avgTotal), 'gap': round(avgTotal - TARGET_RMB),
            'gapPct': round((avgTotal - TARGET_RMB) / TARGET_RMB * 100)
        })

    # ---- generate conclusion text ----
    # Analyze by destination
    def dest_stats(dest_name):
        dr = [r for r in pu if r['dest'] == dest_name]
        if not dr: return None
        n = len(dr)
        avgs = {}
        for seg in ['A','B','C','D','E']:
            avgs[seg] = sum(r[seg] for r in dr) / n
        avgTotal = sum(r['total'] for r in dr) / n
        gap = avgTotal - TARGET_RMB
        gapPct = gap / TARGET_RMB * 100
        ae_share = (avgs['A'] + avgs['E']) / avgTotal * 100
        return {'n': n, 'avgs': avgs, 'avgTotal': avgTotal, 'gap': gap,
                'gapPct': gapPct, 'ae_share': ae_share}

    de_stats = dest_stats('德国')
    us_stats = dest_stats('美国')
    seg_names = {'A': '头程费用', 'B': '上架操作费', 'C': '仓储费', 'D': '出库操作费', 'E': '尾程运费'}

    # Germany model breakdown
    de_models = []
    for model in ['G系列', 'M系列', 'N系列']:
        mr = [r for r in pu if r['dest'] == '德国' and r['model'] == model]
        if mr:
            avg = sum(r['total'] for r in mr) / len(mr)
            de_models.append((model, avg, avg - TARGET_RMB, (avg - TARGET_RMB) / TARGET_RMB * 100))

    # US model breakdown
    us_models = []
    for model in ['G系列', 'M系列', 'N系列']:
        mr = [r for r in pu if r['dest'] == '美国' and r['model'] == model]
        if mr:
            avg = sum(r['total'] for r in mr) / len(mr)
            us_models.append((model, avg, avg - TARGET_RMB, (avg - TARGET_RMB) / TARGET_RMB * 100))

    # Best/worst in Germany
    de_best = min(de_models, key=lambda x: x[1]) if de_models else None
    de_worst = max(de_models, key=lambda x: x[1]) if de_models else None

    # Germany gap description
    de_gap_text = ''
    if de_stats:
        de_gap_text = f'德国路线均值 <strong>{de_stats["avgTotal"]:,.0f} RMB</strong> (超出目标{de_stats["gap"]:+,.0f}, +{de_stats["gapPct"]:.0f}%)'
        if de_best and de_best[3] <= 0:
            de_gap_text += f'，其中 <span class="highlight-blue">{de_best[0]} {de_best[1]:.0f} RMB 已低于目标</span>'

    # US gap description
    us_gap_text = ''
    if us_stats:
        us_gap_text = f'美国路线均值 <strong>{us_stats["avgTotal"]:,.0f} RMB</strong> (超出目标{us_stats["gap"]:+,.0f}, +{us_stats["gapPct"]:.0f}%)，全线远超目标'

    # Germany recommendation
    de_rec = ''
    if de_stats:
        de_a_share = de_stats['avgs']['A'] / de_stats['avgTotal'] * 100
        de_e_share = de_stats['avgs']['E'] / de_stats['avgTotal'] * 100
        de_rec = f'头程占{de_a_share:.0f}%、尾程占{de_e_share:.0f}%。海运头程成本可控，'
        if de_best and de_best[3] <= 0:
            de_rec += f'以达标产品{de_best[0]}为标杆优化{de_worst[0]}；'
        de_rec += '关注尾程快递费率谈判及E段末端配送效率'

    # US recommendation
    us_rec = ''
    if us_stats:
        us_a_share = us_stats['avgs']['A'] / us_stats['avgTotal'] * 100
        us_e_share = us_stats['avgs']['E'] / us_stats['avgTotal'] * 100
        us_rec = f'头程(海运)占{us_a_share:.0f}%、尾程(快递)占{us_e_share:.0f}%，为德国同段的2-3倍。优先评估美线海运集拼/合约价优化及尾程卡车替代方案'

    html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>物流中心费用汇总 - 汇报看板</title>
<style>
  :root { --bg:#f0f2f5;--card:#fff;--text:#1a1a2e;--muted:#6b7280;--blue:#2563eb;--blue-bg:#eff6ff;--red:#ef4444;--red-bg:#fef2f2;--amber:#d97706;--amber-bg:#fffbeb;--shadow:0 1px 3px rgba(0,0,0,0.06); }
  * { box-sizing:border-box;margin:0;padding:0; }
  body { font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;background:var(--bg);color:var(--text);line-height:1.5; }
  .container { max-width:1200px;margin:0 auto;padding:28px 24px; }
  .header { display:flex;align-items:flex-end;justify-content:space-between;margin-bottom:28px;flex-wrap:wrap;gap:12px; }
  .header h1 { font-size:24px;font-weight:700; }
  .header .meta { font-size:13px;color:var(--muted); }
  .tag { padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600; }
  .tag-blue { background:var(--blue-bg);color:var(--blue); }
  .tag-blue { background:var(--blue-bg);color:var(--blue); }
  .tag-red { background:var(--red-bg);color:var(--red); }
  .kpi-grid { display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:24px; }
  .kpi { background:var(--card);border-radius:10px;padding:16px 18px;box-shadow:var(--shadow); }
  .kpi-label { font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px; }
  .kpi-value { font-size:28px;font-weight:700; }
  .kpi-sub { font-size:11px;color:var(--muted);margin-top:2px; }
  .kpi.blue .kpi-value{color:var(--blue);}
  .kpi.amber .kpi-value{color:var(--amber);}
  .kpi.red .kpi-value{color:var(--red);}
  .kpi.blue .kpi-value{color:var(--blue);}
  .alert { border-radius:8px;padding:12px 16px;margin-bottom:20px;font-size:13px;background:var(--amber-bg);border:1px solid #fde68a;color:#92400e; }
  .card { background:var(--card);border-radius:10px;padding:20px 22px;margin-bottom:18px;box-shadow:var(--shadow); }
  .card-header { display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;flex-wrap:wrap;gap:8px; }
  .card-title { font-size:15px;font-weight:600; }
  .section-de { border-left:4px solid var(--blue); }
  .table-wrap { overflow-x:auto; }
  table { width:100%;border-collapse:collapse;font-size:12px;min-width:700px; }
  th { padding:8px;text-align:center;font-weight:600;color:#555;background:#f9fafb;border-bottom:2px solid #e5e7eb;font-size:11px;white-space:nowrap; }
  td { padding:6px 8px;text-align:center;border-bottom:1px solid #f3f4f6;white-space:nowrap; }
  tr:hover td{background:#fafbfc;}
  .text-left{text-align:left;}
  .num{font-family:"SF Mono","Consolas",monospace;font-size:11px;}
  .strong{font-weight:600;}
  .over{color:var(--red);font-weight:600;}
  .bar-wrap{display:flex;align-items:center;gap:8px;margin:2px 0;font-size:11px;}
  .bar-label{width:48px;text-align:right;flex-shrink:0;color:#888;}
  .bar-track{flex:1;height:14px;background:#f3f4f6;border-radius:7px;overflow:hidden;}
  .bar-fill{height:100%;border-radius:7px;}
  .bar-fill.a{background:#86efac;}.bar-fill.b{background:#93c5fd;}.bar-fill.c{background:#fde68a;}.bar-fill.d{background:#fdba74;}.bar-fill.e{background:#c4b5fd;}
  .bar-val{width:80px;font-family:"SF Mono",monospace;font-size:10px;}
  .conclusion-section{margin-top:12px;}
  .conclusion-block{margin-bottom:16px;padding-bottom:16px;border-bottom:1px solid #f3f4f6;}
  .conclusion-block:last-child{border-bottom:none;margin-bottom:0;padding-bottom:0;}
  .conclusion-block h4{font-size:14px;margin-bottom:6px;display:flex;align-items:center;gap:6px;}
  .conclusion-block p{font-size:13px;color:#555;line-height:1.7;}
  .conclusion-block .icon{font-size:18px;}
  .highlight-red{color:var(--red);font-weight:600;}
  .highlight-blue{color:var(--blue);font-weight:600;}
  .highlight-amber{color:var(--amber);font-weight:600;}
  footer{text-align:center;color:#aaa;font-size:11px;margin-top:28px;}
</style>
</head>
<body>
<div class="container">
<div class="header">
  <div><h1>物流中心费用汇总 RMB</h1><div class="meta">DAP全路线成本分析 - 目标对比 - 2026年8月</div></div>
  <div class="tag tag-blue">DAP 条款</div>
</div>
'''

    # ---- KPI row 1: origin x destination ----
    html += f'''
<div class="kpi-grid">
  <div class="kpi blue"><div class="kpi-label">深圳 -> 德国 DAP</div><div class="kpi-value">{sz_de_avg:,.0f}</div><div class="kpi-sub">G/M/N系列单台均值 RMB</div></div>
  <div class="kpi amber"><div class="kpi-label">越南 -> 德国 DAP</div><div class="kpi-value">{vn_de_avg:,.0f}</div><div class="kpi-sub">G/M/N系列单台均值 RMB</div></div>
  <div class="kpi blue"><div class="kpi-label">全段目标价 (DAP)</div><div class="kpi-value">{TARGET_EUR} EUR</div><div class="kpi-sub">= {TARGET_RMB:,.0f} RMB/台 (汇率 7.85)</div></div>
</div>


<div class="alert"><strong>说明：</strong>目标价 35EUR 为全段端到端 DAP 目标（含头程->上架->仓储->出库->尾程）。以下数据覆盖全部 DAP 路线（德国+美国）。</div>
'''

    # ---- Target comparison table ----
    html += f'''
<div class="card">
  <div class="card-header"><div class="card-title">目标对比明细 - 按目的地 x 产品</div><span class="tag tag-red">目标: {TARGET_EUR}EUR = {TARGET_RMB:,.0f} RMB</span></div>
  <div class="table-wrap"><table>
    <thead><tr><th>目的地</th><th>产品</th><th>单台合计</th><th>目标</th><th>差距</th><th>超幅</th></tr></thead>
    <tbody>
'''
    max_gap = max(abs(cr['gapPct']) for cr in compare_rows) if compare_rows else 100
    for cr in compare_rows:
        bar_color = '#ef4444' if cr['gap'] > 0 else '#3b82f6'
        bar_pct = min(abs(cr['gapPct']) / max(max_gap, 1) * 100, 100)
        over_class = 'over' if cr['gap'] > 0 else 'under'
        html += f'<tr><td class="text-left strong">{cr["dest"]}</td><td>{cr["model"]}</td><td class="num strong {over_class}">{cr["total"]:,}</td><td class="num">{TARGET_RMB:,.0f}</td><td class="num {over_class}">{cr["gap"]:+,}</td><td style="min-width:180px;"><div style="display:flex;align-items:center;gap:8px;"><div style="flex:1;height:18px;background:#f3f4f6;border-radius:9px;overflow:hidden;"><div style="height:100%;width:{bar_pct:.0f}%;background:{bar_color};border-radius:9px;"></div></div><span class="{over_class}" style="font-size:12px;font-weight:600;min-width:48px;text-align:right;">{cr["gapPct"]:+,}%</span></div></td></tr>\n'
    html += '</tbody></table></div></div>\n'

    # ---- Conclusion ----
    html += f'''
<div class="card">
  <div class="card-header"><div class="card-title">结论与建议</div><span class="tag tag-blue">自检分析</span></div>
  <div class="conclusion-section">

    <div class="conclusion-block">
    <h4><span class="icon">1</span> 德国路线</h4>
    <p>{de_gap_text}。{de_rec}。</p>
    </div>

    <div class="conclusion-block">
    <h4><span class="icon">2</span> 美国路线</h4>
    <p>{us_gap_text}。{us_rec}。</p>
    </div>

    <div class="conclusion-block">
    <h4><span class="icon">3</span> 综合结论</h4>
    <p>德国路线整体可控，M系列已达标可作为成本标杆；美国路线头程+尾程为核心矛盾，需从运输方案层面突破。B/C/D段(仓储操作)占比小，维持现状即可。</p>
    </div>

  </div>
</div>

<footer>物流中心 - 成本分析 - 2026-08-04</footer>
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

    print('Building combined panorama...')
    panorama_html = build_panorama()
    with open(OUT_PANORAMA, 'w', encoding='utf-8') as f:
        f.write(panorama_html)
    print(f'  -> {OUT_PANORAMA} ({len(panorama_html):,} chars)')

    print('Done.')
