#!/usr/bin/env python3
"""
检查趋势表中是否存在重复记录。

重复定义：
  仓库全名 + 日期 完全相同，但出现多条 record_id。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections import defaultdict

from env_utils import load_env_file


def ensure_lark_cli_ready() -> bool:
    status = subprocess.run(
        ["lark-cli", "auth", "status"], capture_output=True, text=True, timeout=30
    )
    return status.returncode == 0


def iter_trend_records(base_token: str, table_id: str):
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
        fields = payload.get("fields", [])
        rows = payload.get("data", [])
        record_ids = payload.get("record_id_list", [])
        if not rows:
            break

        yield fields, rows, record_ids

        if len(rows) < limit:
            break
        offset += limit


def main() -> int:
    load_env_file()
    base_token = os.getenv("LARK_BASE_TOKEN", "")
    table_id = os.getenv("LARK_TRENDS_TABLE_ID", "")
    if not base_token or not table_id:
        print("缺少飞书配置：LARK_BASE_TOKEN / LARK_TRENDS_TABLE_ID")
        return 2

    if not ensure_lark_cli_ready():
        print("lark-cli 未登录")
        return 2

    grouped: dict[tuple[str, str], list[str]] = defaultdict(list)
    total_rows = 0

    for fields, rows, record_ids in iter_trend_records(base_token, table_id):
        try:
            full_idx = fields.index("仓库全名")
            date_idx = fields.index("日期")
        except ValueError:
            print("趋势表缺少字段：仓库全名 或 日期")
            return 2

        for rec_id, row in zip(record_ids, rows):
            full_name = row[full_idx]
            date_str = str(row[date_idx]).split(" ")[0].split("T")[0]
            grouped[(full_name, date_str)].append(rec_id)
            total_rows += 1

    duplicates = {k: v for k, v in grouped.items() if len(v) > 1}

    print(f"趋势表总记录数: {total_rows}")
    print(f"唯一 key 数量: {len(grouped)}")
    print(f"重复 key 数量: {len(duplicates)}")

    if not duplicates:
        print("结果: 未发现任何 仓库全名 + 日期 的重复记录")
        return 0

    print("结果: 发现重复记录")
    for (full_name, date_str), record_ids in sorted(duplicates.items()):
        print(f"- {full_name} | {date_str} | count={len(record_ids)} | record_ids={record_ids}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
