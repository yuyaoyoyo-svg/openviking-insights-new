#!/usr/bin/env python3
"""
Use GitHub stargazer timestamps to repair recent historical star totals/deltas.

This script is designed for recent backfill windows where local snapshots exist
but `stars` / `stars_daily_delta` are inaccurate because the snapshots were
generated after the fact.

Important limitation:
- GitHub's stargazers API only returns current stargazers with `starred_at`.
- If a user starred on day D and later unstarred, that event is no longer
  available from the API, so older historical totals may still be understated.
- For recent gaps this is usually acceptable and is the best public GitHub
  source available without original daily raw snapshots.

Usage examples:
  python3 src/fix_star_history_from_stargazers.py 2026-05-10 2026-05-12 \
    --repo volcengine/OpenViking --repo NevaMind-AI/memU

  python3 src/fix_star_history_from_stargazers.py 2026-05-10 2026-05-12 \
    --repo volcengine/OpenViking --repo NevaMind-AI/memU --sync-lark --dedupe
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import subprocess
import sys
import time
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

import requests

from env_utils import load_env_file


logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
TZ_CST = timezone(timedelta(hours=8))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("start", help="inclusive YYYY-MM-DD")
    parser.add_argument("end", help="inclusive YYYY-MM-DD")
    parser.add_argument(
        "--repo",
        action="append",
        dest="repos",
        required=True,
        help="full repo name, repeatable, e.g. volcengine/OpenViking",
    )
    parser.add_argument("--sync-lark", action="store_true", help="upsert updated snapshot files to Lark")
    parser.add_argument("--dedupe", action="store_true", help="remove duplicate Lark records after sync")
    return parser.parse_args()


def parse_day(value: str) -> date:
    return date.fromisoformat(value)


def iter_days(start: date, end: date) -> Iterable[date]:
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def format_ratio_percent(numerator: float, denominator: float, decimals: int = 2) -> str:
    if denominator <= 0:
        return "N/A"
    return f"{(numerator / denominator) * 100:.{decimals}f}%"


def recompute_star_derived_fields(project: dict) -> None:
    forks = float(project.get("forks", 0) or 0)
    stars = float(project.get("stars", 0) or 0)
    stars_daily = float(project.get("stars_daily_delta", 0) or 0)
    forks_daily = float(project.get("forks_daily_delta", 0) or 0)
    contributors_daily = float(project.get("contributors_daily_delta", 0) or 0)
    contributors_total = float(project.get("contributors_count", 0) or 0)

    project["external_attraction_index"] = round(math.log1p(stars) + 2 * math.log1p(forks), 4)
    project["recent_growth_momentum"] = round(stars_daily + 2.0 * forks_daily + 3.0 * contributors_daily, 2)
    if stars_daily < 10:
        project["contributor_growth_star_growth_ratio"] = "N/A"
    else:
        project["contributor_growth_star_growth_ratio"] = format_ratio_percent(contributors_daily, stars_daily)
    project["contributors_to_star_total_ratio"] = format_ratio_percent(contributors_total, stars, decimals=4)


class GitHubStargazerHistory:
    base_url = "https://api.github.com"

    def __init__(self, token: str):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "OpenViking-Insights/1.0",
            }
        )

    def _request_json(self, url: str, params: dict | None = None, accept: str | None = None) -> list | dict:
        headers = {}
        if accept:
            headers["Accept"] = accept

        for attempt in range(3):
            try:
                response = self.session.get(url, params=params, headers=headers, timeout=60)
                if response.status_code == 200:
                    return response.json()

                if response.status_code == 403 and "X-RateLimit-Reset" in response.headers:
                    reset_ts = int(response.headers["X-RateLimit-Reset"])
                    wait_s = max(1, reset_ts - int(time.time()) + 1)
                    logger.warning("GitHub rate limited, waiting %ss", wait_s)
                    time.sleep(wait_s)
                    continue

                response.raise_for_status()
            except requests.RequestException as exc:
                if attempt == 2:
                    raise RuntimeError(f"GitHub request failed: {url} | {exc}") from exc
                time.sleep(2 * (attempt + 1))

        raise RuntimeError(f"GitHub request failed after retries: {url}")

    def get_current_star_count(self, owner: str, repo: str) -> int:
        payload = self._request_json(f"{self.base_url}/repos/{owner}/{repo}")
        return int(payload.get("stargazers_count", 0))

    def get_recent_starred_days(self, owner: str, repo: str, start: date, tzinfo=TZ_CST) -> list[str]:
        current_total = self.get_current_star_count(owner, repo)
        if current_total <= 0:
            return []

        per_page = 100
        last_page = max((current_total + per_page - 1) // per_page, 1)
        starred_days: list[str] = []

        for page in range(last_page, 0, -1):
            payload = self._request_json(
                f"{self.base_url}/repos/{owner}/{repo}/stargazers",
                params={"per_page": per_page, "page": page},
                accept="application/vnd.github.star+json",
            )
            if not payload:
                break

            page_days = []
            for item in payload:
                starred_at = item.get("starred_at")
                if not starred_at:
                    continue
                ts = datetime.strptime(starred_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).astimezone(tzinfo)
                page_days.append(ts.date().isoformat())

            starred_days.extend(page_days)

            earliest_day = min(page_days) if page_days else None
            if earliest_day and earliest_day < start.isoformat():
                break

        return starred_days

    def compute_recent_daily_stats(self, owner: str, repo: str, start: date, end: date) -> dict[str, dict[str, int]]:
        current_total = self.get_current_star_count(owner, repo)
        starred_days = self.get_recent_starred_days(owner, repo, start)
        counts = Counter(starred_days)
        result: dict[str, dict[str, int]] = {}

        for day in iter_days(start, end):
            day_str = day.isoformat()
            future_events = sum(1 for d in starred_days if d > day_str)
            result[day_str] = {
                "stars": current_total - future_events,
                "stars_daily_delta": counts.get(day_str, 0),
            }
        return result


def update_snapshot_file(file_path: Path, repo_updates: dict[str, dict[str, int]]) -> bool:
    payload = json.loads(file_path.read_text(encoding="utf-8"))
    changed = False

    for project in payload.get("projects", []):
        full_name = project.get("full_name")
        if full_name not in repo_updates:
            continue

        patch = repo_updates[full_name]
        before = (project.get("stars"), project.get("stars_daily_delta"))
        after = (patch["stars"], float(patch["stars_daily_delta"]))
        if before == after:
            continue

        project["stars"] = patch["stars"]
        project["stars_daily_delta"] = float(patch["stars_daily_delta"])
        recompute_star_derived_fields(project)
        changed = True

    if changed:
        file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return changed


def run_python_script(args: list[str]) -> None:
    result = subprocess.run([sys.executable, *args], cwd=ROOT, check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> int:
    args = parse_args()
    start = parse_day(args.start)
    end = parse_day(args.end)
    if end < start:
        raise SystemExit("end must be >= start")

    load_env_file()
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if not token:
        raise SystemExit("missing GITHUB_TOKEN")

    client = GitHubStargazerHistory(token)
    updates_by_day: dict[str, dict[str, dict[str, int]]] = {day.isoformat(): {} for day in iter_days(start, end)}

    for full_name in args.repos:
        if "/" not in full_name:
            raise SystemExit(f"invalid repo: {full_name}")
        owner, repo = full_name.split("/", 1)
        logger.info("fetching exact stargazer history for %s", full_name)
        daily_stats = client.compute_recent_daily_stats(owner, repo, start, end)
        for day_str, stats in daily_stats.items():
            updates_by_day[day_str][full_name] = stats
            logger.info("%s | %s | stars=%s delta=%s", day_str, full_name, stats["stars"], stats["stars_daily_delta"])

    changed_files: list[Path] = []
    for day in iter_days(start, end):
        file_path = DATA_DIR / f"insights_{day.isoformat()}.json"
        if not file_path.exists():
            logger.warning("skip missing snapshot: %s", file_path)
            continue
        changed = update_snapshot_file(file_path, updates_by_day[day.isoformat()])
        if changed:
            changed_files.append(file_path)
            logger.info("updated %s", file_path.name)
        else:
            logger.info("no changes in %s", file_path.name)

    if args.sync_lark:
        for path in changed_files:
            run_python_script(["src/backfill_snapshot_day.py", str(path)])

    if args.dedupe:
        run_python_script(
            ["src/dedupe_snapshot_records.py", "--start", start.isoformat(), "--end", end.isoformat(), "--apply"]
        )

    if not changed_files:
        logger.info("no snapshot files changed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
