#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
钉钉每日待办日报

每天拉取钉钉里「今天到期 + 近 7 天逾期」的未完成待办，生成日报，
并通过钉钉自定义机器人 Webhook 发送到指定群（发给本人）。

用法：
    python dingtalk_daily_digest.py --dry-run   # 只拉取并预览，不发消息
    python dingtalk_daily_digest.py             # 正式生成并发送到钉钉机器人
"""

import argparse
import re
from datetime import datetime, time as dtime, timedelta

from dingtalk_common import McpClient, send_via_robot, load_config, setup_utf8_console

# 已逾期部分只看最近 N 天（更早的逾期不列入日报，避免历史堆积淹没重点）
OVERDUE_WINDOW_DAYS = 7

NAME_RE = re.compile(r"[一-龥·・]{2,5}")


def parse_submitter(subject):
    """从待办标题解析提交人姓名。"""
    if not subject:
        return "—"
    s = re.sub(r"^[【［][^】］]*[】］]", "", subject).strip()
    for sep in ["提交的", "提交", "-", "—", "－", "：", " ", "·"]:
        if sep in s:
            head = s.split(sep, 1)[0].strip()
            if NAME_RE.fullmatch(head):
                return head
    return "—"


def strip_submitter(subject, submitter):
    """从展示标题中去掉开头的提交人前缀，避免重复。"""
    if submitter == "—":
        return subject
    for sep in ["提交的", "提交", "-", "—", "－"]:
        prefix = submitter + sep
        if subject.startswith(prefix):
            return subject[len(prefix):].strip()
    if subject.startswith(submitter):
        rest = subject[len(submitter):]
        return rest.lstrip(" -—－·：").strip()
    return subject


def end_of_today_ms():
    now = datetime.now()
    eod = datetime.combine(now.date(), dtime(23, 59, 59, 999000))
    return int(eod.timestamp() * 1000)


def start_of_today_ms():
    now = datetime.now()
    sod = datetime.combine(now.date(), dtime(0, 0, 0))
    return int(sod.timestamp() * 1000)


def fetch_due_today_and_overdue(client):
    """拉取「今天到期 + 近 OVERDUE_WINDOW_DAYS 天逾期」的未完成待办。

    钉钉 MCP 的坑：pageSize>20 返回空；todoStatus 与 planFinishDate* 不能并用。
    故用 planFinishDateStart/End 圈定窗口，再客户端按 finalStatusStage 剔除已完成。
    """
    eod = end_of_today_ms()
    now = datetime.now()
    window_start = datetime.combine(
        now.date() - timedelta(days=OVERDUE_WINDOW_DAYS), dtime(0, 0, 0)
    )
    start_ms = int(window_start.timestamp() * 1000)

    cards = []
    page = 1
    while True:
        data = client.call_tool("get_user_todos_in_current_org", {
            "pageNum": str(page),
            "pageSize": "20",
            "roleTypes": ["executor"],
            "planFinishDateStart": start_ms,
            "planFinishDateEnd": eod,
        })
        result = data.get("result", data) if isinstance(data, dict) else {}
        batch = result.get("todoCards", []) or []
        cards.extend(batch)
        if not result.get("hasMore", False):
            break
        page += 1
        if page > 50:
            break

    filtered = [
        c for c in cards
        if c.get("dueTime") and start_ms <= c["dueTime"] <= eod
        and c.get("finalStatusStage", 0) != 2
    ]
    filtered.sort(key=lambda c: c["dueTime"])
    return filtered


def build_title(todos, date_str):
    if not todos:
        return f"📋 每日待办日报 {date_str}（共 0 条 🎉）"
    return f"📋 每日待办日报 {date_str}（共 {len(todos)} 条）"


def build_plain_body(todos, now):
    """控制台预览用的纯文本。"""
    time_str = now.strftime("%H:%M")
    sod = start_of_today_ms()
    overdue = [t for t in todos if t["dueTime"] < sod]
    lines = [f"📌 今日待办日报 · {now.strftime('%Y-%m-%d')} {time_str}"]
    if not todos:
        lines += ["今天到期 / 近 7 天逾期的未完成待办：0 条 🎉",
                  "今天没有到期或逾期的待办，可以安心处理其他事。"]
        return "\n".join(lines)
    lines.append(f"今天到期 / 近 {OVERDUE_WINDOW_DAYS} 天逾期的未完成待办，共 {len(todos)} 条"
                 f"（其中已逾期 {len(overdue)} 条）：")
    lines.append("")
    for i, t in enumerate(todos, 1):
        subject = t.get("subject", "")
        submitter = parse_submitter(subject)
        title_clean = strip_submitter(subject, submitter)
        marker = "⚠️ " if t["dueTime"] < sod else ""
        lines.append(f"{i}. {marker}{submitter}｜{title_clean}")
    lines.append("")
    lines.append(f"（仅含近 {OVERDUE_WINDOW_DAYS} 天到期/逾期；更早的逾期待办未列出）")
    return "\n".join(lines)


def build_markdown(todos, now):
    """钉钉机器人 markdown 正文。"""
    time_str = now.strftime("%H:%M")
    sod = start_of_today_ms()
    overdue = [t for t in todos if t["dueTime"] < sod]
    lines = [f"### 📋 每日待办日报 · {now.strftime('%Y-%m-%d')} {time_str}", ""]
    if not todos:
        lines += ["今天到期 / 近 7 天逾期的未完成待办：**0 条** 🎉", "",
                  "今天没有到期或逾期的待办，可以安心处理其他事。"]
        return "\n".join(lines)
    lines.append(f"今天到期 / 近 {OVERDUE_WINDOW_DAYS} 天逾期，共 **{len(todos)}** 条"
                 f"（已逾期 {len(overdue)} 条）：")
    lines.append("")
    for i, t in enumerate(todos, 1):
        subject = t.get("subject", "")
        submitter = parse_submitter(subject)
        title_clean = strip_submitter(subject, submitter)
        marker = "⚠️ " if t["dueTime"] < sod else ""
        lines.append(f"{i}. {marker}**{submitter}**｜{title_clean}")
    lines.append("")
    lines.append(f"> 仅含近 {OVERDUE_WINDOW_DAYS} 天到期/逾期；更早的逾期待办未列出")
    return "\n".join(lines)


def main():
    setup_utf8_console()
    ap = argparse.ArgumentParser(description="钉钉每日待办日报")
    ap.add_argument("--dry-run", action="store_true", help="只预览，不发消息")
    ap.add_argument("--config", default=None, help="配置文件路径")
    args = ap.parse_args()

    cfg = load_config(args.config) if args.config else load_config()
    now = datetime.now()
    print(f"=== 钉钉每日待办日报 {now.strftime('%Y-%m-%d %H:%M')} ===")
    if args.dry_run:
        print("[模式] dry-run（仅预览，不发消息）")

    print("[1/2] 拉取今天到期 + 近 7 天逾期的未完成待办 ...")
    client = McpClient(cfg["mcp_url"])
    todos = fetch_due_today_and_overdue(client)
    print(f"      命中 {len(todos)} 条")

    title = build_title(todos, now.strftime("%Y-%m-%d"))
    body = build_plain_body(todos, now)
    print("\n----- 日报预览 -----")
    print(f"{title}\n")
    print(body)
    print("--------------------\n")

    if args.dry_run:
        print("[dry-run] 未发送。")
        return 0

    print("[2/2] 发送到钉钉机器人 ...")
    md = build_markdown(todos, now)
    result = send_via_robot(cfg["robot_webhook"], cfg["robot_secret"], title, md)
    print(f"      发送成功: {result}")
    print(f"\nSUMMARY: {len(todos)} 条待办，日报已发送到钉钉机器人。")
    return 0


if __name__ == "__main__":
    import sys
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
