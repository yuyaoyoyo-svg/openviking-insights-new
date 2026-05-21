#!/usr/bin/env python3
"""
De-duplicate snapshot table records by `仓库全名 + 日期`.

Selection rule:
- Prefer the record that best matches local `data/insights_YYYY-MM-DD.json`
- If no local snapshot exists for that day, keep the last record in the group

Usage:
  python3 src/dedupe_snapshot_records.py
  python3 src/dedupe_snapshot_records.py --apply
  python3 src/dedupe_snapshot_records.py --start 2026-04-30 --end 2026-05-03 --apply
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from env_utils import load_env_file


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

FIELD_MAP = {
    "Stars": "stars",
    "Forks": "forks",
    "Watchers": "watchers",
    "Open Issues": "open_issues",
    "Open PRs": "open_prs",
    "Contributors": "contributors_count",
    "Stars日增量": "stars_daily_delta",
    "Forks日增量": "forks_daily_delta",
    "Watchers日增量": "watchers_daily_delta",
    "Open Issues日增量": "open_issues_daily_delta",
    "Open PRs日增量": "open_prs_daily_delta",
    "Contributors日增量": "contributors_daily_delta",
    "对比基准日期": "baseline_date",
    "采集间隔天数": "days_since_last_snapshot",
}


@dataclass
class Record:
    record_id: str
    fields: dict[str, object]


def ensure_lark_cli_ready() -> bool:
    status = subprocess.run(
        ["lark-cli", "auth", "status"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return status.returncode == 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", help="inclusive YYYY-MM-DD")
    parser.add_argument("--end", help="inclusive YYYY-MM-DD")
    parser.add_argument("--apply", action="store_true", help="delete duplicate records")
    return parser.parse_args()


def day_in_range(day_str: str, start: date | None, end: date | None) -> bool:
    try:
        current = date.fromisoformat(day_str)
    except ValueError:
        return False
    if start and current < start:
        return False
    if end and current > end:
        return False
    return True


def iter_records(base_token: str, table_id: str):
    offset = 0
    limit = 200
    while True:
        cmd = [
            "lark-cli",
            "base",
            "+record-list",
            "--base-token",
            base_token,
            "--table-id",
            table_id,
            "--as",
            "user",
            "--limit",
            str(limit),
            "--offset",
            str(offset),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip())

        payload = json.loads(result.stdout).get("data", {})
        field_names = payload.get("fields", [])
        rows = payload.get("data", [])
        record_ids = payload.get("record_id_list", [])
        if not rows:
            break

        for record_id, row in zip(record_ids, rows):
            yield Record(record_id=record_id, fields=dict(zip(field_names, row)))

        if len(rows) < limit:
            break
        offset += limit


def load_expected_project(day_str: str, repo: str) -> dict | None:
    path = DATA_DIR / f"insights_{day_str}.json"
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return next((project for project in payload.get("projects", []) if project.get("full_name") == repo), None)


def normalize_value(value: object) -> object:
    if isinstance(value, list):
        return tuple(value)
    if isinstance(value, str):
        return value.split(" ")[0].split("T")[0]
    return value


def values_match(left: object, right: object) -> bool:
    left = normalize_value(left)
    right = normalize_value(right)

    try:
        return abs(float(left) - float(right)) < 1e-6
    except (TypeError, ValueError):
        return left == right


def score_record(record: Record, expected: dict | None) -> int:
    if expected is None:
        return -1

    score = 0
    for lark_field, snapshot_field in FIELD_MAP.items():
        if lark_field not in record.fields:
            continue
        if values_match(record.fields.get(lark_field), expected.get(snapshot_field)):
            score += 1
    return score


def delete_record(base_token: str, table_id: str, record_id: str) -> None:
    cmd = [
        "lark-cli",
        "base",
        "+record-delete",
        "--base-token",
        base_token,
        "--table-id",
        table_id,
        "--record-id",
        record_id,
        "--as",
        "user",
        "--yes",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())


def main() -> int:
    args = parse_args()
    start = date.fromisoformat(args.start) if args.start else None
    end = date.fromisoformat(args.end) if args.end else None

    load_env_file()
    base_token = os.getenv("LARK_BASE_TOKEN", "")
    table_id = os.getenv("LARK_TABLE_ID", "")
    if not base_token or not table_id:
        print("缺少飞书配置：LARK_BASE_TOKEN / LARK_TABLE_ID")
        return 2

    if not ensure_lark_cli_ready():
        print("lark-cli 未登录")
        return 2

    grouped: dict[tuple[str, str], list[Record]] = defaultdict(list)
    for record in iter_records(base_token, table_id):
        repo = str(record.fields.get("仓库全名", ""))
        day_str = str(record.fields.get("日期", "")).split(" ")[0].split("T")[0]
        if not repo or not day_in_range(day_str, start, end):
            continue
        grouped[(repo, day_str)].append(record)

    duplicates = {key: records for key, records in grouped.items() if len(records) > 1}
    if not duplicates:
        print("未发现重复记录")
        return 0

    deletions: list[tuple[str, str, str]] = []
    for (repo, day_str), records in sorted(duplicates.items(), key=lambda item: (item[0][1], item[0][0])):
        expected = load_expected_project(day_str, repo)
        ranked = [(score_record(record, expected), index, record) for index, record in enumerate(records)]
        ranked.sort(key=lambda item: (item[0], item[1]))
        keep = ranked[-1][2]
        print(f"{day_str} | {repo} | keep={keep.record_id} | total={len(records)}")
        for score, _, record in ranked:
            print(
                "  ",
                record.record_id,
                "score=",
                score,
                "stars=",
                record.fields.get("Stars"),
                "delta=",
                record.fields.get("Stars日增量"),
                "baseline=",
                record.fields.get("对比基准日期"),
            )
            if record.record_id != keep.record_id:
                deletions.append((day_str, repo, record.record_id))

    print(f"待删除记录数: {len(deletions)}")
    if not args.apply:
        print("当前为 dry-run；加 --apply 执行删除")
        return 1 if deletions else 0

    for day_str, repo, record_id in deletions:
        delete_record(base_token, table_id, record_id)
        print(f"deleted: {day_str} | {repo} | {record_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
