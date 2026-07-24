#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
物流团队周会信息同步推送

每周三 18:00 生成周会信息文档（飞书在线文档），通过钉钉机器人发送链接。
文档内容通过飞书 Blocks API 构建，支持 text/heading/bullet/divider 四种块类型。

用法：
    python dingtalk_weekly_sync.py --dry-run   # 只预览，不发消息
    python dingtalk_weekly_sync.py             # 正式创建文档并发送链接
"""

import argparse
import json
import os
import urllib.error
import urllib.request
from datetime import date, timedelta

from dingtalk_common import send_via_robot, load_config, setup_utf8_console


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def next_thursday():
    """计算最近的周四（即周会的日期）。"""
    today = date.today()
    days_ahead = 3 - today.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return today + timedelta(days_ahead)


def week_of_month(d):
    return (d.day - 1) // 7 + 1


# ---------------------------------------------------------------------------
# 飞书 API
# ---------------------------------------------------------------------------

def get_feishu_token(app_id, app_secret):
    """通过 App ID + App Secret 获取 tenant_access_token。"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"飞书 token API HTTP {e.code}: {detail}") from e
    if result.get("code") != 0:
        raise RuntimeError(f"飞书 token 获取失败: {result}")
    token = result.get("tenant_access_token", "")
    if not token:
        raise RuntimeError("飞书 token 为空")
    return token


def feishu_api(method, path, token, payload=None):
    """通用飞书 API 请求。"""
    url = f"https://open.feishu.cn{path}"
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload else None
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"飞书 API {method} {path} HTTP {e.code}: {detail}") from e


def create_feishu_doc(title, blocks):
    """
    通过飞书 Blocks API 创建在线文档，返回文档链接。
    blocks: list of Feishu block dict
    """
    _cfg = {}
    _path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    if os.path.exists(_path):
        with open(_path, "r", encoding="utf-8") as _f:
            _cfg = json.load(_f)

    app_id = os.environ.get("FEISHU_APP_ID") or _cfg.get("feishu_app_id", "")
    app_secret = os.environ.get("FEISHU_APP_SECRET") or _cfg.get("feishu_app_secret", "")
    if not app_id or not app_secret:
        raise RuntimeError(
            "未配置飞书凭证。请在 config.json 中填写 feishu_app_id 和 feishu_app_secret，"
            "或在环境变量中设置 FEISHU_APP_ID 和 FEISHU_APP_SECRET。"
        )

    token = get_feishu_token(app_id, app_secret)

    # 1. 创建空文档
    doc_result = feishu_api("POST", "/open-apis/docx/v1/documents", token, {"title": title})
    doc_id = doc_result.get("data", {}).get("document", {}).get("document_id", "")
    if not doc_id:
        raise RuntimeError(f"文档创建失败: {doc_result}")

    # 2. 获取文档根 block_id
    doc_info = feishu_api("GET", f"/open-apis/docx/v1/documents/{doc_id}", token)
    root_id = doc_info.get("data", {}).get("document", {}).get("document_id", doc_id)

    # 3. 批量添加子块（每次最多 50 个）
    blocks_url = f"/open-apis/docx/v1/documents/{doc_id}/blocks/{root_id}/children"
    for i in range(0, len(blocks), 50):
        batch = blocks[i:i + 50]
        result = feishu_api("POST", blocks_url, token, {"children": batch, "index": i})
        if result.get("code") != 0:
            raise RuntimeError(f"添加 blocks 失败: {result}")

    return f"https://my.feishu.cn/docx/{doc_id}", doc_id


# ---------------------------------------------------------------------------
# Feishu Block 构建器
# ---------------------------------------------------------------------------

# Block type constants
T_TEXT   = 2
T_H1     = 3
T_H2     = 4
T_H3     = 5
T_BULLET = 12
T_DIV    = 22


def bold(text):
    return {"bold": True}


def run(text, **style):
    return {"text_run": {"content": text, "text_element_style": style}}


def text_block(*parts):
    """纯文本段落。parts 可以是 (text,) 或 (text, style_dict)"""
    elements = []
    for p in parts:
        if isinstance(p, dict):
            elements.append(p)
        else:
            elements.append(run(p))
    return {"block_type": T_TEXT, "text": {"elements": elements, "style": {"align": 1, "folded": False}}}


def h1(text):
    return {"block_type": T_H1, "heading1": {
        "elements": [run(text, bold=True)],
        "style": {"align": 1, "folded": False}
    }}


def h2(text):
    return {"block_type": T_H2, "heading2": {
        "elements": [run(text, bold=True)],
        "style": {"align": 1, "folded": False}
    }}


def h3(text):
    return {"block_type": T_H3, "heading3": {
        "elements": [run(text, bold=True)],
        "style": {"align": 1, "folded": False}
    }}


def bullet(text, indent=1):
    return {"block_type": T_BULLET, "bullet": {
        "elements": [run(text)],
        "style": {"align": 1, "folded": False, "indent_level": indent}
    }}


def bullet_bold(text, indent=1):
    return {"block_type": T_BULLET, "bullet": {
        "elements": [run(text, bold=True)],
        "style": {"align": 1, "folded": False, "indent_level": indent}
    }}


def divider():
    return {"block_type": T_DIV, "divider": {"style": 1}}


def blank():
    return text_block(" ")


def dim_row(dim_text, this_week="", next_week=""):
    """生成一个维度表格行（用 bullet list 模拟）。"""
    return bullet(f"{dim_text}  |  {this_week}  |  {next_week}", indent=1)


# ---------------------------------------------------------------------------
# 文档内容构建
# ---------------------------------------------------------------------------

def build_blocks(meeting_date):
    """
    直接构建 Feishu blocks，返回列表。
    """
    week_num = week_of_month(meeting_date)
    date_short = f"{meeting_date.year} / {meeting_date.month:02d}/{meeting_date.day:02d}"

    blocks = []

    # 标题
    blocks.append(h1("物流团队周会信息同步文档"))
    blocks.append(blank())
    blocks.append(h1(f"{date_short} - {meeting_date.month}月第{week_num}周"))
    blocks.append(blank())

    # 使用说明
    blocks.append(bullet_bold("使用说明", indent=0))
    blocks.append(bullet("本文档用于物流团队每周内部例会，会前 1 小时由各模块负责人填写，会中 20 分钟快速过进度。"))
    blocks.append(bullet("填写原则：数据先行、异常必报、闭环上周、明确下周，没有数据支撑的结论不写。"))
    blocks.append(bullet("红色 / 加粗项为必填；黄色高亮用于标注异常或需决策事项。"))
    blocks.append(bullet("会后将本页内容归档到共享盘，并生成《本周行动项》跟踪表。"))
    blocks.append(blank())
    blocks.append(divider())
    blocks.append(blank())

    # 上周行动项闭环
    blocks.append(h2("上周行动项闭环"))
    blocks.append(bullet("上周会议产出的 action items，必须逐项回复状态；未完成需说明原因和新 deadline。"))
    blocks.append(blank())
    blocks.append(bullet_bold("序号 | 行动项 | 责任人 | Deadline | 完成状态 | 备注", indent=0))
    blocks.append(bullet("1 |  |  |  | / 进行中 / | "))
    blocks.append(bullet("2 |  |  |  | / 进行中 / | "))
    blocks.append(bullet("3 |  |  |  | / 进行中 / | "))
    blocks.append(bullet("4 |  |  |  | / 进行中 / | "))
    blocks.append(blank())
    blocks.append(divider())
    blocks.append(blank())

    # 头程
    blocks.append(h2("头程 @郑舒漫"))
    blocks.append(text_block("负责人：郑舒漫    填写说明：本周关键进展、数据、异常、下周动作，用要点呈现，避免大段文字。"))
    blocks.append(blank())
    blocks.append(bullet_bold("维度 | 本周情况 | 下周计划 / 需协调事项", indent=0))
    blocks.append(dim_row("本周发运情况"))
    blocks.append(dim_row("在途/到港货物"))
    blocks.append(dim_row("海运船期与市场价"))
    blocks.append(dim_row("发运计划（下周）"))
    blocks.append(dim_row("成本与异常"))
    blocks.append(dim_row("其他补充"))
    blocks.append(blank())
    blocks.append(divider())
    blocks.append(blank())

    # 尾程-B端
    blocks.append(h2("尾程 — B 端 @黄婷"))
    blocks.append(text_block("负责人：黄婷    填写说明：本周关键进展、数据、异常、下周动作，用要点呈现，避免大段文字。"))
    blocks.append(blank())
    blocks.append(bullet_bold("维度 | 本周情况 | 下周计划 / 需协调事项", indent=0))
    blocks.append(dim_row("本周发货量"))
    blocks.append(dim_row("签收与时效"))
    blocks.append(dim_row("单台费用"))
    blocks.append(dim_row("订单流程卡点"))
    blocks.append(dim_row("库存可视度"))
    blocks.append(dim_row("其他补充"))
    blocks.append(blank())
    blocks.append(divider())
    blocks.append(blank())

    # 尾程+库存-C端
    blocks.append(h2("尾程+库存 — C 端 @吴定佳"))
    blocks.append(text_block("负责人：吴定佳    填写说明：本周关键进展、数据、异常、下周动作，用要点呈现，避免大段文字。"))
    blocks.append(blank())
    blocks.append(bullet_bold("维度 | 本周情况 | 下周计划 / 需协调事项", indent=0))
    blocks.append(dim_row("本周发货量"))
    blocks.append(dim_row("渠道拆分"))
    blocks.append(dim_row("单台费用"))
    blocks.append(dim_row("异常订单"))
    blocks.append(dim_row("缺货/库存"))
    blocks.append(dim_row("售后衔接"))
    blocks.append(dim_row("其他补充"))
    blocks.append(blank())
    blocks.append(divider())
    blocks.append(blank())

    # 账单
    blocks.append(h2("账单 / 财务 @张雨洁"))
    blocks.append(text_block("负责人：张雨洁    填写说明：本周关键进展、数据、异常、下周动作，用要点呈现，避免大段文字。"))
    blocks.append(blank())
    blocks.append(bullet_bold("维度 | 本周情况 | 下周计划 / 需协调事项", indent=0))
    blocks.append(dim_row("本月到账单据"))
    blocks.append(dim_row("对账差异"))
    blocks.append(dim_row("付款计划"))
    blocks.append(dim_row("费用异常"))
    blocks.append(dim_row("需支持事项"))
    blocks.append(dim_row("其他补充"))
    blocks.append(blank())
    blocks.append(divider())
    blocks.append(blank())

    # 数字化
    blocks.append(h2("数字化 / 系统 @王娜"))
    blocks.append(text_block("负责人：王娜    填写说明：本周关键进展、数据、异常、下周动作，用要点呈现，避免大段文字。"))
    blocks.append(blank())
    blocks.append(bullet_bold("维度 | 本周情况 | 下周计划 / 需协调事项", indent=0))
    blocks.append(dim_row("系统上线进展"))
    blocks.append(dim_row("数据看板"))
    blocks.append(dim_row("流程自动化"))
    blocks.append(dim_row("异常与支持"))
    blocks.append(dim_row("下周计划"))
    blocks.append(dim_row("其他补充"))
    blocks.append(blank())
    blocks.append(divider())
    blocks.append(blank())

    # 异常/风险
    blocks.append(h2("异常 / 风险 / 卡点（本周必须讨论）"))
    blocks.append(bullet("请各模块负责人填写本周遇到的异常、风险或需会议决策的卡点事项"))
    blocks.append(blank())
    blocks.append(divider())
    blocks.append(blank())

    # 本周重点事项
    blocks.append(h2("本周重点事项"))
    blocks.append(bullet("请填写本周最重要的 1-3 项事项"))
    blocks.append(blank())
    blocks.append(divider())
    blocks.append(blank())
    blocks.append(text_block("💡 请各负责人在会前 1 小时完成本模块内容，会议时逐项过堂。"))

    return blocks


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
        "| 本周发运情况 | 在途/到港货物 | 海运船期 | 发运计划 | 成本与异常 |",
        "",
        "## 尾程 — B 端 @黄婷",
        "| 本周发货量 | 签收与时效 | 单台费用 | 订单流程卡点 |",
        "",
        "## 尾程+库存 — C 端 @吴定佳",
        "| 本周发货量 | 渠道拆分 | 单台费用 | 异常订单 | 缺货/库存 |",
        "",
        "## 账单 / 财务 @张雨洁",
        "| 本月到账单据 | 对账差异 | 付款计划 | 费用异常 |",
        "",
        "## 数字化 / 系统 @王娜",
        "| 系统上线进展 | 数据看板 | 流程自动化 | 下周计划 |",
        "",
        "## 异常 / 风险 / 卡点（请填写）",
        "## 本周重点事项（请填写）",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

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

    print(f"=== 物流团队周会信息同步 {date.today().isoformat()} ===")
    if args.dry_run:
        print("[模式] dry-run（仅预览，不发消息）")
    print(f"\n会议时间：{meeting_date}（周四），本月第 {week_num} 周\n")
    print(build_plain(meeting_date))

    if args.dry_run:
        print("\n[dry-run] 未发送。")
        return 0

    print("\n[1/2] 创建飞书文档 ...")
    try:
        blocks = build_blocks(meeting_date)
        print(f"      生成 {len(blocks)} 个 blocks")
    except Exception as e:
        print(f"      [ERROR] build_blocks 失败: {type(e).__name__}: {e}", flush=True)
        raise
    try:
        doc_url, doc_id = create_feishu_doc(title, blocks)
        print(f"      文档已创建: {doc_url}")
    except Exception as e:
        print(f"      [ERROR] create_feishu_doc 失败: {type(e).__name__}: {e}", flush=True)
        raise

    print("\n[2/2] 发送文档链接到钉钉机器人 ...")
    robot_md = (
        f"## 📋 物流团队周会信息同步\n\n"
        f"**会议时间**：{meeting_date.month}月{meeting_date.day}日（周四）\n"
        f"**本月第 {week_num} 周**\n\n"
        f"📄 [点击查看并填写周会文档]({doc_url})\n\n"
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
