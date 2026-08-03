#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
物流团队周会信息同步推送

每周三 18:00 生成「物流团队周会信息同步」模板，通过钉钉机器人推送：
- 若本地已安装 dws CLI：额外创建一份钉钉在线文档，消息里附带文档链接。
- CI 环境通常没有 dws：直接把完整模板推送到机器人，便于查看与复制。
模板内容（Markdown）由 build_markdown 生成；在线文档通过 dws doc CLI 写入。

用法：
    python dingtalk_weekly_sync.py --dry-run   # 只预览，不发消息
    python dingtalk_weekly_sync.py             # 正式推送（有 dws 则同时建文档）
"""

import argparse
import json
import os
import subprocess
import tempfile
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
# dws doc CLI 封装
# ---------------------------------------------------------------------------

def _extract_json(text):
    """
    从 dws 输出里提取 JSON 对象。
    dws 可能带 [INFO] 日志行，且 --format json 返回美化过的多行 JSON，
    因此不能简单逐行 json.loads。按 整体 → 首尾大括号切片 → 逐行 依次尝试。
    """
    if not text:
        return None
    # 1. 整体解析
    try:
        return json.loads(text)
    except (ValueError, json.JSONDecodeError):
        pass
    # 2. 取首个 { 到末个 } 的切片（剥离前面的 [INFO] 日志行）
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except (ValueError, json.JSONDecodeError):
            pass
    # 3. 逐行解析（兼容历史单行 JSON 输出）
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            return json.loads(line)
        except (ValueError, json.JSONDecodeError):
            continue
    return None


def run_dws(args, timeout=60):
    """
    调用 dws 命令，返回 parsed JSON。
    args: list of str, e.g. ["doc", "create", "--name", "xxx"]
    """
    cmd = ["dws"] + args + ["--format", "json"]
    # Windows 默认按 GBK 解码子进程输出，dws 返回 UTF-8（含中文）会解码失败导致 stdout=None，
    # 显式指定 UTF-8 + replace 兜底。
    result = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=timeout,
    )
    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()

    parsed = _extract_json(stdout)
    if parsed is not None:
        return parsed

    # 无 JSON 输出
    if stderr:
        raise RuntimeError(f"dws 命令执行失败: {stderr[:500]}")
    raise RuntimeError(f"dws 命令无有效输出: {stdout[:200]}")


def create_dingtalk_doc(title, markdown_content):
    """
    通过 dws doc create 创建钉钉在线文档，写入 Markdown 内容。
    返回文档 nodeId 和访问 URL。
    """
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", encoding="utf-8", delete=False
    ) as f:
        f.write(markdown_content)
        tmp_path = f.name

    try:
        # 写入内容较长，用 --content-file 避免 shell escape 问题
        result = run_dws(
            ["doc", "create", "--name", title, "--content-file", tmp_path],
            timeout=120,
        )
    finally:
        os.unlink(tmp_path)

    node_id = result.get("nodeId", "")
    if not node_id:
        raise RuntimeError(f"钉钉文档创建失败，未返回 nodeId: {result}")

    doc_url = f"https://alidocs.dingtalk.com/i/nodes/{node_id}"
    return doc_url, node_id


# ---------------------------------------------------------------------------
# Markdown 内容构建器
# ---------------------------------------------------------------------------

def build_markdown(meeting_date):
    """构建周会文档的 Markdown 内容。"""
    week_num = week_of_month(meeting_date)
    date_short = f"{meeting_date.year} / {meeting_date.month:02d}/{meeting_date.day:02d}"

    md = f"""# 物流团队周会信息同步文档

## {date_short} — {meeting_date.month}月第{week_num}周

---

### 使用说明

> - 本文档用于物流团队每周内部例会，**会前 1 小时**由各模块负责人填写，会中 20 分钟快速过进度。
> - **填写原则**：数据先行、异常必报、闭环上周、明确下周，没有数据支撑的结论不写。
> - **加粗 / 红色**项为必填；黄色高亮用于标注异常或需决策事项。
> - 会后将本页内容归档到共享盘，并生成《本周行动项》跟踪表。

---

## 上周行动项闭环

> 上周会议产出的 action items，必须逐项回复状态；未完成需说明原因和新 deadline。

| 序号 | 行动项 | 责任人 | Deadline | 完成状态 | 备注 |
|------|--------|--------|----------|----------|------|
| 1 |  |  |  | 进行中 / 已完成 / 已取消 / |  |
| 2 |  |  |  | 进行中 / 已完成 / 已取消 / |  |
| 3 |  |  |  | 进行中 / 已完成 / 已取消 / |  |
| 4 |  |  |  | 进行中 / 已完成 / 已取消 / |  |

---

## 头程 @郑舒漫

> 负责人：郑舒漫    填写说明：本周关键进展、数据、异常、下周动作，用要点呈现，避免大段文字。

| 维度 | 本周情况 | 下周计划 / 需协调事项 |
|------|----------|------------------------|
| 本周发运情况 |  |  |
| 在途 / 到港货物 |  |  |
| 海运船期与市场价 |  |  |
| 发运计划（下周） |  |  |
| 成本与异常 |  |  |
| 其他补充 |  |  |

---

## 尾程 — B 端 @黄婷

> 负责人：黄婷    填写说明：本周关键进展、数据、异常、下周动作，用要点呈现，避免大段文字。

| 维度 | 本周情况 | 下周计划 / 需协调事项 |
|------|----------|------------------------|
| 本周发货量 |  |  |
| 签收与时效 |  |  |
| 单台费用 |  |  |
| 订单流程卡点 |  |  |
| 库存可视度 |  |  |
| 其他补充 |  |  |

---

## 尾程 + 库存 — C 端 @吴定佳

> 负责人：吴定佳    填写说明：本周关键进展、数据、异常、下周动作，用要点呈现，避免大段文字。

| 维度 | 本周情况 | 下周计划 / 需协调事项 |
|------|----------|------------------------|
| 本周发货量 |  |  |
| 渠道拆分 |  |  |
| 单台费用 |  |  |
| 异常订单 |  |  |
| 缺货 / 库存 |  |  |
| 售后衔接 |  |  |
| 其他补充 |  |  |

---

## 账单 / 财务 @张雨洁

> 负责人：张雨洁    填写说明：本周关键进展、数据、异常、下周动作，用要点呈现，避免大段文字。

| 维度 | 本周情况 | 下周计划 / 需协调事项 |
|------|----------|------------------------|
| 本月到账单据 |  |  |
| 对账差异 |  |  |
| 付款计划 |  |  |
| 费用异常 |  |  |
| 需支持事项 |  |  |
| 其他补充 |  |  |

---

## 数字化 / 系统 @王娜

> 负责人：王娜    填写说明：本周关键进展、数据、异常、下周动作，用要点呈现，避免大段文字。

| 维度 | 本周情况 | 下周计划 / 需协调事项 |
|------|----------|------------------------|
| 系统上线进展 |  |  |
| 数据看板 |  |  |
| 流程自动化 |  |  |
| 异常与支持 |  |  |
| 下周计划 |  |  |
| 其他补充 |  |  |

---

## 异常 / 风险 / 卡点（本周必须讨论）

> 请各模块负责人填写本周遇到的异常、风险或需会议决策的卡点事项。

| 模块 | 异常描述 | 影响范围 | 建议对策 |
|------|----------|----------|----------|
|  |  |  |  |

---

## 本周重点事项

> 请填写本周最重要的 1-3 项事项。

1.

---

> **提示**：请各负责人在会前 1 小时完成本模块内容，会议时逐项过堂。
"""
    return md


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

    markdown = build_markdown(meeting_date)
    print(markdown)

    if args.dry_run:
        print("\n[dry-run] 仅预览，未发送。")
        return 0

    # [1/2] 尽力创建钉钉在线文档（需本地安装 dws CLI；CI 环境通常没有，会自动跳过）
    print("\n[1/2] 尝试创建钉钉在线文档 ...")
    doc_url = None
    try:
        doc_url, _node_id = create_dingtalk_doc(title, markdown)
        print(f"      文档已创建: {doc_url}")
    except FileNotFoundError:
        print("      [INFO] 未检测到 dws CLI（CI 环境），跳过在线文档创建，将模板直接推送至机器人。")
    except Exception as e:
        print(f"      [WARN] 钉钉文档创建失败: {type(e).__name__}: {e}", flush=True)
        print(f"      将模板直接推送至机器人，继续 ...")

    # [2/2] 发送周会内容到钉钉机器人
    #   - 有在线文档：推送「文档链接 + 议程」，引导大家在文档里填写
    #   - 无在线文档（CI）：直接把完整模板推送到机器人，便于查看与复制
    print("\n[2/2] 发送周会内容到钉钉机器人 ...")
    if doc_url:
        robot_md = (
            f"## 📋 物流团队周会信息同步\n\n"
            f"**会议时间**：{meeting_date.month}月{meeting_date.day}日（周四）· 本月第 {week_num} 周\n\n"
            f"📄 [点击打开周会文档并填写]({doc_url})\n\n"
            f"**议程**：上周行动项闭环 → 头程 → 尾程(B端/C端) → 账单 → 数字化 → 异常/风险 → 本周重点\n\n"
            f"> 请各负责人会前 1 小时完成本模块填写，会议时逐项过堂。"
        )
    else:
        robot_md = (
            f"## 📋 物流团队周会信息同步\n\n"
            f"**会议时间**：{meeting_date.month}月{meeting_date.day}日（周四）· 本月第 {week_num} 周\n\n"
            f"> 请各负责人会前 1 小时完成本模块填写，会议时逐项过堂。\n\n"
            f"---\n\n{markdown}"
        )

    result = send_via_robot(cfg["robot_webhook"], cfg["robot_secret"], title, robot_md)
    print(f"      发送成功: {result}")
    if doc_url:
        print(f"\nSUMMARY: 周会在线文档已创建，链接已发送到钉钉机器人。")
    else:
        print(f"\nSUMMARY: 周会模板已直接发送到钉钉机器人（未创建在线文档）。")
    return 0


if __name__ == "__main__":
    import sys
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
