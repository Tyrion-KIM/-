#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
钉钉团队任务表每周简报

每周一自动拉取钉钉 AI 表格中的未完成任务，按负责人分组，
显示距离截止日期天数，通过钉钉自定义机器人 Webhook 发送。

用法：
    python dingtalk_task_weekly.py --dry-run           # 预览
    python dingtalk_task_weekly.py --build-user-map    # 生成 user_map.json 模板
    python dingtalk_task_weekly.py                     # 正式发送
"""

import argparse
import json
import os
from collections import defaultdict
from datetime import datetime, date, timedelta

from dingtalk_common import McpClient, send_via_robot, load_config, setup_utf8_console

HERE = os.path.dirname(os.path.abspath(__file__))
USER_MAP_PATH = os.path.join(HERE, "user_map.json")

# 字段 ID（从 get_fields 获取）
FIELD_TASK = "jxzfinmckxuusjowbz5ca"      # 待办事项
FIELD_DUE = "153qqi6uj540iw0thx4gs"       # 截止日期
FIELD_DONE = "ceg6ny4yi4pzc9wg2rmm3"      # 是否完成
FIELD_PRIORITY = "tp2wvatuqgb43y14t90gp"  # 优先级
FIELD_EXECUTOR = "v4qng51vfjjxe7mryzci7"  # 执行人
FIELD_ASSIGNER = "PSDU9Db"                # 指派人
FIELD_OWNER = "QpqMGQP"                   # 责任人（负责人）


def load_user_map():
    if not os.path.exists(USER_MAP_PATH):
        return {}
    with open(USER_MAP_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_user_map(m):
    with open(USER_MAP_PATH, "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=2)


def user_name(user_list, user_map):
    """从 user 字段提取显示名。"""
    if not user_list:
        return None
    u = user_list[0]
    name = u.get("userName") or u.get("name")
    if name:
        return name
    uid = u.get("userId")
    if uid and str(uid) in user_map:
        return user_map[str(uid)]
    if uid:
        return str(uid)
    return None


def fetch_incomplete_records(client, base_id, table_id):
    """分页拉取所有未完成记录。"""
    records = []
    cursor = None
    while True:
        args = {
            "baseId": base_id,
            "tableId": table_id,
            "limit": 100,
            "filters": {
                "operator": "and",
                "operands": [{
                    "operator": "eq",
                    "operands": [FIELD_DONE, "false"],
                }],
            },
        }
        if cursor:
            args["cursor"] = cursor
        data = client.call_tool("query_records", args)
        if not isinstance(data, dict):
            break
        # AI 表格网关直接返回 {data:{records,nextCursor}}，没有 result 包裹
        payload = data.get("data") or data.get("result") or data
        batch = payload.get("records", []) or []
        records.extend(batch)
        cursor = payload.get("nextCursor")
        if not cursor or len(records) >= 2000:
            break
    return records


def parse_date(cell_value):
    """解析日期字段为 date 对象。"""
    if not cell_value:
        return None
    if isinstance(cell_value, str):
        try:
            return datetime.fromisoformat(cell_value.replace("Z", "+00:00")).date()
        except ValueError:
            return None
    return None


def days_to_due(due_date, today):
    if not due_date:
        return None, "无截止日期"
    delta = (due_date - today).days
    if delta < 0:
        return delta, f"已逾期 {abs(delta)} 天"
    if delta == 0:
        return delta, "今天截止"
    return delta, f"剩余 {delta} 天"


def extract_task(rec, user_map):
    cells = rec.get("cells", {})
    task = cells.get(FIELD_TASK, "（无标题）")
    due = parse_date(cells.get(FIELD_DUE))
    priority = (cells.get(FIELD_PRIORITY) or {}).get("name", "")

    # 负责人严格使用「责任人」字段；空则归为「未分配」
    owner = user_name(cells.get(FIELD_OWNER), user_map) or "未分配"

    return {"task": task, "due": due, "priority": priority, "owner": owner, "raw_record": rec}


def build_report(records, today, user_map):
    tasks = [extract_task(r, user_map) for r in records]
    # 按负责人分组，组内按截止日期排序
    groups = defaultdict(list)
    for t in tasks:
        groups[t["owner"]].append(t)
    for owner in groups:
        # 逾期最严重的在前，未来按截止日期近远，无截止日期排最后
        groups[owner].sort(key=lambda x: (
            2 if x["due"] is None else (0 if x["due"] < today else 1),
            x["due"] if x["due"] else date.max,
        ))

    # 排序负责人：未分配放最后，其余按任务数降序
    owners = sorted(groups.keys(), key=lambda o: (o == "未分配", -len(groups[o]), o))

    overdue_count = sum(1 for t in tasks if t["due"] and t["due"] < today)
    return groups, owners, len(tasks), overdue_count


def build_title(total, overdue, report_date):
    if total == 0:
        return f"📊 团队任务周报 · {report_date.strftime('%m-%d')}（无未完成任务 🎉）"
    return f"📊 团队任务周报 · {report_date.strftime('%m-%d')}（未完成 {total} 条，逾期 {overdue} 条）"


def build_plain_body(groups, owners, total, overdue, today, missing_ids):
    title = build_title(total, overdue, today)
    lines = [title.replace("📊 ", "📌 "), ""]
    if total == 0:
        lines.append("本周没有未完成的任务。")
        return "\n".join(lines)
    lines.append(f"本周未完成共 {total} 条，其中逾期 {overdue} 条：")
    lines.append("")
    for owner in owners:
        lines.append(f"**{owner}（{len(groups[owner])} 条）**")
        for i, t in enumerate(groups[owner], 1):
            _, due_str = days_to_due(t["due"], today)
            due_part = f"｜{t['due'].strftime('%m-%d')}｜{due_str}" if t["due"] else f"｜{due_str}"
            pri_part = f"｜{t['priority']}" if t["priority"] else ""
            lines.append(f"{i}. {t['task']}{due_part}{pri_part}")
        lines.append("")
    if missing_ids:
        lines.append(f"（注：以下 userId 暂无中文姓名，可在 user_map.json 中补充：{', '.join(sorted(missing_ids))}）")
    return "\n".join(lines)


def build_markdown(groups, owners, total, overdue, today, missing_ids):
    title = build_title(total, overdue, today)
    lines = [f"### {title}", ""]
    if total == 0:
        lines.append("本周没有未完成的任务 🎉")
        return "\n".join(lines)
    lines.append(f"本周未完成 **{total}** 条，逾期 **{overdue}** 条。")
    lines.append("")
    for owner in owners:
        tasks = groups[owner]
        lines.append(f"**{owner}（{len(tasks)} 条）**")
        for i, t in enumerate(tasks, 1):
            _, due_str = days_to_due(t["due"], today)
            marker = "⚠️ " if "已逾期" in due_str else ("🔴 " if "今天" in due_str else "")
            lines.append(f"{i}. {marker}{t['task']}（{due_str}）")
        lines.append("")
    lines.append("> 由钉钉 AI 表格自动整理")
    return "\n".join(lines)


def collect_missing_ids(records):
    """收集责任人字段中未提供 userName 的 userId。"""
    missing = set()
    for r in records:
        cells = r.get("cells", {})
        for u in cells.get(FIELD_OWNER) or []:
            if u.get("userId") and not u.get("userName"):
                missing.add(str(u["userId"]))
    return missing


def main():
    setup_utf8_console()
    ap = argparse.ArgumentParser(description="钉钉团队任务表每周简报")
    ap.add_argument("--dry-run", action="store_true", help="只预览，不发消息")
    ap.add_argument("--build-user-map", action="store_true", help="生成 user_map.json 模板并退出")
    ap.add_argument("--config", default=None, help="配置文件路径")
    args = ap.parse_args()

    cfg = load_config(args.config) if args.config else load_config()
    user_map = load_user_map()
    today = date.today()

    print(f"=== 钉钉团队任务周报 {today.strftime('%Y-%m-%d')} ===")
    if args.dry_run:
        print("[模式] dry-run（仅预览，不发消息）")

    print("[1/2] 拉取 AI 表格未完成任务 ...")
    client = McpClient(cfg["table_mcp_url"])
    records = fetch_incomplete_records(client, cfg["base_id"], cfg["table_id"])
    print(f"      命中 {len(records)} 条")

    missing_ids = {uid for uid in collect_missing_ids(records) if uid not in user_map}
    if args.build_user_map:
        new_map = {uid: "" for uid in missing_ids}
        new_map.update(user_map)
        save_user_map(new_map)
        print(f"已生成/更新 {USER_MAP_PATH}，共 {len(new_map)} 个 userId 待补充姓名。")
        return 0

    groups, owners, total, overdue = build_report(records, today, user_map)
    title = build_title(total, overdue, today)
    body = build_plain_body(groups, owners, total, overdue, today, missing_ids)
    print("\n----- 周报预览 -----")
    print(body)
    print("--------------------\n")

    if args.dry_run:
        print("[dry-run] 未发送。")
        if missing_ids:
            print(f"\n[提示] 有 {len(missing_ids)} 个 userId 没有中文姓名：")
            print(", ".join(sorted(missing_ids)))
            print("运行 `python dingtalk_task_weekly.py --build-user-map` 可生成映射模板。")
        return 0

    print("[2/2] 发送到钉钉机器人 ...")
    md = build_markdown(groups, owners, total, overdue, today, missing_ids)
    result = send_via_robot(cfg["robot_webhook"], cfg["robot_secret"], title, md)
    print(f"      发送成功: {result}")
    print(f"\nSUMMARY: {total} 条未完成任务，周报已发送到钉钉机器人。")
    if missing_ids:
        print(f"[提示] 有 {len(missing_ids)} 个 userId 没有中文姓名，建议补充 user_map.json。")
    return 0


if __name__ == "__main__":
    import sys
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
