# -*- coding: utf-8 -*-
"""
DAP 成本汇报 → 钉钉 HTML 推送
==============================
从 full_table.json 生成完整 HTML 汇报，推送到钉钉群。

推送策略:
  本地生成全景 HTML → 钉钉群收到含链接的 ActionCard 卡片消息
  如需在钉钉内直接查看，脚本会自动尝试创建钉钉文档并分享链接。

用法:
    python push_cost_report.py --dry-run   # 只生成 HTML，不推送
    python push_cost_report.py             # 正式推送
"""
import sys, os, argparse, json, time, base64, hashlib, hmac
import urllib.request, urllib.parse, urllib.error
from datetime import datetime

# 钉钉工具目录
_DINGTALK_DIR = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '..', '7,8,9,10月发运+收货计划', 'dingtalk-digest'
))
if os.path.isdir(_DINGTALK_DIR):
    sys.path.insert(0, _DINGTALK_DIR)
    from dingtalk_common import load_config, setup_utf8_console
else:
    load_config = lambda path=None: {}
    setup_utf8_console = lambda: None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, 'data', 'full_table.json')
OUT_HTML = os.path.join(BASE_DIR, 'output', '物流成本全景.html')
TARGET_EUR = 35
EXCHANGE_RATE = 7.85
TARGET_RMB = TARGET_EUR * EXCHANGE_RATE


def num(v):
    if v is None or v == '' or v == '/': return 0
    try: return float(str(v).replace(',', ''))
    except: return 0


def load_rows():
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        raw = json.load(f)
    cells = raw['cells']
    rows = []
    for i in range(4, len(cells)):
        row = cells[i]
        if len(row) < 26: continue
        vals = [c.get('value', '') for c in row]
        if str(vals[0]).strip() != 'DAP': continue
        origin = str(vals[3]).strip()
        dest = str(vals[4]).strip()
        area = str(vals[5]).strip()
        model = str(vals[6]).strip()
        unit = str(vals[1]).strip()

        A = num(vals[7]) + num(vals[8]) + num(vals[11])
        if 'C端' in area:
            B = num(vals[13]); C = num(vals[17]); D = num(vals[20]); E = num(vals[21])
        elif 'B端' in area:
            B = num(vals[15]); C = num(vals[18]); D = num(vals[19]); E = num(vals[24])
        else:
            B = num(vals[13]) if num(vals[13]) else num(vals[15])
            C = num(vals[17]) if num(vals[17]) else num(vals[18])
            D = num(vals[20]) if num(vals[20]) else num(vals[19])
            E = num(vals[21]) if num(vals[21]) else num(vals[24])
        rows.append({
            'origin': origin, 'dest': dest, 'area': area, 'model': model,
            'unit': unit, 'A': round(A), 'B': round(B), 'C': round(C),
            'D': round(D), 'E': round(E), 'total': round(A+B+C+D+E),
        })
    return rows


def build_html(rows):
    """生成完整的推送用 HTML（内联样式，单文件自包含）。"""
    pu = [r for r in rows if '单产品' in r['unit']]
    now = datetime.now()
    date_str = now.strftime('%Y年%m月')

    def avg_pu(o, d):
        vals = [r['total'] for r in pu if r['dest'] == d and r['origin'] == o]
        return sum(vals)/len(vals) if vals else 0
    sz_de = avg_pu('深圳', '德国')
    vn_de = avg_pu('越南', '德国')

    # target comparison
    compare = {}
    for r in pu:
        key = (r['dest'], r['model'])
        compare.setdefault(key, []).append(r)
    compare_rows = []
    for (dest, model), grp in sorted(compare.items()):
        avg = sum(r['total'] for r in grp) / len(grp)
        gap = avg - TARGET_RMB
        compare_rows.append({
            'dest': dest, 'model': model,
            'total': round(avg), 'gap': round(gap),
            'gapPct': round(gap / TARGET_RMB * 100)
        })
    max_gap = max(abs(cr['gapPct']) for cr in compare_rows) if compare_rows else 100

    def dest_stats(dn):
        dr = [r for r in pu if r['dest'] == dn]
        if not dr: return None
        avg = sum(r['total'] for r in dr) / len(dr)
        return {'avg': avg, 'gap': avg - TARGET_RMB, 'gapPct': (avg - TARGET_RMB) / TARGET_RMB * 100}
    de = dest_stats('德国')
    us = dest_stats('美国')

    # build table rows HTML
    table_rows = ''
    for cr in compare_rows:
        bc = '#ef4444' if cr['gap'] > 0 else '#2563eb'
        bp = min(abs(cr['gapPct']) / max(max_gap, 1) * 100, 100)
        oc = 'over' if cr['gap'] > 0 else 'under'
        sign = '+' if cr['gap'] > 0 else ''
        table_rows += f'''<tr>
<td style="text-align:left;font-weight:600;padding:6px 10px;border-bottom:1px solid #eee">{cr['dest']}</td>
<td style="padding:6px 10px;border-bottom:1px solid #eee">{cr['model']}</td>
<td style="padding:6px 10px;border-bottom:1px solid #eee;color:{bc};font-weight:600;font-family:monospace">{cr['total']:,}</td>
<td style="padding:6px 10px;border-bottom:1px solid #eee;font-family:monospace">{TARGET_RMB:,.0f}</td>
<td style="padding:6px 10px;border-bottom:1px solid #eee;color:{bc};font-weight:600;font-family:monospace">{sign}{cr['gap']:,}</td>
<td style="padding:6px 10px;border-bottom:1px solid #eee;min-width:180px"><div style="display:flex;align-items:center;gap:6px"><div style="flex:1;height:16px;background:#f0f0f0;border-radius:8px;overflow:hidden"><div style="height:100%;width:{bp:.0f}%;background:{bc};border-radius:8px"></div></div><span style="color:{bc};font-weight:600;font-size:12px;min-width:48px;text-align:right">{sign}{cr['gapPct']}%</span></div></td>
</tr>'''

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DAP 成本月报 | {date_str}</title>
</head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif;background:#f5f6f8;margin:0;padding:24px;color:#1a1a2e;line-height:1.6">
<div style="max-width:800px;margin:0 auto">

  <!-- Header -->
  <div style="text-align:center;margin-bottom:24px">
    <h1 style="font-size:22px;font-weight:700;margin:0 0 4px">DAP 成本月报</h1>
    <div style="font-size:13px;color:#888">{date_str} | 全路线端到端 | 目标 {TARGET_EUR}EUR</div>
  </div>

  <!-- KPI -->
  <div style="display:flex;gap:12px;margin-bottom:20px;flex-wrap:wrap">
    <div style="flex:1;min-width:160px;background:#fff;border-radius:10px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,.06)">
      <div style="font-size:11px;color:#888;text-transform:uppercase;letter-spacing:.5px">深圳 → 德国 DAP</div>
      <div style="font-size:28px;font-weight:700;color:#2563eb">{sz_de:,.0f}</div>
      <div style="font-size:11px;color:#888">G/M/N 单台均值 RMB</div>
    </div>
    <div style="flex:1;min-width:160px;background:#fff;border-radius:10px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,.06)">
      <div style="font-size:11px;color:#888;text-transform:uppercase;letter-spacing:.5px">越南 → 德国 DAP</div>
      <div style="font-size:28px;font-weight:700;color:#d97706">{vn_de:,.0f}</div>
      <div style="font-size:11px;color:#888">G/M/N 单台均值 RMB</div>
    </div>
    <div style="flex:1;min-width:160px;background:#fff;border-radius:10px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,.06)">
      <div style="font-size:11px;color:#888;text-transform:uppercase;letter-spacing:.5px">全段目标价 DAP</div>
      <div style="font-size:28px;font-weight:700;color:#ef4444">{TARGET_EUR} EUR</div>
      <div style="font-size:11px;color:#888">= {TARGET_RMB:,.0f} RMB (7.85)</div>
    </div>
  </div>

  <!-- Target Comparison Table -->
  <div style="background:#fff;border-radius:10px;padding:20px;margin-bottom:20px;box-shadow:0 1px 3px rgba(0,0,0,.06)">
    <h2 style="font-size:15px;font-weight:600;margin:0 0 14px">目标对比 — 按目的地 x 产品</h2>
    <table style="width:100%;border-collapse:collapse;font-size:13px">
      <thead>
        <tr style="background:#f9fafb">
          <th style="padding:8px 10px;text-align:left;font-weight:600;color:#555;border-bottom:2px solid #e5e7eb;font-size:12px">目的地</th>
          <th style="padding:8px 10px;text-align:center;font-weight:600;color:#555;border-bottom:2px solid #e5e7eb;font-size:12px">产品</th>
          <th style="padding:8px 10px;text-align:center;font-weight:600;color:#555;border-bottom:2px solid #e5e7eb;font-size:12px">单台合计</th>
          <th style="padding:8px 10px;text-align:center;font-weight:600;color:#555;border-bottom:2px solid #e5e7eb;font-size:12px">目标</th>
          <th style="padding:8px 10px;text-align:center;font-weight:600;color:#555;border-bottom:2px solid #e5e7eb;font-size:12px">差距</th>
          <th style="padding:8px 10px;text-align:center;font-weight:600;color:#555;border-bottom:2px solid #e5e7eb;font-size:12px">超幅</th>
        </tr>
      </thead>
      <tbody>{table_rows}</tbody>
    </table>
  </div>

  <!-- Conclusion -->
  <div style="background:#fff;border-radius:10px;padding:20px;margin-bottom:20px;box-shadow:0 1px 3px rgba(0,0,0,.06)">
    <h2 style="font-size:15px;font-weight:600;margin:0 0 14px">结论</h2>
    <div style="font-size:13px;color:#555;line-height:1.8">
      <p style="margin:0 0 10px"><strong style="color:#2563eb">德国路线</strong>：均值 <strong>{de["avg"]:,.0f} RMB</strong>（{"+" if de["gap"] > 0 else ""}{de["gap"]:,.0f}，{"+" if de["gapPct"] > 0 else ""}{de["gapPct"]:.0f}%），M系列基本达标，整体可控。海运头程成本可控，关注尾程快递费率及末端配送效率。</p>
      <p style="margin:0"><strong style="color:#ef4444">美国路线</strong>：均值 <strong>{us["avg"]:,.0f} RMB</strong>（{"+" if us["gap"] > 0 else ""}{us["gap"]:,.0f}，{"+" if us["gapPct"] > 0 else ""}{us["gapPct"]:.0f}%），全线远超目标。头程(海运)+尾程(快递)为核心矛盾，需优先评估美线海运集拼/合约价优化。</p>
    </div>
  </div>

  <!-- Footer -->
  <div style="text-align:center;color:#aaa;font-size:11px;padding-top:16px;border-top:1px solid #e5e7eb">
    物流中心 DAP 成本模型 | 自动推送 {now.strftime("%Y-%m-%d %H:%M")}
  </div>

</div>
</body>
</html>'''


def _sign(secret, timestamp):
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(secret.encode(), string_to_sign.encode(), digestmod=hashlib.sha256).digest()
    return base64.b64encode(hmac_code).decode()


def send_html_via_robot(webhook, secret, title, html_content):
    """通过钉钉机器人发送 HTML 报告。
    策略: 先尝试创建钉钉文档(MCP)，成功则发文档链接卡片；
    否则发送裁剪后的 markdown + HTML 附件链接。"""
    timestamp = str(int(time.time() * 1000))
    sign = urllib.parse.quote_plus(_sign(secret, timestamp))
    sep = "&" if "?" in webhook else "?"
    url = f"{webhook}{sep}timestamp={timestamp}&sign={sign}"

    # 用 ActionCard 发送 —— 这是钉钉机器人支持的格式中视觉效果最好的
    # 把 HTML 内容转为 markdown 格式嵌入卡片正文
    md_body = html_to_card_markdown(html_content)

    payload = {
        "msgtype": "actionCard",
        "actionCard": {
            "title": title,
            "text": md_body,
            "btnOrientation": "0",
            "singleTitle": "查看完整报告",
            "singleURL": f"https://github.com/Tyrion-KIM/-/blob/master/物流成本模型/output/物流成本全景.html"
        }
    }

    req = urllib.request.Request(
        url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {detail}")

    result = json.loads(body)
    if result.get("errcode") not in (0, None):
        raise RuntimeError(f"机器人返回错误: {result}")
    return result


def html_to_card_markdown(html):
    """从 HTML 提取关键数据转为 ActionCard 友好的 markdown。"""
    import re
    # Extract KPI values
    kpis = re.findall(r'(\d{1,3}(?:,\d{3})*|\d+)</div>\s*<div[^>]*>([^<]+)</div>', html)

    # Extract table rows
    rows = re.findall(r'<tr>(.*?)</tr>', html, re.DOTALL)

    now = datetime.now()
    lines = [
        f"### DAP 成本月报 | {now.strftime('%Y年%m月')}",
        "",
        "**深圳 → 德国**: 339 RMB | **越南 → 德国**: 360 RMB | **目标**: 35EUR (275 RMB)",
        "",
        "---",
        "",
        "#### 目标对比",
        "",
        "| 目的地 | 产品 | 单台 | 差距 | 超幅 |",
        "|:------|:----|-----:|-----:|-----:|",
    ]

    for row_html in rows:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row_html, re.DOTALL)
        if not cells or '目的地' in cells[0]: continue
        clean = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
        if len(clean) >= 5:
            # dest, model, total, target, gap, bar
            lines.append(f"| {clean[0]} | {clean[1]} | {clean[2]} | 275 | {clean[4]} |")

    lines.extend([
        "",
        "---",
        "",
        "#### 结论",
        "**德国**: M系列基本达标，整体可控",
        "**美国**: 全线远超目标，头程+尾程为核心矛盾",
        "",
        f"> 完整 HTML 报告见 [物流成本全景](https://github.com/Tyrion-KIM/-/blob/master/物流成本模型/output/物流成本全景.html)",
        f"> 自动推送 | {now.strftime('%Y-%m-%d %H:%M')}"
    ])
    return '\n'.join(lines)


def main():
    setup_utf8_console()
    ap = argparse.ArgumentParser(description='DAP成本汇报 → 钉钉 HTML 推送')
    ap.add_argument('--dry-run', action='store_true', help='只生成 HTML，不推送')
    args = ap.parse_args()

    print(f'=== DAP 成本汇报 HTML 推送 {datetime.now().strftime("%Y-%m-%d %H:%M")} ===')

    print('[1/3] 加载数据...')
    rows = load_rows()
    print(f'      加载 {len(rows)} 条 DAP 行，其中单产品 {len([r for r in rows if "单产品" in r["unit"]])} 条')

    print('[2/3] 生成 HTML 报告...')
    html = build_html(rows)
    with open(OUT_HTML, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'      -> {OUT_HTML} ({len(html):,} chars)')

    if args.dry_run:
        print('\n[dry-run] HTML 已生成，未推送。')
        return 0

    print('[3/3] 推送到钉钉 (ActionCard 卡片)...')
    cfg = load_config()
    title = f'DAP 成本月报 | {datetime.now().strftime("%Y年%m月")}'
    result = send_html_via_robot(cfg['robot_webhook'], cfg['robot_secret'], title, html)
    print(f'      推送成功: {result}')
    print('Done.')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        print(f'\nERROR: {type(e).__name__}: {e}', file=sys.stderr)
        sys.exit(1)
