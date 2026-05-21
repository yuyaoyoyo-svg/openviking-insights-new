#!/usr/bin/env python3
"""
OpenViking traffic / funnel helper functions.
"""

from __future__ import annotations

import json
from pathlib import Path


def load_traffic_snapshot(snapshot_path: str | Path) -> dict:
    path = Path(snapshot_path)
    return json.loads(path.read_text(encoding="utf-8"))


def build_top_summary(items: list[dict], key_name: str, top_n: int = 5) -> str:
    parts = []
    for item in items[:top_n]:
        label = item.get(key_name, "")
        count = item.get("count", 0)
        uniques = item.get("uniques", 0)
        parts.append(f"{label}({count}/{uniques})")
    return " | ".join(parts)


def build_daily_traffic_rows(snapshot: dict) -> list[dict]:
    views_by_day = {
        item["timestamp"][:10]: {
            "浏览量": item.get("count", 0),
            "访客数": item.get("uniques", 0),
        }
        for item in snapshot.get("views", {}).get("views", [])
    }
    clones_by_day = {
        item["timestamp"][:10]: {
            "克隆次数": item.get("count", 0),
            "克隆者数": item.get("uniques", 0),
        }
        for item in snapshot.get("clones", {}).get("clones", [])
    }

    top_paths = build_top_summary(snapshot.get("popular_paths", []), "path")
    top_referrers = build_top_summary(snapshot.get("referrers", []), "referrer")

    days = sorted(set(views_by_day) | set(clones_by_day))
    rows = []
    for day in days:
        view = views_by_day.get(day, {})
        clone = clones_by_day.get(day, {})
        rows.append(
            {
                "日期": day,
                "仓库全名": snapshot.get("repo", "volcengine/OpenViking"),
                "浏览量": view.get("浏览量", 0),
                "访客数": view.get("访客数", 0),
                "克隆次数": clone.get("克隆次数", 0),
                "克隆者数": clone.get("克隆者数", 0),
                "Top Referrers 摘要": top_referrers,
                "Top Paths 摘要": top_paths,
                "总浏览量(14d)": snapshot.get("views", {}).get("count", 0),
                "总访客数(14d)": snapshot.get("views", {}).get("uniques", 0),
                "总克隆次数(14d)": snapshot.get("clones", {}).get("count", 0),
                "总克隆者数(14d)": snapshot.get("clones", {}).get("uniques", 0),
                "数据新鲜度说明": "GitHub traffic 通常按 T+1 更新，抓取日看到的最新数据通常对应前一天",
                "数据抓取时间": snapshot.get("pulled_at", ""),
                "数据来源": snapshot.get("source", "traffic_snapshot.json"),
            }
        )
    return rows


def load_latest_insights_by_date(data_dir: Path) -> dict[str, dict]:
    mapping: dict[str, dict] = {}
    for path in sorted(data_dir.glob("insights_*.json")):
        day = path.stem.replace("insights_", "")
        payload = json.loads(path.read_text(encoding="utf-8"))
        for project in payload.get("projects", []):
            if project.get("full_name") == "volcengine/OpenViking":
                mapping[day] = project
                break
    return mapping


def build_funnel_rows(snapshot: dict, insights_by_date: dict[str, dict]) -> list[dict]:
    rows = []
    traffic_rows = build_daily_traffic_rows(snapshot)

    for traffic in traffic_rows:
        day = traffic["日期"]
        insights = insights_by_date.get(day, {})

        visitors = float(traffic.get("访客数", 0) or 0)
        cloners = float(traffic.get("克隆者数", 0) or 0)
        stars_daily = insights.get("stars_daily_delta", "")
        contributors_daily = insights.get("contributors_daily_delta", "")
        contributors_total = insights.get("contributors_count", "")
        stars_total = insights.get("stars", "")

        if stars_daily == "":
            visitor_to_star = "N/A"
        elif visitors > 0:
            visitor_to_star = f"{(float(stars_daily) / visitors) * 100:.2f}%"
        else:
            visitor_to_star = "N/A"

        visitor_to_cloner = f"{(cloners / visitors) * 100:.2f}%" if visitors > 0 else "N/A"

        if stars_daily == "" or float(stars_daily or 0) < 10:
            growth_ratio = "N/A"
        else:
            growth_ratio = f"{(float(contributors_daily or 0) / float(stars_daily)) * 100:.2f}%"

        if stars_total:
            total_ratio = f"{(float(contributors_total or 0) / float(stars_total)) * 100:.4f}%"
        else:
            total_ratio = "N/A"

        rows.append(
            {
                "日期": day,
                "仓库全名": snapshot.get("repo", "volcengine/OpenViking"),
                "访客数": traffic.get("访客数", 0),
                "浏览量": traffic.get("浏览量", 0),
                "克隆者数": traffic.get("克隆者数", 0),
                "克隆次数": traffic.get("克隆次数", 0),
                "Stars日增量": stars_daily if stars_daily != "" else "",
                "Contributors日增量": contributors_daily if contributors_daily != "" else "",
                "贡献者总数": contributors_total if contributors_total != "" else "",
                "Stars总数": stars_total if stars_total != "" else "",
                "访客→Star转化率": visitor_to_star,
                "访客→克隆者转化率": visitor_to_cloner,
                "贡献者增长/Star增长比": growth_ratio,
                "贡献者总数/Star总数": total_ratio,
                "数据新鲜度说明": "GitHub traffic 通常按 T+1 更新，抓取日看到的最新数据通常对应前一天",
                "数据抓取时间": snapshot.get("pulled_at", ""),
                "数据来源": snapshot.get("source", "traffic_snapshot.json"),
            }
        )

    return rows
