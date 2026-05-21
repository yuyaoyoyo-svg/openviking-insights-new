#!/usr/bin/env python3
"""
同步 OSSInsight 趋势数据到飞书表：生态位趋势(日)

数据来源：OSSInsight Public API
  https://ossinsight.io/docs/api/
"""

import datetime as dt
import json
import logging
import os
import subprocess
import time
from pathlib import Path

from env_utils import load_env_file
from lark_cli_utils import ensure_lark_cli_ready, get_lark_identity, lark_base_cmd
from ossinsight_client import OSSInsightClient, to_daily_deltas

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAX_BATCH_CREATE_ROWS = 200


def load_projects() -> list[dict]:
    config = json.loads((Path(__file__).resolve().parent.parent / "config" / "projects.json").read_text(encoding="utf-8"))
    return config["projects"]


def list_table_field_names(base_token: str, table_id: str) -> set[str]:
    cmd = lark_base_cmd("+field-list", base_token=base_token, table_id=table_id)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        return set()
    payload = json.loads(result.stdout)
    items = payload.get("data", {}).get("items") or payload.get("data", {}).get("fields") or []
    return {it.get("field_name") or it.get("name") for it in items if (it.get("field_name") or it.get("name"))}


def list_existing_record_ids(base_token: str, table_id: str) -> dict:
    """key = 仓库全名|日期(yyyy-MM-dd) -> record_id"""
    mapping: dict[str, str] = {}
    offset = 0
    limit = 200
    while True:
        cmd = lark_base_cmd("+record-list", base_token=base_token, table_id=table_id)
        cmd.extend(["--limit", str(limit), "--offset", str(offset)])
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            logger.warning("读取趋势表记录失败: %s", result.stderr.strip() or result.stdout.strip())
            return mapping
        payload = json.loads(result.stdout).get("data", {})
        fields = payload.get("fields", [])
        rows = payload.get("data", [])
        record_ids = payload.get("record_id_list", [])

        if not rows:
            break

        try:
            full_idx = fields.index("仓库全名")
            date_idx = fields.index("日期")
        except ValueError:
            return mapping

        for rec_id, row in zip(record_ids, rows):
            full = row[full_idx]
            date_value = row[date_idx]
            date_str = str(date_value).split(" ")[0].split("T")[0]
            mapping[f"{full}|{date_str}"] = rec_id

        if len(rows) < limit:
            break
        offset += limit
    return mapping


def upsert_rows(base_token: str, table_id: str, records: list[dict]) -> bool:
    """Upsert by 仓库全名+日期"""
    existing = list_existing_record_ids(base_token, table_id)
    table_fields = list_table_field_names(base_token, table_id)
    if table_fields:
        for record in records:
            record["fields"] = {k: v for k, v in record["fields"].items() if k in table_fields}

    to_create = []
    to_update = []
    for record in records:
        fields = record["fields"]
        key = f"{fields.get('仓库全名','')}|{str(fields.get('日期','')).split(' ')[0].split('T')[0]}"
        rec_id = existing.get(key)
        if rec_id:
            to_update.append((rec_id, fields))
        else:
            to_create.append(record)

    ok = True
    if to_create:
        field_names = list(to_create[0]["fields"].keys())

        for start in range(0, len(to_create), MAX_BATCH_CREATE_ROWS):
            chunk = to_create[start : start + MAX_BATCH_CREATE_ROWS]
            payload = {
                "fields": field_names,
                "rows": [[r["fields"].get(k, "") for k in field_names] for r in chunk],
            }
            cmd = lark_base_cmd("+record-batch-create", base_token=base_token, table_id=table_id)
            cmd.extend(["--json", json.dumps(payload, ensure_ascii=False)])
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if res.returncode != 0:
                logger.error(
                    "新增趋势记录失败(%s-%s/%s): %s",
                    start + 1,
                    start + len(chunk),
                    len(to_create),
                    res.stderr.strip() or res.stdout.strip(),
                )
                ok = False
                # If create fails, don't spam requests.
                time.sleep(2)
            else:
                logger.info(
                    "✓ 已新增趋势记录 %s-%s/%s",
                    start + 1,
                    start + len(chunk),
                    len(to_create),
                )

    for rec_id, patch in to_update:
        cmd = lark_base_cmd("+record-batch-update", base_token=base_token, table_id=table_id)
        cmd.extend(["--json", json.dumps({"record_id_list": [rec_id], "patch": patch}, ensure_ascii=False)])
        # Retry a bit on rate-limit errors to make daily job stable.
        for attempt in (0, 1, 2):
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if res.returncode == 0:
                break
            msg = res.stderr.strip() or res.stdout.strip()
            if "limited" in msg or "800004135" in msg:
                time.sleep(1 + attempt)
                continue
            logger.error("更新趋势记录失败(%s): %s", rec_id, msg)
            ok = False
            break
        else:
            logger.error("更新趋势记录失败(%s): rate limited", rec_id)
            ok = False
    if to_update:
        logger.info("✓ 已更新 %s 条趋势记录", len(to_update))
    return ok


def main():
    load_env_file()
    base_token = os.getenv("LARK_BASE_TOKEN", "")
    table_id = os.getenv("LARK_TRENDS_TABLE_ID", "")
    if not base_token or not table_id:
        logger.error("缺少飞书配置：LARK_BASE_TOKEN / LARK_TRENDS_TABLE_ID")
        return 1

    if not ensure_lark_cli_ready():
        logger.error("lark-cli 不可用或当前身份(%s)未就绪，跳过趋势同步", get_lark_identity())
        return 2

    # 增量策略：每日跑只需要最近 30 天（既能 backfill 也能抗偶发失败）
    end = dt.date.today()
    start = end - dt.timedelta(days=30)

    client = OSSInsightClient()
    projects = load_projects()

    records: list[dict] = []
    for project in projects:
        owner = project["owner"]
        repo = project["repo"]
        full_name = f"{owner}/{repo}"
        tier = project.get("ecosystem_tier", "更广义Agent生态位")

        stars_series = client.stargazers_history(owner, repo, start, end)
        pr_series = client.pr_creators_history(owner, repo, start, end)
        issue_series = client.issue_creators_history(owner, repo, start, end)

        stars_delta = to_daily_deltas(stars_series)
        pr_delta = to_daily_deltas(pr_series)
        issue_delta = to_daily_deltas(issue_series)

        # merge on date union
        dates = sorted({p.date for p in stars_series} | {p.date for p in pr_series} | {p.date for p in issue_series})
        stars_map = {p.date: p.value for p in stars_series}
        pr_map = {p.date: p.value for p in pr_series}
        issue_map = {p.date: p.value for p in issue_series}

        for day in dates:
            records.append(
                {
                    "fields": {
                        "日期": day,
                        "仓库全名": full_name,
                        "生态位层级": tier,
                        "OSSInsight Stars(累计)": stars_map.get(day, 0),
                        "OSSInsight Stars(日增)": stars_delta.get(day, 0),
                        "PR Creators(累计)": pr_map.get(day, 0),
                        "PR Creators(日增)": pr_delta.get(day, 0),
                        "Issue Creators(累计)": issue_map.get(day, 0),
                        "Issue Creators(日增)": issue_delta.get(day, 0),
                        "数据源": "OSSInsight Public API",
                    }
                }
            )

    ok = upsert_rows(base_token, table_id, records)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
