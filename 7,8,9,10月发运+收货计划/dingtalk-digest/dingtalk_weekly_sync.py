#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
物流团队周会信息同步推送

每周三 18:00 生成周会信息文档，通过飞书文档创建+钉钉机器人发送链接。

用法：
    python dingtalk_weekly_sync.py --dry-run   # 只预览，不发消息
    python dingtalk_weekly_sync.py             # 正式创建文档并发送链接
"""

import argparse
import json
import urllib.request
from datetime import date, timedelta

from dingtalk_common import send_via_robot, load_config, setup_utf8_console


# ----------------------------------------------------------------------
# 工具函数
# ----------------------------------------------------------------------

def next_thursday():
    """计算最近的周四（即周会的日期）。"""
    today = date.today()
    days_ahead = 3 - today.weekday()  # Thursday = 3
    if days_ahead <= 0:
        days_ahead += 7
    return today + timedelta(days=days_ahead)


def week_of_month(d):
    return (d.day - 1) // 7 + 1


def month_cn(d):
    cn = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十", "十一", "十二"]
    return cn[d.month - 1] + "月"


# ----------------------------------------------------------------------
# 飞书文档创建
# ----------------------------------------------------------------------

def create_doc(title, markdown_content):
    """
    通过 Feishu MCP (docx_builtin_import) 创建在线文档，返回 (文档链接, doc_id)。
    """
    import os
    # 从环境变量读取 Feishu MCP token
    # 优先读环境变量，兼容 CI
    lark_token = os.environ.get("FEISHU_MCP_TOKEN") or os.environ.get("LARK_MCP_TOKEN")
    if not lark_token:
        raise RuntimeError(
            "未找到 Feishu MCP token。请设置环境变量 FEISHU_MCP_TOKEN 或 LARK_MCP_TOKEN，"
            "或联系管理员配置飞书文档创建权限。"
        )

    url = "https://open.feishu.cn/open-apis/docx/v1/documents/import"
    payload = {
        "file_name": title,
        "docx_format": "md",
        "markdown_content": markdown_content,
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {lark_token}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"飞书文档 API HTTP {e.code}: {detail}") from e
    except Exception as e:
        raise RuntimeError(f"飞书文档创建请求失败: {e}") from e

    if result.get("code") != 0:
        raise RuntimeError(f"飞书文档创建失败: {result}")

    doc_id = result.get("data", {}).get("document", {}).get("document_id", "")
    doc_url = f"https://my.feishu.cn/docx/{doc_id}"
    return doc_url, doc_id


# ----------------------------------------------------------------------
# 文档内容构建
# ----------------------------------------------------------------------

def _dim_row(dim, filled=False):
    """生成一个维度表格行。filled=True 时填入示例内容占位。"""
    val = "" if not filled else "(请填写)"
    return f"| **{dim}** | {val} | {val} |"


def _module_section(name, person, dims, filled=False):
    """生成单个模块的 Markdown 段落。"""
    lines = [
        f"## {name} @{person}",
        "",
        f"负责人：{person}    填写说明：本周关键进展、数据、异常、下周动作，用要点呈现，避免大段文字。",
        "",
        "| **维度** | **本周情况** | **下周计划 / 需协调事项** |",
        "| --- | --- | --- |",
    ]
    for dim in dims:
        lines.append(_dim_row(dim, filled))
    lines.append("")
    return "\n".join(lines)


def build_doc_markdown(meeting_date):
    """
    构建完整的周会文档 Markdown，格式对齐「物流团队周会信息同步文档.md」模板。
    """
    week_num = week_of_month(meeting_date)
    date_short = f"{meeting_date.year} / {meeting_date.month:02d}/{meeting_date.day:02d}"

    lines = [
        "# 物流团队周会信息同步文档",
        "",
        f"# {date_short} - {meeting_date.month}月第{week_num}周",
        "",
        "> **使用说明**",
        ">",
        "> - 本文档用于物流团队每周内部例会，会前 1 小时由各模块负责人填写，会中 20 分钟快速过进度。",
        "> - 填写原则：数据先行、异常必报、闭环上周、明确下周。没有数据支撑的结论不写。",
        "> - 红色 / 加粗项为必填；黄色高亮用于标注异常或需决策事项。",
        "> - 会后将本页内容归档到共享盘，并生成《本周行动项》跟踪表。",
        "",
        "---",
        "",
        "## 上周行动项闭环",
        "",
        "上周会议产出的 action items，必须逐项回复状态；未完成需说明原因和新 deadline。",
        "",
        "| **序号** | **行动项** | **责任人** | **Deadline** | **完成状态** | **备注 / 卡点** |",
        "| --- | --- | --- | --- | --- | --- |",
        "| 1 |  |  |  | / 进行中 / |  |",
        "| 2 |  |  |  | / 进行中 / |  |",
        "| 3 |  |  |  | / 进行中 / |  |",
        "| 4 |  |  |  | / 进行中 / |  |",
        "",
        "---",
        "",
    ]

    # 头程
    lines.append(_module_section("头程", "郑舒漫", [
        "本周发运情况",
        "在途/到港货物",
        "海运船期与市场价",
        "发运计划（下周）",
        "成本与异常",
        "其他补充",
    ]))
    lines.append("")

    # 尾程-B端
    lines.append(_module_section("尾程 — B 端", "黄婷", [
        "本周发货量",
        "签收与时效",
        "单台费用",
        "订单流程卡点",
        "库存可视度",
        "其他补充",
    ]))
    lines.append("")

    # 尾程+库存-C端
    lines.append(_module_section("尾程+库存 — C 端", "吴定佳", [
        "本周发货量",
        "渠道拆分",
        "单台费用",
        "异常订单",
        "缺货/库存",
        "售后衔接",
        "其他补充",
    ]))
    lines.append("")

    # 账单
    lines.append(_module_section("账单 / 财务", "张雨洁", [
        "本月到账单据",
        "对账差异",
        "付款计划",
        "费用异常",
        "需支持事项",
        "其他补充",
    ]))
    lines.append("")

    # 数字化
    lines.append(_module_section("数字化 / 系统", "王娜", [
        "系统上线进展",
        "数据看板",
        "流程自动化",
        "异常与支持",
        "下周计划",
        "其他补充",
    ]))
    lines.append("")

    # 异常/风险
    lines.extend([
        "## 异常 / 风险 / 卡点（本周必须讨论）",
        "",
        "（请各模块负责人填写本周遇到的异常、风险或需会议决策的卡点事项）",
        "",
        "---",
        "",
        "## 本周重点事项",
        "",
        "1. （请填写本周最重要的 1-3 项事项）",
        "",
        "---",
        "",
        "> 💡 文档填写完成后，请各负责人在会前 1 小时完成本模块内容，会议时逐项过堂。",
    ])

    return "\n".join(lines)


def build_plain(meeting_date):
    """构建纯文本预览（控制台 dry-run 输出）。"""
    week_num = week_of_month(meeting_date)
    date_short = f"{meeting_date.year}/{meeting_date.month:02d}/{meeting_date.day:02d}"
    lines = [
        f"=== 物流团队周会信息同步 {date.today().isoformat()} ===",
        f"会议时间：{meeting_date}（周四），本月第 {week_num} 周",
        "",
        f"# {date_short} - {meeting_date.month}月第{week_num}周",
        "",
        "## 上周行动项闭环",
        "| 序号 | 行动项 | 责任人 | Deadline | 完成状态 | 备注 |",
        "| 1 | | | | / 进行中 / | |",
        "| 2 | | | | / 进行中 / | |",
        "",
        "## 头程 @郑舒漫",
        "| 维度 | 本周情况 | 下周计划 |",
        "| 本周发运情况 | | |",
        "| 在途/到港货物 | | |",
        "| 海运船期与市场价 | | |",
        "| 发运计划（下周） | | |",
        "| 成本与异常 | | |",
        "",
        "## 尾程 — B 端 @黄婷",
        "| 维度 | 本周情况 | 下周计划 |",
        "| 本周发货量 | | |",
        "| 签收与时效 | | |",
        "| 单台费用 | | |",
        "| 订单流程卡点 | | |",
        "",
        "## 尾程+库存 — C 端 @吴定佳",
        "| 维度 | 本周情况 | 下周计划 |",
        "| 本周发货量 | | |",
        "| 渠道拆分 | | |",
        "| 单台费用 | | |",
        "| 异常订单 | | |",
        "| 缺货/库存 | | |",
        "",
        "## 账单 / 财务 @张雨洁",
        "| 维度 | 本周情况 | 下周计划 |",
        "| 本月到账单据 | | |",
        "| 对账差异 | | |",
        "| 付款计划 | | |",
        "| 费用异常 | | |",
        "",
        "## 数字化 / 系统 @王娜",
        "| 维度 | 本周情况 | 下周计划 |",
        "| 系统上线进展 | | |",
        "| 数据看板 | | |",
        "| 流程自动化 | | |",
        "| 下周计划 | | |",
        "",
        "## 异常 / 风险 / 卡点",
        "（请填写）",
        "",
        "## 本周重点事项",
        "（请填写）",
    ]
    return "\n".join(lines)


# ----------------------------------------------------------------------
# 主入口
# ----------------------------------------------------------------------

def main():
    setup_utf8_console()
    ap = argparse.ArgumentParser(description="物流团队周会信息同步")
    ap.add_argument("--dry-run", action="store_true", help="只预览，不发消息")
    ap.add_argument("--config", default=None, help="配置文件路径")
    args = ap.parse_args()

    cfg = load_config(args.config) if args.config else load_config()

    meeting_date = next_thursday()
    week_num = week_of_month(meeting_date)
    title = f"物流周会同步 | {meeting_date.month}/{meeting_date.day}（周四）第{week_num}周"
    doc_md = build_doc_markdown(meeting_date)

    print(f"=== 物流团队周会信息同步 {date.today().isoformat()} ===")
    if args.dry_run:
        print("[模式] dry-run（仅预览，不发消息）")
    print(f"\n会议时间：{meeting_date}（周四），本月第 {week_num} 周\n")
    print(build_plain(meeting_date))

    if args.dry_run:
        print("\n[dry-run] 未发送。")
        return 0

    print("\n[1/2] 创建飞书文档 ...")
    doc_url, doc_id = create_doc(title, doc_md)
    print(f"      文档已创建: {doc_url}")

    print("\n[2/2] 发送文档链接到钉钉机器人 ...")
    robot_md = (
        f"## 📋 物流团队周会信息同步\n\n"
        f"**会议时间**：{meeting_date.month}月{meeting_date.day}日（周四）\n"
        f"**本月第 {week_num} 周**\n\n"
        f"👉 [点击查看并填写周会文档]({doc_url})\n\n"
        f"> 请各负责人在会前 1 小时完成本模块内容，会议时逐项过堂。"
    )
    result = send_via_robot(cfg["robot_webhook"], cfg["robot_secret"], title, robot_md)
    print(f"      发送成功: {result}")
    print(f"\nSUMMARY: 周会同步文档已创建并链接已发送到钉钉机器人。")
    return 0


if __name__ == "__main__":
    import sys
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
