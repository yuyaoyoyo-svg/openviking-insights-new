#!/usr/bin/env python3
"""
创建/补齐 OpenViking 漏斗(日) 表，并将表 ID 回写到 .env。
"""

import json
import logging
import os
import subprocess
import sys
from pathlib import Path

from env_utils import load_env_file

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TABLE_NAME = "OpenViking 漏斗(日)"
ENV_KEY = "LARK_OPENVIKING_FUNNEL_TABLE_ID"

FIELD_DEFS = [
    {"type": "datetime", "name": "日期", "style": {"format": "yyyy-MM-dd"}},
    {"type": "text", "name": "仓库全名"},
    {"type": "number", "name": "访客数"},
    {"type": "number", "name": "浏览量"},
    {"type": "number", "name": "克隆者数"},
    {"type": "number", "name": "克隆次数"},
    {"type": "number", "name": "Stars日增量"},
    {"type": "number", "name": "Contributors日增量"},
    {"type": "number", "name": "贡献者总数"},
    {"type": "number", "name": "Stars总数"},
    {"type": "text", "name": "访客→Star转化率"},
    {"type": "text", "name": "访客→克隆者转化率"},
    {"type": "text", "name": "贡献者增长/Star增长比"},
    {"type": "text", "name": "贡献者总数/Star总数"},
    {"type": "text", "name": "数据新鲜度说明"},
    {"type": "text", "name": "数据抓取时间"},
    {"type": "text", "name": "数据来源"},
]


def run_json(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return json.loads(result.stdout)


def get_base_token():
    load_env_file()
    base_token = os.getenv("LARK_BASE_TOKEN")
    if not base_token:
        raise RuntimeError("未设置 LARK_BASE_TOKEN")
    return base_token


def list_tables(base_token):
    payload = run_json(["lark-cli", "base", "+table-list", "--base-token", base_token, "--as", "user"])
    return payload.get("data", {}).get("tables", [])


def find_table_id(base_token):
    for table in list_tables(base_token):
        if table.get("name") == TABLE_NAME:
            return table.get("id")
    return None


def create_table(base_token):
    run_json(
        [
            "lark-cli",
            "base",
            "+table-create",
            "--base-token",
            base_token,
            "--as",
            "user",
            "--name",
            TABLE_NAME,
            "--fields",
            json.dumps(FIELD_DEFS, ensure_ascii=False),
            "--view",
            json.dumps([{"name": "全部数据", "type": "grid"}], ensure_ascii=False),
        ]
    )
    table_id = find_table_id(base_token)
    if not table_id:
        raise RuntimeError("创建 OpenViking 漏斗(日) 表后未找到新表 ID")
    return table_id


def list_fields(base_token, table_id):
    payload = run_json(
        ["lark-cli", "base", "+field-list", "--base-token", base_token, "--table-id", table_id, "--as", "user"]
    )
    return payload.get("data", {}).get("items", []) or payload.get("data", {}).get("fields", [])


def ensure_fields(base_token, table_id):
    existing_names = {field.get("field_name") or field.get("name") for field in list_fields(base_token, table_id)}
    for field_def in FIELD_DEFS:
        if field_def["name"] in existing_names:
            continue
        run_json(
            [
                "lark-cli",
                "base",
                "+field-create",
                "--base-token",
                base_token,
                "--table-id",
                table_id,
                "--as",
                "user",
                "--json",
                json.dumps(field_def, ensure_ascii=False),
            ]
        )
        logger.info("已补充字段: %s", field_def["name"])


def update_env_table_id(table_id):
    env_path = Path(__file__).resolve().parent.parent / ".env"
    lines = env_path.read_text(encoding="utf-8").splitlines()
    updated = False
    for idx, line in enumerate(lines):
        if line.startswith(f"{ENV_KEY}="):
            lines[idx] = f"{ENV_KEY}={table_id}"
            updated = True
            break
    if not updated:
        lines.append(f"{ENV_KEY}={table_id}")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    base_token = get_base_token()
    table_id = find_table_id(base_token)
    if not table_id:
        table_id = create_table(base_token)
        logger.info("已创建表: %s", table_id)
    else:
        logger.info("检测到已存在表: %s", table_id)
    ensure_fields(base_token, table_id)
    update_env_table_id(table_id)
    logger.info("已写入 .env: %s=%s", ENV_KEY, table_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
