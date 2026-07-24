#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
钉钉明日行程简报（下班前推送）

拉取钉钉日历里明天的行程，整理成简报，通过钉钉自定义机器人 Webhook 发送。

用法：
    python dingtalk_calendar_briefing.py --dry-run   # 只预览，不发消息
    python dingtalk_calendar_briefing.py             # 正式发送
"""

import argparse
from datetime import datetime, time as dtime, timedelta

from dingtalk_common import McpClient, send_via_robot, load_config, setup_utf8_console

WEEKDAYS = "一二三四五六日"


def weekday_cn(d):
    return f"周{WEEKDAYS[d.weekday()]}"


def parse_dt(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def fmt_range(ev):
    """格式化行程时间。"""
    if ev.get("isAllDay"):
        return "全天"
    start = parse_dt((ev.get("start") or {}).get("dateTime"))
    end = parse_dt((ev.get("end") or {}).get("dateTime"))
    if not start:
        return "全天"
    if end and end.date() != start.date():
        return f"{start.strftime('%m-%d %H:%M')}-{end.strftime('%m-%d %H:%M')}"
    end_str = end.strftime("%H:%M") if end else ""
    return f"{start.strftime('%H:%M')}-{end_str}" if end_str else start.strftime("%H:%M")


def event_location(ev):
    loc = ev.get("location") or ""
    rooms = ev.get("meetingRooms") or []
    if not loc and rooms:
        loc = "、".join(r.get("roomName", "") for r in rooms if r.get("roomName"))
    return loc.strip()


def fetch_tomorrow_events(client):
    """拉取明天的日历行程（primary 日历）。"""
    now = datetime.now()
    tomorrow = now.date() + timedelta(days=1)
    start = datetime.combine(tomorrow, dtime(0, 0, 0))
    end = datetime.combine(tomorrow, dtime(23, 59, 59))
    start_ms, end_ms = int(start.timestamp() * 1000), int(end.timestamp() * 1000)

    events = []
    cursor = None
    while True:
        args = {"startTime": start_ms, "endTime": end_ms, "limit": 100}
        if cursor:
            args["cursor"] = cursor
        data = client.call_tool("list_calendar_events", args)
        result = data.get("result", data) if isinstance(data, dict) else {}
        batch = result.get("events", []) or []
        events.extend(batch)
        cursor = result.get("nextCursor") or result.get("cursor")
        if not cursor or len(events) >= 500:
            break

    # 剔除已取消；按开始时间排序
    def start_key(ev):
        dt = parse_dt((ev.get("start") or {}).get("dateTime"))
        return dt.timestamp() if dt else 0

    cleaned = [e for e in events if (e.get("status") or "").lower() != "cancelled"]
    cleaned.sort(key=start_key)
    return cleaned, tomorrow


def build_title(events, tomorrow):
    if not events:
        return f"📅 明日行程 · {tomorrow.strftime('%m-%d')} {weekday_cn(tomorrow)}（无行程 🎉）"
    return f"📅 明日行程 · {tomorrow.strftime('%m-%d')} {weekday_cn(tomorrow)}（共 {len(events)} 个）"


def _event_line(ev, markdown):
    rng = fmt_range(ev)
    summary = ev.get("summary", "") or "（无标题）"
    loc = event_location(ev)
    organizer = (ev.get("organizer") or {}).get("displayName", "")
    attendees = ev.get("attendees") or []
    n_people = len([a for a in attendees])  # 含自己
    parts = []
    head = f"**{rng}**｜**{summary}**" if markdown else f"{rng}｜{summary}"
    parts.append(head)
    meta = []
    if loc:
        meta.append(f"📍{loc}")
    if organizer:
        meta.append(f"👤{organizer}")
    if n_people:
        meta.append(f"👥{n_people}人")
    tail = " ".join(meta)
    return f"{head}  {tail}" if tail else head


def build_plain_body(events, tomorrow):
    lines = [f"📌 明日行程 · {tomorrow.strftime('%Y-%m-%d')} {weekday_cn(tomorrow)}"]
    if not events:
        lines += ["明天日历里没有行程，可以安心下班 🎉"]
        return "\n".join(lines)
    lines.append(f"明天共 {len(events)} 个行程：")
    lines.append("")
    for i, ev in enumerate(events, 1):
        lines.append(f"{i}. {_event_line(ev, markdown=False)}")
    return "\n".join(lines)


def build_markdown(events, tomorrow):
    lines = [f"### 📅 明日行程 · {tomorrow.strftime('%m-%d')} {weekday_cn(tomorrow)}", ""]
    if not events:
        lines += ["明天日历里没有行程，可以安心下班 🎉"]
        return "\n".join(lines)
    lines.append(f"明天共 **{len(events)}** 个行程：")
    lines.append("")
    for i, ev in enumerate(events, 1):
        lines.append(f"{i}. {_event_line(ev, markdown=True)}")
    lines.append("")
    lines.append("> 由钉钉日历自动整理")
    return "\n".join(lines)


def main():
    setup_utf8_console()
    ap = argparse.ArgumentParser(description="钉钉明日行程简报")
    ap.add_argument("--dry-run", action="store_true", help="只预览，不发消息")
    ap.add_argument("--config", default=None, help="配置文件路径")
    args = ap.parse_args()

    cfg = load_config(args.config) if args.config else load_config()
    now = datetime.now()
    print(f"=== 钉钉明日行程简报 {now.strftime('%Y-%m-%d %H:%M')} ===")
    if args.dry_run:
        print("[模式] dry-run（仅预览，不发消息）")

    print("[1/2] 拉取明天的日历行程 ...")
    client = McpClient(cfg["calendar_mcp_url"])
    events, tomorrow = fetch_tomorrow_events(client)
    print(f"      命中 {len(events)} 个（{tomorrow.strftime('%m-%d')} {weekday_cn(tomorrow)}）")

    title = build_title(events, tomorrow)
    body = build_plain_body(events, tomorrow)
    print("\n----- 简报预览 -----")
    print(f"{title}\n")
    print(body)
    print("--------------------\n")

    if args.dry_run:
        print("[dry-run] 未发送。")
        return 0

    print("[2/2] 发送到钉钉机器人 ...")
    md = build_markdown(events, tomorrow)
    result = send_via_robot(cfg["robot_webhook"], cfg["robot_secret"], title, md)
    print(f"      发送成功: {result}")
    print(f"\nSUMMARY: 明天 {len(events)} 个行程，简报已发送到钉钉机器人。")
    return 0


if __name__ == "__main__":
    import sys
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
