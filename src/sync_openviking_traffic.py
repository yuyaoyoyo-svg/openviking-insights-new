#!/usr/bin/env python3
"""
将 OpenViking traffic snapshot 同步到飞书表 OpenViking Traffic(日)。

用法:
  python3 src/sync_openviking_traffic.py /path/to/traffic_snapshot.json
  python3 src/sync_openviking_traffic.py /path/to/export_dir
  python3 src/sync_openviking_traffic.py   # 自动选择最新导出目录
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

from env_utils import load_env_file
from lark_cli_utils import lark_base_cmd
from openviking_traffic_utils import build_daily_traffic_rows, load_traffic_snapshot

ROOT = Path(__file__).resolve().parent.parent


def resolve_snapshot_path(arg_path: str | None) -> Path:
    if arg_path:
        path = Path(arg_path).expanduser().resolve()
        if path.is_dir():
            return path / "traffic_snapshot.json"
        return path

    candidates = sorted((ROOT / "data" / "github-traffic" / "volcengine_OpenViking").glob("*/traffic_snapshot.json"))
    if not candidates:
        raise FileNotFoundError("未找到本地 traffic_snapshot.json，请先执行 export_github_traffic.sh")
    return max(candidates, key=lambda p: p.stat().st_mtime)


def list_table_field_names(base_token: str, table_id: str) -> set[str]:
    cmd = lark_base_cmd("+field-list", base_token=base_token, table_id=table_id)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        return set()
    payload = json.loads(result.stdout)
    items = payload.get("data", {}).get("items") or payload.get("data", {}).get("fields") or []
    return {it.get("field_name") or it.get("name") for it in items if (it.get("field_name") or it.get("name"))}


def list_existing_record_ids(base_token: str, table_id: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    offset = 0
    limit = 200
    while True:
        cmd = lark_base_cmd("+record-list", base_token=base_token, table_id=table_id)
        cmd.extend(["--limit", str(limit), "--offset", str(offset)])
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            return mapping
        payload = json.loads(result.stdout).get("data", {})
        fields = payload.get("fields", [])
        rows = payload.get("data", [])
        record_ids = payload.get("record_id_list", [])
        if not rows:
            break
        full_idx = fields.index("仓库全名")
        date_idx = fields.index("日期")
        for rec_id, row in zip(record_ids, rows):
            mapping[f"{row[full_idx]}|{str(row[date_idx]).split(' ')[0].split('T')[0]}"] = rec_id
        if len(rows) < limit:
            break
        offset += limit
    return mapping


def upsert_rows(base_token: str, table_id: str, records: list[dict]) -> bool:
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
        for start in range(0, len(to_create), 200):
            chunk = to_create[start : start + 200]
            payload = {
                "fields": field_names,
                "rows": [[r["fields"].get(k, "") for k in field_names] for r in chunk],
            }
            cmd = lark_base_cmd("+record-batch-create", base_token=base_token, table_id=table_id)
            cmd.extend(["--json", json.dumps(payload, ensure_ascii=False)])
            for attempt in (0, 1, 2):
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                if res.returncode == 0:
                    break
                msg = res.stderr.strip() or res.stdout.strip()
                if "limited" in msg or "800004135" in msg:
                    time.sleep(1 + attempt)
                    continue
                print("create failed:", msg)
                ok = False
                break
            else:
                print("create failed: rate limited")
                ok = False

    for rec_id, patch in to_update:
        cmd = lark_base_cmd("+record-batch-update", base_token=base_token, table_id=table_id)
        cmd.extend(["--json", json.dumps({"record_id_list": [rec_id], "patch": patch}, ensure_ascii=False)])
        for attempt in (0, 1, 2):
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if res.returncode == 0:
                break
            msg = res.stderr.strip() or res.stdout.strip()
            if "limited" in msg or "800004135" in msg:
                time.sleep(1 + attempt)
                continue
            print("update failed:", rec_id, msg)
            ok = False
            break
        else:
            print("update failed:", rec_id, "rate limited")
            ok = False
    return ok


def main() -> int:
    load_env_file()
    base_token = os.getenv("LARK_BASE_TOKEN", "")
    table_id = os.getenv("LARK_OPENVIKING_TRAFFIC_TABLE_ID", "")
    if not base_token or not table_id:
        print("缺少 .env 配置: LARK_BASE_TOKEN / LARK_OPENVIKING_TRAFFIC_TABLE_ID")
        return 2

    snapshot_path = resolve_snapshot_path(sys.argv[1] if len(sys.argv) > 1 else None)
    snapshot = load_traffic_snapshot(snapshot_path)
    rows = build_daily_traffic_rows(snapshot)
    records = [{"fields": row} for row in rows]
    ok = upsert_rows(base_token, table_id, records)
    print(f"snapshot: {snapshot_path}")
    print(f"rows: {len(records)}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
