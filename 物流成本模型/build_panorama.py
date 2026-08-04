# -*- coding: utf-8 -*-
"""
物流成本全景 - 合并生成器
将成本云图 + 汇报看板合并为单一页面，统一蓝/红/橙色系
测试性质，不改变 build_all.py 定稿内容
"""
import json, sys, os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, 'data', 'full_table.json')
OUT_FILE = os.path.join(BASE_DIR, 'output', '物流成本全景.html')

# ---- helpers (same as build_all.py) ----
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
        unit = str(vals[1]).strip()
        if clause != 'DAP': continue
        origin = str(vals[3]).strip()
        dest = str(vals[4]).strip()
        area = str(vals[5]).strip()
        model = str(vals[6]).strip()
        A = num(vals[7]) + num(vals[8]) + num(vals[11]) + num(vals[12])
        if 'B端' in area:
            B = num(vals[15]) + num(vals[16])
            C = num(vals[18])
            D = num(vals[19])
            E = num(vals[24])
        elif 'C端' in area:
            B = num(vals[13]) + num(vals[14])
            C = num(vals[17])
            D = num(vals[20])
            E = num(vals[21])
        else:  # 美东 / 美西
            B = num(vals[13])
            C = num(vals[17])
            D = num(vals[20])
            E = num(vals[21])
        total = A + B + C + D + E
        pcs = 1
        if 'pcs' in unit:
            try: pcs = int(unit.split('（')[1].split('pcs')[0])
            except: pcs = 1
        rows.append({
            'origin': origin, 'dest': dest, 'area': area, 'model': model,
            'unit': unit, 'pcs': pcs,
            'A': round(A), 'B': round(B), 'C': round(C), 'D': round(D), 'E': round(E),
            'total': round(total),
        })
    return rows

def per_unit_rows(rows):
    return [r for r in rows if '单产品' in r['unit']]

# ---- build ----
def build():
    rows = load_data()
    pu = per_unit_rows(rows)

    TARGET_EUR = 36
    EXCHANGE_RATE = 7.85
    TARGET_RMB = round(TARGET_EUR * EXCHANGE_RATE)
    TARGET_BREAKDOWN = {'head': 15, 'tail': 15, 'other': 6}  # EUR 头程/尾程/其他

    # -- cloud chart data: grouped by (model, dest) --
    series_data = {}
    for model in ['G系列', 'M系列', 'N系列']:
        for dest in ['德国', '美国']:
            mr = [r for r in pu if r['model'] == model and r['dest'] == dest]
            key = f"{model[0].lower()}_{'de' if dest == '德国' else 'us'}"
            routes_js = ',\n    '.join(
                f"{{label:'{r['origin']}->{r['dest']} {r['area']}', A:{r['A']},B:{r['B']},C:{r['C']},D:{r['D']},E:{r['E']}}}"
                for r in mr
            )
            series_data[key] = (model, dest, routes_js, len(mr))

    pcs_map = {'G系列': '462', 'M系列': '574', 'N系列': '330'}
    model_color = {'G系列': '#2563eb', 'M系列': '#d97706', 'N系列': '#7c3aed'}

    # -- horizontal comparison data --
    compare_biz = []  # [{model, dest, biz, A, E, BCD, total, aPct, ePct}]
    for model in ['G系列', 'M系列', 'N系列']:
        for dest, biz_types in [('德国', ['C端谷仓', 'B端中转']), ('美国', ['美东', '美西'])]:
            for biz in biz_types:
                mr = [r for r in pu if r['model'] == model and r['dest'] == dest and r['area'] == biz]
                if not mr: continue
                n = len(mr)
                avgA = sum(r['A'] for r in mr) / n
                avgE = sum(r['E'] for r in mr) / n
                avgBCD = sum(r['B'] + r['C'] + r['D'] for r in mr) / n
                avgTotal = avgA + avgE + avgBCD
                compare_biz.append({
                    'model': model, 'dest': dest, 'biz': biz,
                    'A': round(avgA), 'E': round(avgE), 'BCD': round(avgBCD),
                    'total': round(avgTotal),
                    'aPct': round(avgA / avgTotal * 100) if avgTotal else 0,
                    'ePct': round(avgE / avgTotal * 100) if avgTotal else 0,
                    'bcdPct': round(avgBCD / avgTotal * 100) if avgTotal else 0,
                })

    # -- KPI --
    def avg_pu(origin, dest):
        vals = [r['total'] for r in pu if r['dest'] == dest and r['origin'] == origin and r['total'] > 0]
        return sum(vals) / len(vals) if vals else 0
    sz_de_avg = avg_pu('深圳', '德国')
    vn_de_avg = avg_pu('越南', '德国')
    sz_us_avg = avg_pu('深圳', '美国')
    vn_us_avg = avg_pu('越南', '美国')

    # -- target comparison --
    dest_order = {'德国': 0, '美国': 1}
    model_order = {'G系列': 0, 'M系列': 1, 'N系列': 2}
    compare_groups = {}
    for r in pu:
        key = (r['dest'], r['model'])
        compare_groups.setdefault(key, []).append(r)
    compare_rows = []
    for (dest, model), grp in sorted(compare_groups.items(),
            key=lambda x: (dest_order.get(x[0][0], 9), model_order.get(x[0][1], 9))):
        n = len(grp)
        avgTotal = sum(r['total'] for r in grp) / n
        compare_rows.append({
            'dest': dest, 'model': model,
            'total': round(avgTotal), 'gap': round(avgTotal - TARGET_RMB),
            'gapPct': round((avgTotal - TARGET_RMB) / TARGET_RMB * 100)
        })

    # -- conclusion --
    def dest_stats(dn):
        dr = [r for r in pu if r['dest'] == dn]
        if not dr: return None
        n = len(dr)
        avgs = {seg: sum(r[seg] for r in dr) / n for seg in ['A','B','C','D','E']}
        avgTotal = sum(r['total'] for r in dr) / n
        gap = avgTotal - TARGET_RMB
        return {'n': n, 'avgs': avgs, 'avgTotal': avgTotal, 'gap': gap, 'gapPct': gap / TARGET_RMB * 100}

    de_stats = dest_stats('德国')
    us_stats = dest_stats('美国')

    de_models = []
    for m in ['G系列', 'M系列', 'N系列']:
        mr = [r for r in pu if r['dest'] == '德国' and r['model'] == m]
        if mr:
            avg = sum(r['total'] for r in mr) / len(mr)
            de_models.append((m, avg, avg - TARGET_RMB, (avg - TARGET_RMB) / TARGET_RMB * 100))
    de_best = min(de_models, key=lambda x: x[1]) if de_models else None
    de_worst = max(de_models, key=lambda x: x[1]) if de_models else None

    de_gap = ''
    if de_stats:
        de_gap = f'德国路线均值 <strong>{de_stats["avgTotal"]:,.0f} RMB</strong> (超出目标{de_stats["gap"]:+,.0f}, +{de_stats["gapPct"]:.0f}%)'
        if de_best and de_best[3] <= 0:
            de_gap += f'，其中 <span class="hl-b">{de_best[0]} {de_best[1]:.0f} RMB 已低于目标</span>'
    de_rec = ''
    if de_stats:
        da = de_stats['avgs']['A'] / de_stats['avgTotal'] * 100
        de = de_stats['avgs']['E'] / de_stats['avgTotal'] * 100
        de_rec = f'海运头程占{da:.0f}%、尾程占{de:.0f}%。成本可控，'
        if de_best and de_best[3] <= 0:
            de_rec += f'以达标产品{de_best[0]}为标杆优化{de_worst[0]}；'
        de_rec += '关注尾程快递费率谈判及末端配送效率'

    us_gap = ''
    if us_stats:
        us_gap = f'美国路线均值 <strong>{us_stats["avgTotal"]:,.0f} RMB</strong> (超出目标{us_stats["gap"]:+,.0f}, +{us_stats["gapPct"]:.0f}%)，全线远超目标'
    us_rec = ''
    if us_stats:
        ua = us_stats['avgs']['A'] / us_stats['avgTotal'] * 100
        ue = us_stats['avgs']['E'] / us_stats['avgTotal'] * 100
        us_rec = f'头程(海运)占{ua:.0f}%、尾程(快递)占{ue:.0f}%，为德国同段的2-3倍。优先评估美线海运集拼/合约价优化及尾程卡车替代方案'

    # ---- HTML ----
    html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DAP 成本全景</title>
<style>
:root{--bg:#f0f2f5;--card:#fff;--text:#1a1a2e;--muted:#6b7280;--blue:#2563eb;--blue-bg:#eff6ff;--red:#ef4444;--red-bg:#fef2f2;--amber:#d97706;--amber-bg:#fffbeb;--shadow:0 1px 3px rgba(0,0,0,.06)}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;background:var(--bg);color:var(--text);line-height:1.5}
.container{max-width:1400px;margin:0 auto;padding:24px}
.page-title{text-align:center;margin-bottom:22px}
.page-title h1{font-size:24px;font-weight:700}
.page-title .meta{font-size:13px;color:var(--muted);margin-top:2px}
.kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:16px}
.kpi{background:var(--card);border-radius:10px;padding:14px 16px;box-shadow:var(--shadow)}
.kpi-label{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px}
.kpi-value{font-size:26px;font-weight:700}
.kpi-sub{font-size:11px;color:var(--muted);margin-top:2px}
.kpi.blue .kpi-value{color:var(--blue)}.kpi.amber .kpi-value{color:var(--amber)}.kpi.red .kpi-value{color:var(--red)}
.card{background:var(--card);border-radius:10px;padding:18px 20px;margin-bottom:16px;box-shadow:var(--shadow)}
.card-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;flex-wrap:wrap;gap:8px}
.card-title{font-size:14px;font-weight:600}
.tag{padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600}
.tag-blue{background:var(--blue-bg);color:var(--blue)}.tag-red{background:var(--red-bg);color:var(--red)}
table{width:100%;border-collapse:collapse;font-size:12px}
th{padding:7px;text-align:center;font-weight:600;color:#555;background:#f9fafb;border-bottom:2px solid #e5e7eb;font-size:11px;white-space:nowrap}
td{padding:5px 7px;text-align:center;border-bottom:1px solid #f3f4f6;white-space:nowrap}
tr:hover td{background:#fafbfc}
.tl{text-align:left}.num{font-family:"SF Mono",Consolas,monospace;font-size:11px}.b{font-weight:600}
.over{color:var(--red);font-weight:600}.under{color:var(--blue);font-weight:600}
.clouds{display:grid;grid-template-columns:repeat(2,1fr);gap:16px;margin-bottom:16px}
@media(max-width:1000px){.clouds{grid-template-columns:1fr}}
.cloud-card{background:var(--card);border-radius:12px;padding:20px;box-shadow:var(--shadow)}
.cloud-card h2{font-size:18px;text-align:center;margin-bottom:2px}
.cloud-card .sub{text-align:center;font-size:11px;color:var(--muted);margin-bottom:12px}
.cloud-area{position:relative;width:100%;height:310px}
.cloud-area svg{width:100%;height:100%}
.legend{display:flex;justify-content:center;gap:16px;margin-top:12px;flex-wrap:wrap}
.legend-item{display:flex;align-items:center;gap:6px;font-size:11px}
.legend-dot{width:10px;height:10px;border-radius:50%}
.route-group{margin-top:14px}
.rgl{font-size:11px;font-weight:700;padding:4px 8px;border-radius:4px;display:inline-block;margin-bottom:6px}
.rgl.de{background:#dbeafe;color:#1e40af}.rgl.us{background:#fee2e2;color:#991b1b}
.route-cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:6px}
.route-item{background:#f9fafb;border-radius:6px;padding:6px 8px;text-align:center}
.route-item .rl{font-size:9px;color:var(--muted);margin-bottom:1px}
.route-item .rv{font-size:15px;font-weight:700}
.route-item .rs{font-size:9px;color:var(--muted)}
.route-item.de{border-left:3px solid #93c5fd}.route-item.us{border-left:3px solid #fca5a5}
.conc-block{margin-bottom:14px;padding-bottom:14px;border-bottom:1px solid #f3f4f6}
.conc-block:last-child{border-bottom:none;margin-bottom:0;padding-bottom:0}
.conc-block h4{font-size:13px;margin-bottom:4px}
.conc-block p{font-size:12px;color:#555;line-height:1.7}
.hl-r{color:var(--red);font-weight:600}.hl-b{color:var(--blue);font-weight:600}
footer{text-align:center;color:#aaa;font-size:11px;margin-top:24px;padding-top:16px;border-top:1px solid #e5e7eb}
</style>
</head>
<body>
<div class="container">
<div class="page-title">
  <h1>DAP 成本全景</h1>
  <div class="meta">全路线端到端 | 目标 36EUR (头程15&euro;+尾程15&euro;+其他6&euro;) | 2026年8月</div>
</div>
'''

    # -- KPI --
    html += f'''
<div class="kpi-grid">
  <div class="kpi blue"><div class="kpi-label">深圳 → 德国 DAP</div><div class="kpi-value">{sz_de_avg:,.0f}</div><div class="kpi-sub">G/M/N单台均值 RMB</div></div>
  <div class="kpi amber"><div class="kpi-label">越南 → 德国 DAP</div><div class="kpi-value">{vn_de_avg:,.0f}</div><div class="kpi-sub">G/M/N单台均值 RMB</div></div>
  <div class="kpi red"><div class="kpi-label">深圳 → 美国 DAP</div><div class="kpi-value">{sz_us_avg:,.0f}</div><div class="kpi-sub">G/M/N单台均值 RMB</div></div>
  <div class="kpi amber"><div class="kpi-label">越南 → 美国 DAP</div><div class="kpi-value">{vn_us_avg:,.0f}</div><div class="kpi-sub">G/M/N单台均值 RMB</div></div>
  <div class="kpi blue"><div class="kpi-label">全段目标价 DAP</div><div class="kpi-value">{TARGET_EUR} EUR</div><div class="kpi-sub">头程{TARGET_BREAKDOWN["head"]}€ + 尾程{TARGET_BREAKDOWN["tail"]}€ + 其他{TARGET_BREAKDOWN["other"]}€ = {TARGET_RMB:,.0f} RMB (7.85)</div></div>
</div>
'''

    # -- Target comparison --
    max_gap = max(abs(cr['gapPct']) for cr in compare_rows) if compare_rows else 100
    html += f'''
<div class="card">
  <div class="card-header"><div class="card-title">目标对比 — 按目的地 x 产品</div><span class="tag tag-red">目标: {TARGET_EUR}EUR = {TARGET_RMB:,.0f} RMB</span></div>
  <table>
    <thead><tr><th>目的地</th><th>产品</th><th>单台合计</th><th>目标</th><th>差距</th><th>超幅</th></tr></thead>
    <tbody>
'''
    for cr in compare_rows:
        bc = '#ef4444' if cr['gap'] > 0 else '#2563eb'
        bp = min(abs(cr['gapPct']) / max(max_gap, 1) * 100, 100)
        oc = 'over' if cr['gap'] > 0 else 'under'
        html += f'<tr><td class="tl b">{cr["dest"]}</td><td>{cr["model"]}</td><td class="num b {oc}">{cr["total"]:,}</td><td class="num">{TARGET_RMB:,.0f}</td><td class="num {oc}">{cr["gap"]:+,}</td><td style="min-width:160px"><div style="display:flex;align-items:center;gap:6px"><div style="flex:1;height:16px;background:#f3f4f6;border-radius:8px;overflow:hidden"><div style="height:100%;width:{bp:.0f}%;background:{bc};border-radius:8px"></div></div><span class="{oc}" style="font-size:11px;font-weight:600;min-width:44px;text-align:right">{cr["gapPct"]:+,}%</span></div></td></tr>\n'
    html += '</tbody></table></div>\n'

    # -- Cloud charts: 3 models × 2 destinations = 6 cards --
    html += '<div class="clouds">\n'
    dest_colors = {'德国': '#2563eb', '美国': '#ef4444'}
    for model in ['G系列', 'M系列', 'N系列']:
        for dest in ['德国', '美国']:
            key = f"{model[0].lower()}_{'de' if dest == '德国' else 'us'}"
            _, _, _, n_routes = series_data[key]
            mid = key
            html += f'''
<div class="cloud-card">
  <h2 style="color:{dest_colors[dest]}">{model} — {dest}</h2>
  <div class="sub">{n_routes}条路线 | 单产品单台成本结构</div>
  <div class="cloud-area" id="{mid}cloud"></div>
  <div class="legend">
    <div class="legend-item"><span class="legend-dot" style="background:#93c5fd"></span>A 头程运费</div>
    <div class="legend-item"><span class="legend-dot" style="background:#60a5fa"></span>B 上架费</div>
    <div class="legend-item"><span class="legend-dot" style="background:#fcd34d"></span>C 仓储费</div>
    <div class="legend-item"><span class="legend-dot" style="background:#fb923c"></span>D 出库操作费</div>
    <div class="legend-item"><span class="legend-dot" style="background:#c084fc"></span>E 尾程运费</div>
  </div>
  <div id="{mid}-routes"></div>
</div>'''
    html += '</div>\n'

    # -- Cost breakdown reference --
    html += '''
<div class="card" style="padding:16px 20px">
  <div class="card-header"><div class="card-title">费用构成说明</div><span class="tag tag-blue">A/B/C/D/E 五段明细</span></div>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:10px;font-size:12px;line-height:1.8">
    <div><strong style="color:#2563eb">A 头程运费</strong><br><span style="color:#6b7280">内陆运费 + 报关费 + 港杂费 + 海运费 + 目的港港杂费 + 目的港拖车费</span></div>
    <div><strong style="color:#1d4ed8">B 海外仓上架费</strong><br><span style="color:#6b7280">海外仓卸柜费 + 入库清点费 + 海外仓上架费</span></div>
    <div><strong style="color:#ca8a04">C 仓储费</strong><br><span style="color:#6b7280">按货物存放<strong>90天</strong>计算得出</span></div>
    <div><strong style="color:#ea580c">D 出库操作费</strong><br><span style="color:#6b7280">C端仓库：下架 + 贴面单 + 收集SN<br>B端仓库：下架 + 收集SN + 打托 + 装柜</span></div>
    <div><strong style="color:#7c3aed">E 尾程运费</strong><br><span style="color:#6b7280">C端：本地快递费用 / B端：尾程卡车费用</span></div>
  </div>
</div>
'''

    # -- Horizontal comparison --
    de_rows = sorted([r for r in compare_biz if r['dest'] == '德国'], key=lambda x: x['total'], reverse=True)
    us_rows = sorted([r for r in compare_biz if r['dest'] == '美国'], key=lambda x: x['total'], reverse=True)
    max_total = max(r['total'] for r in compare_biz) if compare_biz else 1

    # target standard line values
    TGT_HEAD = round(TARGET_BREAKDOWN['head'] * EXCHANGE_RATE)
    TGT_TAIL = round(TARGET_BREAKDOWN['tail'] * EXCHANGE_RATE)
    TGT_OTHER = round(TARGET_BREAKDOWN['other'] * EXCHANGE_RATE)
    tgt_bar_pct = TARGET_RMB / max_total * 100
    tgt_a_w = TGT_HEAD / TARGET_RMB * tgt_bar_pct
    tgt_e_w = TGT_TAIL / TARGET_RMB * tgt_bar_pct
    tgt_o_w = tgt_bar_pct - tgt_a_w - tgt_e_w

    html += '''
<div class="card">
  <div class="card-header"><div class="card-title">横向对比 — 头程 / 尾程 成本结构</div><span class="tag tag-blue">产品 × 目的地 × 业务类型</span></div>
'''
    for label, rows in [('德国', de_rows), ('美国', us_rows)]:
        # target standard line
        html += f'''
  <div style="margin-bottom:14px">
    <h4 style="font-size:13px;margin-bottom:6px;color:#1e40af">{label}</h4>
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;font-size:11px">
      <div style="width:68px;text-align:right;font-weight:700;flex-shrink:0;color:#dc2626;font-size:10px">目标 36€</div>
      <div style="flex:1;height:14px;background:transparent;border-radius:7px;overflow:hidden;display:flex;max-width:700px;border:2px dashed #fca5a5">
        <div style="width:{tgt_a_w:.1f}%;background:rgba(37,99,235,0.25);display:flex;align-items:center;justify-content:center">
          <span style="color:#1e40af;font-size:9px;font-weight:700;white-space:nowrap">头{TGT_HEAD}({round(TGT_HEAD/TARGET_RMB*100)}%)</span>
        </div>
        <div style="width:{tgt_e_w:.1f}%;background:rgba(124,58,237,0.25);display:flex;align-items:center;justify-content:center">
          <span style="color:#7c3aed;font-size:9px;font-weight:700;white-space:nowrap">尾{TGT_TAIL}({round(TGT_TAIL/TARGET_RMB*100)}%)</span>
        </div>
        <div style="width:{tgt_o_w:.1f}%;background:rgba(217,119,6,0.25);display:flex;align-items:center;justify-content:center">
          <span style="color:#b45309;font-size:9px;font-weight:700;white-space:nowrap">其他{TGT_OTHER}({round(TGT_OTHER/TARGET_RMB*100)}%)</span>
        </div>
      </div>
      <div style="width:48px;font-weight:700;font-size:11px;flex-shrink:0;text-align:left;color:#dc2626">&yen;{TARGET_RMB}</div>
    </div>'''
        for r in rows:
            short = f"{r['model'][0]} {r['biz'].replace('谷仓','').replace('中转','')}"
            bar_pct = r['total'] / max_total * 100
            a_w = r['A'] / r['total'] * bar_pct
            e_w = r['E'] / r['total'] * bar_pct
            bcd_w = bar_pct - a_w - e_w
            html += f'''
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;font-size:12px">
      <div style="width:68px;text-align:right;font-weight:600;flex-shrink:0;font-size:11px">{short}</div>
      <div style="flex:1;height:18px;background:#f3f4f6;border-radius:9px;overflow:hidden;display:flex;position:relative;max-width:700px">
        <div style="width:{a_w:.1f}%;background:linear-gradient(90deg,#93c5fd,#3b82f6);border-radius:9px 0 0 9px;display:flex;align-items:center;justify-content:center;min-width:{ '0' if r['aPct'] < 10 else '40px'}">
          <span style="color:#fff;font-size:10px;font-weight:600;white-space:nowrap;padding:0 3px">头{r['A']}({r['aPct']}%)</span>
        </div>
        <div style="width:{e_w:.1f}%;background:linear-gradient(90deg,#c084fc,#7c3aed);display:flex;align-items:center;justify-content:center;min-width:{ '0' if r['ePct'] < 10 else '40px'}">
          <span style="color:#fff;font-size:10px;font-weight:600;white-space:nowrap;padding:0 3px">尾{r['E']}({r['ePct']}%)</span>
        </div>
        <div style="width:{bcd_w:.1f}%;background:linear-gradient(90deg,#fcd34d,#f59e0b);display:flex;align-items:center;justify-content:center;border-radius:0 9px 9px 0;min-width:{ '0' if r['bcdPct'] < 8 else '36px'}">
          <span style="color:#78350f;font-size:9px;font-weight:600;white-space:nowrap;padding:0 3px">其他{r['BCD']}({r['bcdPct']}%)</span>
        </div>
      </div>
      <div style="width:48px;font-weight:700;font-size:13px;flex-shrink:0;text-align:left">&yen;{r['total']}</div>
    </div>'''
        html += '</div>\n'

    html += '</div>\n'

    # -- Conclusion --
    html += f'''
<div class="card">
  <div class="card-header"><div class="card-title">结论与建议</div><span class="tag tag-blue">自检分析</span></div>
  <div class="conc-block"><h4>德国路线</h4><p>{de_gap}。{de_rec}。</p></div>
  <div class="conc-block"><h4>美国路线</h4><p>{us_gap}。{us_rec}。</p></div>
  <div class="conc-block"><h4>综合结论</h4><p>德国路线整体可控，M系列已达标可作为成本标杆；美国路线头程+尾程为核心矛盾。B/C/D段(仓储操作)占比小，维持现状。</p></div>
</div>
'''

    # -- JS --
    html += '''
<footer>物流中心 | DAP成本全景 | 2026-08-04</footer>
</div>
<script>
var colors={A:'#93c5fd',B:'#60a5fa',C:'#fcd34d',D:'#fb923c',E:'#c084fc'};
var cd={A:'#2563eb',B:'#1d4ed8',C:'#ca8a04',D:'#ea580c',E:'#7c3aed'};
var keys=['A','B','C','D','E'];
var labels={A:'头程运费',B:'上架费',C:'仓储费(90天)',D:'出库操作费',E:'尾程运费'};

function avgCosts(rs){
  var s={A:0,B:0,C:0,D:0,E:0};
  rs.forEach(function(r){keys.forEach(function(k){s[k]+=r[k]})});
  var t=keys.reduce(function(a,k){return a+s[k]},0);
  var o={};
  keys.forEach(function(k){o[k]={val:Math.round(s[k]/rs.length),pct:Math.round(s[k]/t*100)}});
  return o;
}

function drawCloud(cid,rs){
  var c=document.getElementById(cid);
  var W=c.clientWidth||500,H=380,cx=W/2,cy=H/2;
  var avg=avgCosts(rs);
  var items=keys.map(function(k){return{key:k,val:avg[k].val,pct:avg[k].pct,label:labels[k]}}).sort(function(a,b){return b.val-a.val});
  var maxVal=items[0].val,maxR=90,minR=28;
  var bubbles=items.map(function(it){var r=minR+Math.sqrt(it.val/maxVal)*(maxR-minR);return{key:it.key,val:it.val,pct:it.pct,label:it.label,r:r}});
  bubbles[0].x=cx;bubbles[0].y=cy;
  var pos=[{dx:-100,dy:-65},{dx:110,dy:-40},{dx:-85,dy:85},{dx:95,dy:75}];
  for(var i=1;i<bubbles.length;i++){bubbles[i].x=cx+pos[i-1].dx;bubbles[i].y=cy+pos[i-1].dy}
  var svg='<svg viewBox="0 0 '+W+' '+H+'" xmlns="http://www.w3.org/2000/svg">';
  for(var i=1;i<bubbles.length;i++){svg+='<line x1="'+bubbles[0].x+'" y1="'+bubbles[0].y+'" x2="'+bubbles[i].x+'" y2="'+bubbles[i].y+'" stroke="#e5e7eb" stroke-width="1" stroke-dasharray="4,3"/>'}
  bubbles.forEach(function(b){
    var gid='g-'+cid+'-'+b.key;
    svg+='<defs><radialGradient id="'+gid+'" cx="35%" cy="30%"><stop offset="0%" stop-color="'+colors[b.key]+'" stop-opacity="0.95"/><stop offset="100%" stop-color="'+cd[b.key]+'" stop-opacity="0.9"/></radialGradient></defs>';
    svg+='<circle cx="'+(b.x+2)+'" cy="'+(b.y+3)+'" r="'+b.r+'" fill="rgba(0,0,0,0.05)"/>';
    svg+='<circle cx="'+b.x+'" cy="'+b.y+'" r="'+b.r+'" fill="url(#'+gid+')" stroke="'+cd[b.key]+'" stroke-width="1.5"/>';
    var fs=Math.max(9,b.r*0.22);
    svg+='<text x="'+b.x+'" y="'+(b.y-b.r*0.12)+'" text-anchor="middle" fill="#fff" font-size="'+(fs+2)+'" font-weight="700">'+b.label+'</text>';
    svg+='<text x="'+b.x+'" y="'+(b.y+b.r*0.2)+'" text-anchor="middle" fill="rgba(255,255,255,0.9)" font-size="'+(fs-2)+'" font-weight="600">&yen;'+b.val+'</text>';
    svg+='<text x="'+b.x+'" y="'+(b.y+b.r*0.42)+'" text-anchor="middle" fill="rgba(255,255,255,0.8)" font-size="'+Math.max(8,fs-4)+'">'+b.pct+'%</text>';
  });
  svg+='</svg>';c.innerHTML=svg;
}

function drawRouteCards(cid,rs){
  var c=document.getElementById(cid);
  function avgT(rs){if(!rs.length)return 0;return Math.round(rs.reduce(function(s,r){return s+keys.reduce(function(a,k){return a+r[k]},0)},0)/rs.length)}
  var h='';
  h+='<div class="route-cards">';
  rs.forEach(function(r){var t=keys.reduce(function(s,k){return s+r[k]},0);var sh=r.label.split(' ').slice(1).join(' ');h+='<div class="route-item"><div class="rl">'+sh+'</div><div class="rv">&yen;'+t+'</div><div class="rs">头'+Math.round(r.A/t*100)+'% 尾'+Math.round(r.E/t*100)+'%</div></div>'});
  h+='<div class="route-item" style="background:#f0f2f5;border:2px solid #d1d5db"><div class="rl">均值</div><div class="rv" style="font-size:17px">&yen;'+avgT(rs)+'</div><div class="rs">'+rs.length+'条</div></div></div>';
  c.innerHTML=h;
}
'''

    for model in ['G系列', 'M系列', 'N系列']:
        for dest in ['德国', '美国']:
            key = f"{model[0].lower()}_{'de' if dest == '德国' else 'us'}"
            _, _, routes_js, _ = series_data[key]
            html += f"var {key}Data={{name:'{model} — {dest}',routes:[\n    {routes_js}\n]}};\n"

    for model in ['G系列', 'M系列', 'N系列']:
        for dest in ['德国', '美国']:
            key = f"{model[0].lower()}_{'de' if dest == '德国' else 'us'}"
            html += f"drawCloud('{key}cloud',{key}Data.routes);\ndrawRouteCards('{key}-routes',{key}Data.routes);\n"

    html += '</script>\n</body>\n</html>'
    return html

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    print('Building combined panorama...')
    result = build()
    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        f.write(result)
    print(f'  -> {OUT_FILE} ({len(result):,} chars)')
    print('Done.')
