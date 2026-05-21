#!/usr/bin/env python3
"""
OSSInsight Public API client.

Docs:
  https://ossinsight.io/docs/api/
Base URL:
  https://api.ossinsight.io/v1
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Iterable

import requests


@dataclass(frozen=True)
class TimePoint:
    date: str  # YYYY-MM-DD
    value: float


class OSSInsightClient:
    def __init__(self, base_url: str = "https://api.ossinsight.io/v1", timeout_s: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s
        self._session = requests.Session()
        self._session.headers.update({"Accept": "application/json", "User-Agent": "OpenViking-Insights/1.0"})

    def _get(self, path: str, params: dict) -> dict:
        url = f"{self.base_url}{path}"
        resp = self._session.get(url, params=params, timeout=self.timeout_s)
        resp.raise_for_status()
        return resp.json()

    def _history(self, owner: str, repo: str, metric: str, start: dt.date, end: dt.date) -> list[TimePoint]:
        payload = self._get(
            f"/repos/{owner}/{repo}/{metric}/history/",
            params={"per": "day", "from": start.isoformat(), "to": end.isoformat()},
        )
        rows = payload.get("data", {}).get("rows", [])
        # payload columns use metric name as key, e.g. "stargazers"
        metric_key = {
            "stargazers": "stargazers",
            "pull_request_creators": "pull_request_creators",
            "issue_creators": "issue_creators",
        }[metric]

        points: list[TimePoint] = []
        for row in rows:
            points.append(TimePoint(date=row["date"], value=float(row[metric_key])))
        points.sort(key=lambda p: p.date)
        return points

    def stargazers_history(self, owner: str, repo: str, start: dt.date, end: dt.date) -> list[TimePoint]:
        return self._history(owner, repo, "stargazers", start, end)

    def pr_creators_history(self, owner: str, repo: str, start: dt.date, end: dt.date) -> list[TimePoint]:
        return self._history(owner, repo, "pull_request_creators", start, end)

    def issue_creators_history(self, owner: str, repo: str, start: dt.date, end: dt.date) -> list[TimePoint]:
        return self._history(owner, repo, "issue_creators", start, end)


def to_daily_deltas(points: Iterable[TimePoint]) -> dict[str, float]:
    """Convert cumulative series into daily deltas keyed by date."""
    points = list(points)
    points.sort(key=lambda p: p.date)
    deltas: dict[str, float] = {}
    prev: TimePoint | None = None
    for p in points:
        if prev is None:
            deltas[p.date] = 0.0
        else:
            deltas[p.date] = round(p.value - prev.value, 4)
        prev = p
    return deltas

