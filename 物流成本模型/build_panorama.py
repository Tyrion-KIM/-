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

    # -- horizontal comparison data (B/C/D split individually) --
    compare_biz = []
    for model in ['G系列', 'M系列', 'N系列']:
        for dest, biz_types in [('德国', ['C端谷仓', 'B端中转']), ('美国', ['美东', '美西'])]:
            for biz in biz_types:
                mr = [r for r in pu if r['model'] == model and r['dest'] == dest and r['area'] == biz]
                if not mr: continue
                n = len(mr)
                avgA = sum(r['A'] for r in mr) / n
                avgB = sum(r['B'] for r in mr) / n
                avgC = sum(r['C'] for r in mr) / n
                avgD = sum(r['D'] for r in mr) / n
                avgE = sum(r['E'] for r in mr) / n
                avgTotal = avgA + avgB + avgC + avgD + avgE
                compare_biz.append({
                    'model': model, 'dest': dest, 'biz': biz,
                    'A': round(avgA), 'B': round(avgB), 'C': round(avgC),
                    'D': round(avgD), 'E': round(avgE),
                    'total': round(avgTotal),
                    'aPct': round(avgA / avgTotal * 100) if avgTotal else 0,
                    'bPct': round(avgB / avgTotal * 100) if avgTotal else 0,
                    'cPct': round(avgC / avgTotal * 100) if avgTotal else 0,
                    'dPct': round(avgD / avgTotal * 100) if avgTotal else 0,
                    'ePct': round(avgE / avgTotal * 100) if avgTotal else 0,
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

    # -- Cost breakdown reference --
    html += '''
<div class="card" style="padding:16px 20px">
  <div class="card-header"><div class="card-title">费用构成说明</div><span class="tag tag-blue">A/B/C/D/E 五段明细</span></div>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:10px;font-size:12px;line-height:1.8">
    <div><strong style="color:#2563eb">A 头程运费</strong><br><span style="color:#6b7280">内陆运费 + 报关费 + 港杂费 + 海运费 + 目的港港杂费 + 目的港拖车费</span></div>
    <div><strong style="color:#0d9488">B 海外仓上架费</strong><br><span style="color:#6b7280">海外仓卸柜费 + 入库清点费 + 海外仓上架费</span></div>
    <div><strong style="color:#d97706">C 仓储费</strong><br><span style="color:#6b7280">按货物存放<strong>90天</strong>计算得出</span></div>
    <div><strong style="color:#e11d48">D 出库操作费</strong><br><span style="color:#6b7280">C端仓库：下架 + 贴面单 + 收集SN<br>B端仓库：下架 + 收集SN + 打托 + 装柜</span></div>
    <div><strong style="color:#7c3aed">E 尾程运费</strong><br><span style="color:#6b7280">C端：本地快递费用 / B端：尾程卡车费用</span></div>
  </div>
</div>
'''

    # -- Horizontal comparison --
    de_rows = sorted([r for r in compare_biz if r['dest'] == '德国'], key=lambda x: x['total'], reverse=True)
    us_rows = sorted([r for r in compare_biz if r['dest'] == '美国'], key=lambda x: x['total'], reverse=True)
    TGT_HEAD = round(TARGET_BREAKDOWN['head'] * EXCHANGE_RATE)
    TGT_TAIL = round(TARGET_BREAKDOWN['tail'] * EXCHANGE_RATE)
    TGT_OTHER = round(TARGET_BREAKDOWN['other'] * EXCHANGE_RATE)
    all_rows = de_rows + us_rows
    maxA = max(r['A'] for r in all_rows) if all_rows else 1
    maxB = max(r['B'] for r in all_rows) if all_rows else 1
    maxC = max(r['C'] for r in all_rows) if all_rows else 1
    maxD = max(r['D'] for r in all_rows) if all_rows else 1
    maxE = max(r['E'] for r in all_rows) if all_rows else 1
    tgt_head_pct = round(TGT_HEAD / TARGET_RMB * 100)
    tgt_tail_pct = round(TGT_TAIL / TARGET_RMB * 100)

    cols = [
        ('A 头程运费', '头', maxA, TGT_HEAD, tgt_head_pct, '#2563eb', '#dbeafe'),
        ('B 上架费', 'B上架', maxB, 0, 0, '#0d9488', '#ccfbf1'),
        ('C 仓储费', 'C仓储', maxC, 0, 0, '#d97706', '#fef3c7'),
        ('D 出库操作', 'D出库', maxD, 0, 0, '#e11d48', '#ffe4e6'),
        ('E 尾程运费', '尾', maxE, TGT_TAIL, tgt_tail_pct, '#7c3aed', '#ede9fe'),
    ]

    html += '''
<div class="card">
  <div class="card-header"><div class="card-title">横向对比 — 五段成本分列对齐</div><span class="tag tag-blue">产品 × 目的地 × 业务类型</span></div>
'''
    for label, rows in [('德国', de_rows), ('美国', us_rows)]:
        html += f'''
  <div style="margin-bottom:16px">
    <h4 style="font-size:14px;margin-bottom:8px;color:#1e40af">{label}</h4>
    <!-- column header -->
    <div style="display:flex;align-items:center;gap:0;margin-bottom:4px;font-size:10px;color:#9ca3af;padding:0 84px 0 84px">
      <div style="flex:1;text-align:center">A 头程</div>
      <div style="width:6px;flex-shrink:0"></div>
      <div style="flex:1;text-align:center">B 上架</div>
      <div style="width:6px;flex-shrink:0"></div>
      <div style="flex:1;text-align:center">C 仓储</div>
      <div style="width:6px;flex-shrink:0"></div>
      <div style="flex:1;text-align:center">D 出库</div>
      <div style="width:6px;flex-shrink:0"></div>
      <div style="flex:1;text-align:center">E 尾程</div>
      <div style="width:60px;flex-shrink:0"></div>
    </div>
    <!-- target line -->
    <div style="display:flex;align-items:center;gap:0;margin-bottom:10px;height:22px;padding:0 84px 0 84px">'''
        for _, _, col_max, tgt_val, tgt_p, _, bg in cols:
            tgt_w = (tgt_val / col_max * 100) if col_max and tgt_val else 0
            html += f'''
      <div style="flex:1;height:22px;background:{bg};border-radius:6px;border:2px dashed #fca5a5;display:flex;align-items:center;justify-content:flex-end;position:relative;overflow:visible">
        <div style="position:absolute;right:calc(100% - {tgt_w:.1f}%);top:0;bottom:0;width:{tgt_w:.1f}%;background:rgba(239,68,68,0.15);border-radius:4px;display:flex;align-items:center;justify-content:center;min-width:{ '28px' if tgt_w > 5 else '0' }">
          <span style="color:#dc2626;font-size:10px;font-weight:700;white-space:nowrap">{"&yen;" + str(tgt_val) if tgt_val else ""}</span>
        </div>
      </div>
      <div style="width:6px;flex-shrink:0"></div>'''
        html += f'''
      <div style="width:60px;flex-shrink:0;text-align:center;font-size:11px;color:#dc2626;font-weight:700">&yen;{TARGET_RMB}</div>
    </div>'''
        # data rows
        for r in rows:
            short = f"{r['model'][0]} {r['biz'].replace('谷仓','').replace('中转','')}"
            vals = [r['A'], r['B'], r['C'], r['D'], r['E']]
            pcts = [r['aPct'], r['bPct'], r['cPct'], r['dPct'], r['ePct']]
            html += f'''
    <div style="display:flex;align-items:center;gap:0;margin-bottom:6px;height:28px;padding:0 0 0 84px">
      <div style="width:76px;text-align:right;font-weight:600;flex-shrink:0;font-size:11px;margin-left:-84px;margin-right:8px">{short}</div>'''
            for i, (col_name, col_label, col_max, _, _, col_color, _) in enumerate(cols):
                val = vals[i]
                pct = pcts[i]
                bar_w = (val / col_max * 100) if col_max else 0
                txt = f'&yen;{val}' if pct >= 3 else (f'&yen;{val}' if pct >= 1 else '')
                html += f'''
      <div style="flex:1;height:28px;background:#f3f4f6;border-radius:6px;display:flex;align-items:center;overflow:visible;position:relative">
        <div style="width:{bar_w:.1f}%;height:100%;background:{col_color};border-radius:6px;display:flex;align-items:center;justify-content:flex-end;min-width:{ '36px' if pct >= 3 and bar_w > 10 else '0' }">
          <span style="color:#fff;font-size:10px;font-weight:600;white-space:nowrap;padding:0 6px">{txt}</span>
        </div>
      </div>
      <div style="width:6px;flex-shrink:0"></div>'''
            html += f'''
      <div style="width:60px;flex-shrink:0;font-weight:700;font-size:13px;text-align:center">&yen;{r['total']}</div>
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

    # -- JS (none needed — all charts are pure HTML/CSS) --
    html += '''
<footer>物流中心 | DAP成本全景 | 2026-08-04</footer>
</div>
</body>
</html>'''
    return html

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    print('Building combined panorama...')
    result = build()
    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        f.write(result)
    print(f'  -> {OUT_FILE} ({len(result):,} chars)')
    print('Done.')
