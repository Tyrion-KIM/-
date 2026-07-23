#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
物流团队周会信息同步推送

每周三 18:00 生成周会信息文档，通过钉钉机器人发送。

用法：
    python dingtalk_weekly_sync.py --dry-run   # 只预览，不发消息
    python dingtalk_weekly_sync.py             # 正式发送
"""

import argparse
from datetime import date, timedelta

from dingtalk_common import send_via_robot, load_config, setup_utf8_console


MODULES = [
    ("头程", "郑舒漫"),
    ("尾程", "黄婷"),
    ("C端", "吴定佳"),
    ("账单", "张雨洁"),
    ("数字化", "王娜"),
]


def next_thursday():
    """计算最近的周四（明天）"""
    today = date.today()
    days_ahead = 3 - today.weekday()  # Thursday = 3
    if days_ahead <= 0:
        days_ahead += 7
    return today + timedelta(days=days_ahead)


def week_of_month(d):
    """计算是本月第几周"""
    return (d.day - 1) // 7 + 1


def month_cn(d):
    cn = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十", "十一", "十二"]
    idx = d.month - 1
    return cn[idx] + "月"


def build_header(meeting_date):
    week_num = week_of_month(meeting_date)
    return (
        f"**📋 物流团队周会信息同步**\n\n"
        f"**🗓️ 会议时间**：{meeting_date.year}年{meeting_date.month}月{meeting_date.day}日（周四）\n\n"
        f"**📅 本月第 {week_num} 周**\n\n"
        "---\n"
    )


MODULE_TEMPLATE = (
    "## 【{module}】@{person}\n\n"
    "> 请在会前填写以下内容：\n\n"
    "- **本周完成**：\n  -\n"
    "- **下周计划**：\n  -\n"
    "- **需要协调**：\n  -\n"
)


def build_body():
    lines = []
    for module, person in MODULES:
        lines.append(MODULE_TEMPLATE.format(module=module, person=person))
        lines.append("")
    return "\n".join(lines)


def build_markdown(meeting_date):
    lines = [build_header(meeting_date)]
    lines.append(build_body())
    lines.append("> 💡 请各负责人在会前更新本模块内容，会议时逐项过堂。")
    return "\n".join(lines)


def build_plain(meeting_date):
    lines = [f"📋 物流团队周会信息同步", ""]
    lines.append(f"🗓️ 会议时间：{meeting_date.year}年{meeting_date.month}月{meeting_date.day}日（周四）")
    lines.append(f"📅 本月第 {week_of_month(meeting_date)} 周")
    lines.append("")
    for module, person in MODULES:
        lines.append(f"## 【{module}】@{person}")
        lines.append("  - 本周完成：")
        lines.append("  - 下周计划：")
        lines.append("  - 需要协调：")
        lines.append("")
    return "\n".join(lines)


def main():
    setup_utf8_console()
    ap = argparse.ArgumentParser(description="物流团队周会信息同步")
    ap.add_argument("--dry-run", action="store_true", help="只预览，不发消息")
    ap.add_argument("--config", default=None, help="配置文件路径")
    args = ap.parse_args()

    cfg = load_config(args.config) if args.config else load_config()

    meeting_date = next_thursday()
    title = f"📋 物流周会同步 | {meeting_date.month}/{meeting_date.day}（周四）"
    body = build_plain(meeting_date)
    md = build_markdown(meeting_date)

    print(f"=== 物流团队周会信息同步 {date.today().isoformat()} ===")
    if args.dry_run:
        print("[模式] dry-run（仅预览，不发消息）")
    print(f"\n会议时间：{meeting_date}（周四），本月第 {week_of_month(meeting_date)} 周\n")
    print(body)

    if args.dry_run:
        print("\n[dry-run] 未发送。")
        return 0

    print("\n[2/2] 发送到钉钉机器人 ...")
    result = send_via_robot(cfg["robot_webhook"], cfg["robot_secret"], title, md)
    print(f"      发送成功: {result}")
    print(f"\nSUMMARY: 周会同步文档已发送到钉钉机器人。")
    return 0


if __name__ == "__main__":
    import sys
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
