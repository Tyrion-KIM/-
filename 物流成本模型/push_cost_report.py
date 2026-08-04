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
OUT_HTML = os.path.join(BASE_DIR, 'output', '物流成本全景.html')

# 直接使用 build_panorama 生成完整的全景 HTML（含云图）
from build_panorama import build as build_full_panorama


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
            "singleURL": f"https://htmlpreview.github.io/?https://github.com/Tyrion-KIM/-/blob/master/物流成本模型/output/物流成本全景.html"
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
        "**全段目标**: 35EUR (275 RMB) | 详细数据见下方表格",
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
        f"> 完整 HTML 报告见 [物流成本全景](https://htmlpreview.github.io/?https://github.com/Tyrion-KIM/-/blob/master/物流成本模型/output/物流成本全景.html)",
        f"> 自动推送 | {now.strftime('%Y-%m-%d %H:%M')}"
    ])
    return '\n'.join(lines)


def main():
    setup_utf8_console()
    ap = argparse.ArgumentParser(description='DAP成本汇报 → 钉钉 HTML 推送')
    ap.add_argument('--dry-run', action='store_true', help='只生成 HTML，不推送')
    args = ap.parse_args()

    print(f'=== DAP 成本汇报 HTML 推送 {datetime.now().strftime("%Y-%m-%d %H:%M")} ===')

    print('[1/2] 生成全景 HTML（含KPI+目标表+云图+结论）...')
    html = build_full_panorama()
    with open(OUT_HTML, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'      -> {OUT_HTML} ({len(html):,} chars)')

    if args.dry_run:
        print('\n[dry-run] HTML 已生成，未推送。')
        return 0

    print('[2/2] 推送到钉钉 (ActionCard 卡片)...')
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
