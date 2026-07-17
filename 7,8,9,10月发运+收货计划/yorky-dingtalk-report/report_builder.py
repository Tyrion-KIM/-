from __future__ import annotations
from dataclasses import dataclass

PROBLEM_KEYWORDS = ("问题", "异常")


@dataclass
class ReportData:
    title: str
    markdown: str
    in_transit_count: int
    is_empty: bool


class ReportBuilder:
    def __init__(self, exclude_track_status: list[int], exclude_delivery_status: list[str],
                 long_tail_threshold: int = 50, today: str = ""):
        self.exclude_track_status = set(exclude_track_status)
        self.exclude_delivery_status = set(exclude_delivery_status)
        self.long_tail_threshold = long_tail_threshold
        self.today = today

    def _is_problem(self, r: dict) -> bool:
        if r.get("deliveryStatus") == "W":
            return True
        text = f"{r.get('trackStatusText', '')} {r.get('trackDesc', '')}"
        return any(k in text for k in PROBLEM_KEYWORDS)

    def _is_excluded(self, r: dict) -> bool:
        if r.get("trackStatus") in self.exclude_track_status:
            return True
        if r.get("deliveryStatus") in self.exclude_delivery_status:
            return True
        return False

    def _truncate(self, s: str, n: int = 40) -> str:
        s = (s or "").replace("\n", " ").strip()
        return s if len(s) <= n else s[:n] + "…"

    def build(self, records: list[dict]) -> ReportData:
        in_transit = [r for r in records if not self._is_excluded(r)]
        title = f"📦 每日转运状态报表（{self.today}）"

        if not in_transit:
            return ReportData(title=title, markdown="✅ 今日全部已送达，无在途单",
                              in_transit_count=0, is_empty=True)

        problem = [r for r in in_transit if self._is_problem(r)]
        normal = [r for r in in_transit if not self._is_problem(r)]

        # 普通组按 trackStatusText 聚合
        groups: dict[str, list[dict]] = {}
        for r in normal:
            key = r.get("trackStatusText") or "未知"
            groups.setdefault(key, []).append(r)

        # 超长只发概要
        if len(in_transit) > self.long_tail_threshold:
            md_parts = [f"> 共 **{len(in_transit)}** 单在途"]
            if problem:
                md_parts.append(f"\n\n**🔴 问题件（{len(problem)}）**")
            for gname, items in groups.items():
                md_parts.append(f"\n\n**{gname}（{len(items)}）**")
            md = "".join(md_parts)
            return ReportData(title=title, markdown=md,
                              in_transit_count=len(in_transit), is_empty=False)

        def table(items: list[dict]) -> str:
            rows = ["| 客户单号 | 渠道 | 国家 | 转运状态 | 最新轨迹 | 时间 |",
                    "|---|---|---|---|---|---|"]
            for r in items:
                rows.append("| {} | {} | {} | {} | {} | {} |".format(
                    r.get("userNo", ""), r.get("serviceName", ""),
                    r.get("countryText", ""), r.get("trackStatusText", ""),
                    self._truncate(r.get("trackDesc", "")), r.get("trackTime", "")))
            return "\n".join(rows)

        md_parts = [f"> 共 **{len(in_transit)}** 单在途"]
        if problem:
            md_parts.append(f"\n\n**🔴 问题件（{len(problem)}）**\n\n" + table(problem))
        for gname, items in groups.items():
            md_parts.append(f"\n\n**{gname}（{len(items)}）**\n\n" + table(items))

        return ReportData(title=title, markdown="".join(md_parts),
                          in_transit_count=len(in_transit), is_empty=False)
