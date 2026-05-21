#!/usr/bin/env python3
"""
Check insights snapshots for high-confidence data quality issues.

Usage:
  python3 src/check_snapshot_integrity.py
  python3 src/check_snapshot_integrity.py 2026-05-07
  python3 src/check_snapshot_integrity.py 2026-04-29 2026-05-07
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CONFIG_PATH = ROOT / "config" / "projects.json"


@dataclass(frozen=True)
class Finding:
    level: str
    day: str
    repo: str
    message: str


def load_expected_repos() -> set[str]:
    payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {f"{item['owner']}/{item['repo']}" for item in payload.get("projects", [])}


def parse_day(value: str) -> date:
    return date.fromisoformat(value)


def day_range(start: date, end: date) -> list[date]:
    days: list[date] = []
    current = start
    while current <= end:
        days.append(current)
        current += timedelta(days=1)
    return days


def list_snapshot_days() -> list[date]:
    days: list[date] = []
    for path in DATA_DIR.glob("insights_*.json"):
        try:
            days.append(parse_day(path.stem.replace("insights_", "")))
        except ValueError:
            continue
    return sorted(days)


def resolve_scan_days(argv: list[str]) -> list[date]:
    if len(argv) == 0:
        available = list_snapshot_days()
        if not available:
            raise SystemExit("No insights snapshots found under data/")
        latest = available[-1]
        previous = latest - timedelta(days=1)
        return [previous, latest]
    if len(argv) == 1:
        target = parse_day(argv[0])
        return [target - timedelta(days=1), target]
    if len(argv) == 2:
        start = parse_day(argv[0])
        end = parse_day(argv[1])
        if end < start:
            raise SystemExit("End date must be >= start date")
        return day_range(start, end)
    raise SystemExit("Usage: python3 src/check_snapshot_integrity.py [YYYY-MM-DD] [YYYY-MM-DD]")


def load_snapshot(day: date) -> dict[str, dict] | None:
    path = DATA_DIR / f"insights_{day.isoformat()}.json"
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        project.get("full_name"): project
        for project in payload.get("projects", [])
        if project.get("full_name")
    }


def scan(days: list[date]) -> tuple[list[Finding], dict[str, int]]:
    expected_repos = load_expected_repos()
    findings: list[Finding] = []
    snapshots: dict[str, dict[str, dict] | None] = {}

    for day in days:
        snapshots[day.isoformat()] = load_snapshot(day)

    for day in days:
        day_str = day.isoformat()
        current = snapshots[day_str]
        if current is None:
            findings.append(Finding("error", day_str, "-", "snapshot file is missing"))
            continue

        missing_repos = sorted(expected_repos - set(current))
        unexpected_repos = sorted(set(current) - expected_repos)
        for repo in missing_repos:
            findings.append(Finding("error", day_str, repo, "repo is missing from snapshot"))
        for repo in unexpected_repos:
            findings.append(Finding("warn", day_str, repo, "repo is unexpected (not in config/projects.json)"))

    for index in range(1, len(days)):
        previous_day = days[index - 1]
        current_day = days[index]
        previous = snapshots[previous_day.isoformat()]
        current = snapshots[current_day.isoformat()]
        if previous is None or current is None:
            continue

        for repo, project in current.items():
            if repo not in previous:
                findings.append(
                    Finding(
                        "error",
                        current_day.isoformat(),
                        repo,
                        (
                            "repo exists today but was missing yesterday; "
                            f"stars={project.get('stars')} delta={project.get('stars_daily_delta')}"
                        ),
                    )
                )

            stars = float(project.get("stars", 0) or 0)
            delta = float(project.get("stars_daily_delta", 0) or 0)
            if stars > 0 and abs(delta) / stars >= 0.5:
                findings.append(
                    Finding(
                        "error",
                        current_day.isoformat(),
                        repo,
                        (
                            "daily delta is suspiciously close to total stars; "
                            f"stars={int(stars)} delta={delta} baseline={project.get('baseline_date')}"
                        ),
                    )
                )

    counts = {}
    for day in days:
        snapshot = snapshots[day.isoformat()]
        counts[day.isoformat()] = len(snapshot or {})

    return findings, counts


def main() -> int:
    days = resolve_scan_days(sys.argv[1:])
    findings, counts = scan(days)

    print("Scan days:", ", ".join(day.isoformat() for day in days))
    print("Snapshot counts:")
    for day_str, count in counts.items():
        print(f"  - {day_str}: {count}")

    if not findings:
        print("OK: no high-confidence integrity issues found.")
        return 0

    print("Findings:")
    for finding in findings:
        print(f"  - [{finding.level}] {finding.day} | {finding.repo} | {finding.message}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
