#!/usr/bin/env python3
"""
创建/补齐 OSSInsight 趋势表，并将表 ID 回写到 .env（LARK_TRENDS_TABLE_ID）。
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

TABLE_NAME = "生态位趋势(日)"

FIELD_DEFS = [
    {"type": "datetime", "name": "日期", "style": {"format": "yyyy-MM-dd"}},
    {"type": "text", "name": "仓库全名"},
    {
        "type": "select",
        "name": "生态位层级",
        "options": [{"name": "OpenViking同生态位"}, {"name": "更广义Agent生态位"}],
    },
    {"type": "number", "name": "OSSInsight Stars(累计)"},
    {"type": "number", "name": "OSSInsight Stars(日增)"},
    {"type": "number", "name": "PR Creators(累计)"},
    {"type": "number", "name": "PR Creators(日增)"},
    {"type": "number", "name": "Issue Creators(累计)"},
    {"type": "number", "name": "Issue Creators(日增)"},
    {"type": "text", "name": "数据源"},
]

VIEW_DEFS = [
    {"name": "全部趋势", "type": "grid"},
    {"name": "OpenViking同生态位", "type": "grid"},
    {"name": "更广义Agent生态位", "type": "grid"},
]


def run_json(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return json.loads(result.stdout)


def ensure_lark_cli_ready():
    status = subprocess.run(
        ["lark-cli", "auth", "status"], capture_output=True, text=True, timeout=30
    )
    if status.returncode != 0:
        raise RuntimeError("lark-cli 尚未登录，请先执行 `lark-cli auth login --recommend`")


def get_base_token():
    load_env_file()
    base_token = os.getenv("LARK_BASE_TOKEN")
    if not base_token:
        raise RuntimeError("未设置 LARK_BASE_TOKEN")
    return base_token


def list_tables(base_token):
    payload = run_json(
        ["lark-cli", "base", "+table-list", "--base-token", base_token, "--as", "user"]
    )
    return payload.get("data", {}).get("tables", [])


def find_table_id(base_token, table_name):
    for table in list_tables(base_token):
        if table.get("name") == table_name:
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
            json.dumps(VIEW_DEFS, ensure_ascii=False),
        ]
    )
    table_id = find_table_id(base_token, TABLE_NAME)
    if not table_id:
        raise RuntimeError("创建表成功但未能找到新表 ID")
    return table_id


def list_fields(base_token, table_id):
    payload = run_json(
        [
            "lark-cli",
            "base",
            "+field-list",
            "--base-token",
            base_token,
            "--table-id",
            table_id,
            "--as",
            "user",
        ]
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


def update_env_trends_table_id(table_id):
    env_path = Path(__file__).resolve().parent.parent / ".env"
    lines = env_path.read_text(encoding="utf-8").splitlines()
    updated = False
    for idx, line in enumerate(lines):
        if line.startswith("LARK_TRENDS_TABLE_ID="):
            lines[idx] = f"LARK_TRENDS_TABLE_ID={table_id}"
            updated = True
            break
    if not updated:
        lines.append(f"LARK_TRENDS_TABLE_ID={table_id}")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    ensure_lark_cli_ready()
    base_token = get_base_token()
    table_id = find_table_id(base_token, TABLE_NAME)
    if table_id:
        logger.info("检测到已存在趋势表: %s", table_id)
    else:
        table_id = create_table(base_token)
        logger.info("已创建趋势表: %s", table_id)

    ensure_fields(base_token, table_id)
    update_env_trends_table_id(table_id)
    logger.info("已将 LARK_TRENDS_TABLE_ID 更新为: %s", table_id)
    logger.info("趋势表链接: https://bytedance.larkoffice.com/base/%s?table=%s", base_token, table_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())

