#!/usr/bin/env python3
"""
按指定快照文件回填快照表中的某一天记录。
用途：
- 修正历史日期的口径变更（例如字段改名、计算方式更新）
- 修正历史日期的生态位标签
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from env_utils import load_env_file

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from sync_to_lark_api import batch_upsert_records, get_lark_config, list_table_field_names


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python3 src/backfill_snapshot_day.py data/insights_YYYY-MM-DD.json")
        return 2

    load_env_file()
    config = get_lark_config()
    if not config:
        return 1

    insights_file = Path(sys.argv[1])
    if not insights_file.is_absolute():
        insights_file = (ROOT / insights_file).resolve()
    if not insights_file.exists():
        print(f"file not found: {insights_file}")
        return 2

    with open(insights_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    date_str = insights_file.stem.replace("insights_", "")
    records = []
    for project in data["projects"]:
        records.append(
            {
                "fields": {
                    "仓库名称": project.get("name", ""),
                    "仓库全名": project.get("full_name", f"{project.get('owner', '')}/{project.get('repo', '')}"),
                    "生态位层级": project.get("ecosystem_tier", "OpenViking同生态位"),
                    "项目类型": "OpenViking" if project.get("type") == "self" else "Peer",
                    "日期": date_str,
                    "Stars": project.get("stars", 0),
                    "Forks": project.get("forks", 0),
                    "Watchers": project.get("watchers", 0),
                    "Open Issues": project.get("open_issues", 0),
                    "Open PRs": project.get("open_prs", 0),
                    "Contributors": project.get("contributors_count", 0),
                    "社区活力评分": project.get("vitality_score", 0),
                    "外部影响力评分": project.get("influence_score", 0),
                    "综合健康度": project.get("overall_health_score", 0),
                    "社区互动总量": project.get("community_engagement_total", 0),
                    "外部吸引力指数(log+加权)": project.get("external_attraction_index", 0),
                    "语言": project.get("language", ""),
                    "最后推送时间": project.get("pushed_at", ""),
                    "GitHub链接": project.get("github_url", ""),
                    "对比基准日期": project.get("baseline_date", ""),
                    "采集间隔天数": project.get("days_since_last_snapshot", 0),
                    "Stars日增量": project.get("stars_daily_delta", 0),
                    "Forks日增量": project.get("forks_daily_delta", 0),
                    "Watchers日增量": project.get("watchers_daily_delta", 0),
                    "Open Issues日增量": project.get("open_issues_daily_delta", 0),
                    "Open PRs日增量": project.get("open_prs_daily_delta", 0),
                    "Contributors日增量": project.get("contributors_daily_delta", 0),
                    "近期增长动力": project.get("recent_growth_momentum", 0),
                    "访客→Star转化率": project.get("visitor_to_star_conversion", "待补traffic"),
                    "访客→克隆者转化率": project.get("visitor_to_cloner_conversion", "待补traffic"),
                    "贡献者增长/Star增长比": project.get("contributor_growth_star_growth_ratio", "N/A"),
                    "贡献者总数/Star总数": project.get("contributors_to_star_total_ratio", "N/A"),
                }
            }
        )

    table_fields = list_table_field_names(config["base_token"], config["table_id"])
    if table_fields:
        for record in records:
            record["fields"] = {k: v for k, v in record["fields"].items() if k in table_fields}

    ok = batch_upsert_records(config["base_token"], config["table_id"], records)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
