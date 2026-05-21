#!/usr/bin/env python3
"""
创建 OpenViking 生态位对比快照表，并将表 ID 回写到 .env。
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

TABLE_NAME = "OpenViking生态位对比快照"

FIELD_DEFS = [
    {"type": "text", "name": "仓库名称"},
    {"type": "text", "name": "仓库全名"},
    {
        "type": "select",
        "name": "生态位层级",
        "options": [{"name": "OpenViking同生态位"}, {"name": "更广义Agent生态位"}],
    },
    {
        "type": "select",
        "name": "项目类型",
        "options": [{"name": "OpenViking"}, {"name": "Peer"}],
    },
    {"type": "datetime", "name": "日期", "style": {"format": "yyyy-MM-dd"}},
    {"type": "number", "name": "Stars"},
    {"type": "number", "name": "Forks"},
    {"type": "number", "name": "Watchers"},
    {"type": "number", "name": "Open Issues"},
    {"type": "number", "name": "Open PRs"},
    {"type": "number", "name": "Contributors"},
    {"type": "number", "name": "社区活力评分"},
    {"type": "number", "name": "外部影响力评分"},
    {"type": "number", "name": "综合健康度"},
    {"type": "number", "name": "社区互动总量"},
    {"type": "number", "name": "外部吸引力指数(log+加权)"},
    {"type": "text", "name": "语言"},
    {"type": "text", "name": "最后推送时间"},
    {"type": "text", "name": "GitHub链接", "style": {"type": "url"}},
    {"type": "datetime", "name": "对比基准日期", "style": {"format": "yyyy-MM-dd"}},
    {"type": "number", "name": "采集间隔天数"},
    {"type": "number", "name": "Stars日增量"},
    {"type": "number", "name": "Forks日增量"},
    {"type": "number", "name": "Watchers日增量"},
    {"type": "number", "name": "Open Issues日增量"},
    {"type": "number", "name": "Open PRs日增量"},
    {"type": "number", "name": "Contributors日增量"},
    {"type": "number", "name": "近期增长动力"},
    {"type": "text", "name": "访客→Star转化率"},
    {"type": "text", "name": "访客→克隆者转化率"},
    {"type": "text", "name": "贡献者增长/Star增长比"},
    {"type": "text", "name": "贡献者总数/Star总数"},
]

VIEW_DEFS = [
    {"name": "全部快照", "type": "grid"},
    {"name": "OpenViking同生态位", "type": "grid"},
    {"name": "更广义Agent生态位", "type": "grid"},
]

VISIBLE_FIELD_NAMES_ALL = [
    "日期",
    "仓库名称",
    "仓库全名",
    "生态位层级",
    "项目类型",
    "Stars",
    "Forks",
    "Watchers",
    "Open Issues",
    "Open PRs",
    "Contributors",
    "社区活力评分",
    "外部影响力评分",
    "综合健康度",
    "社区互动总量",
    "外部吸引力指数(log+加权)",
    "对比基准日期",
    "采集间隔天数",
    "Stars日增量",
    "Forks日增量",
    "Watchers日增量",
    "Open Issues日增量",
    "Open PRs日增量",
    "Contributors日增量",
    "近期增长动力",
    "访客→Star转化率",
    "访客→克隆者转化率",
    "贡献者增长/Star增长比",
    "贡献者总数/Star总数",
    "语言",
    "最后推送时间",
    "GitHub链接",
]

VISIBLE_FIELD_NAMES_COMPARE = [
    "仓库名称",
    "仓库全名",
    "日期",
    "Stars",
    "Forks",
    "Watchers",
    "Open Issues",
    "Open PRs",
    "Contributors",
    "社区活力评分",
    "外部影响力评分",
    "综合健康度",
    "社区互动总量",
    "外部吸引力指数(log+加权)",
    "采集间隔天数",
    "Stars日增量",
    "Forks日增量",
    "Watchers日增量",
    "Open Issues日增量",
    "Open PRs日增量",
    "Contributors日增量",
    "近期增长动力",
    "贡献者增长/Star增长比",
    "贡献者总数/Star总数",
    "语言",
    "最后推送时间",
    "GitHub链接",
]


def run_json(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return json.loads(result.stdout)


def ensure_lark_cli_ready():
    try:
        version = subprocess.run(
            ["lark-cli", "--version"], capture_output=True, text=True, timeout=15
        )
    except FileNotFoundError as exc:
        raise RuntimeError("未找到 lark-cli，请先安装飞书 CLI") from exc

    if version.returncode != 0:
        raise RuntimeError(version.stderr.strip() or version.stdout.strip())

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
        [
            "lark-cli",
            "base",
            "+table-list",
            "--base-token",
            base_token,
            "--as",
            "user",
        ]
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
    """为已存在的表补齐缺失字段。"""
    existing_names = {
        field.get("field_name") or field.get("name") for field in list_fields(base_token, table_id)
    }
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


def ensure_field_renames(base_token, table_id):
    """将旧字段名重命名为新字段名，避免重复列。"""
    renames = {
        "Star→贡献者转化率": "贡献者增长/Star增长比",
        "外部吸引力指数": "外部吸引力指数(log+加权)",
    }
    fields = list_fields(base_token, table_id)
    by_name = {(field.get("field_name") or field.get("name")): field for field in fields}
    existing_names = set(by_name.keys())
    for old, new in renames.items():
        if old in existing_names and new not in existing_names:
            field_type = (by_name.get(old) or {}).get("type") or "text"
            try:
                # 某些版本的 API/CLI 需要同时提交 type，否则会报 discriminator 错误
                run_json(
                    [
                        "lark-cli",
                        "base",
                        "+field-update",
                        "--base-token",
                        base_token,
                        "--table-id",
                        table_id,
                        "--field-id",
                        old,
                        "--as",
                        "user",
                        "--json",
                        json.dumps({"name": new, "type": field_type}, ensure_ascii=False),
                    ]
                )
                logger.info("已重命名字段: %s -> %s", old, new)
            except Exception as exc:
                logger.warning("字段重命名失败(%s -> %s): %s", old, new, exc)


def list_views(base_token, table_id):
    payload = run_json(
        [
            "lark-cli",
            "base",
            "+view-list",
            "--base-token",
            base_token,
            "--table-id",
            table_id,
            "--as",
            "user",
        ]
    )
    return payload.get("data", {}).get("items", []) or payload.get("data", {}).get("views", [])


def configure_views(base_token, table_id):
    fields = list_fields(base_token, table_id)
    field_map = {field.get("field_name") or field.get("name"): field.get("field_id") or field.get("id") for field in fields}
    tier_field_id = field_map.get("生态位层级")
    stars_field_id = field_map.get("Stars")
    date_field_id = field_map.get("日期")
    if not tier_field_id:
        logger.warning("未找到生态位层级字段，跳过视图筛选")

    view_map = {view.get("view_name") or view.get("name"): view.get("view_id") or view.get("id") for view in list_views(base_token, table_id)}
    filter_specs = {
        "OpenViking同生态位": "OpenViking同生态位",
        "更广义Agent生态位": "更广义Agent生态位",
    }

    for view_name, tier_value in filter_specs.items():
        view_id = view_map.get(view_name)
        if not view_id or not tier_field_id:
            continue
        try:
            run_json(
                [
                    "lark-cli",
                    "base",
                    "+view-set-filter",
                    "--base-token",
                    base_token,
                    "--table-id",
                    table_id,
                    "--view-id",
                    view_id,
                    "--as",
                    "user",
                    "--json",
                    json.dumps(
                        {"logic": "and", "conditions": [[tier_field_id, "==", tier_value]]},
                        ensure_ascii=False,
                    ),
                ]
            )
        except Exception as exc:
            logger.warning("设置视图筛选失败(%s): %s", view_name, exc)

    visible_specs = {
        "全部快照": VISIBLE_FIELD_NAMES_ALL,
        "OpenViking同生态位": VISIBLE_FIELD_NAMES_COMPARE,
        "更广义Agent生态位": VISIBLE_FIELD_NAMES_COMPARE,
    }

    for view_name, field_names in visible_specs.items():
        view_id = view_map.get(view_name)
        if not view_id:
            continue
        visible_fields = [field_map[name] for name in field_names if field_map.get(name)]
        try:
            run_json(
                [
                    "lark-cli",
                    "base",
                    "+view-set-visible-fields",
                    "--base-token",
                    base_token,
                    "--table-id",
                    table_id,
                    "--view-id",
                    view_id,
                    "--as",
                    "user",
                    "--json",
                    json.dumps({"visible_fields": visible_fields}, ensure_ascii=False),
                ]
            )
        except Exception as exc:
            logger.warning("设置可见字段失败(%s): %s", view_name, exc)

    sort_specs = {
        "全部快照": [
            {"field": date_field_id, "desc": True},
            {"field": stars_field_id, "desc": True},
        ],
        "OpenViking同生态位": [{"field": stars_field_id, "desc": True}],
        "更广义Agent生态位": [{"field": stars_field_id, "desc": True}],
    }

    for view_name, sort_config in sort_specs.items():
        view_id = view_map.get(view_name)
        if not view_id:
            continue
        cleaned = [item for item in sort_config if item.get("field")]
        if not cleaned:
            continue
        try:
            run_json(
                [
                    "lark-cli",
                    "base",
                    "+view-set-sort",
                    "--base-token",
                    base_token,
                    "--table-id",
                    table_id,
                    "--view-id",
                    view_id,
                    "--as",
                    "user",
                    "--json",
                    json.dumps({"sort_config": cleaned}, ensure_ascii=False),
                ]
            )
        except Exception as exc:
            logger.warning("设置排序失败(%s): %s", view_name, exc)


def update_env_table_id(table_id):
    env_path = Path(__file__).resolve().parent.parent / ".env"
    lines = env_path.read_text(encoding="utf-8").splitlines()
    updated = False
    for idx, line in enumerate(lines):
        if line.startswith("LARK_TABLE_ID="):
            lines[idx] = f"LARK_TABLE_ID={table_id}"
            updated = True
            break
    if not updated:
        lines.append(f"LARK_TABLE_ID={table_id}")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    ensure_lark_cli_ready()
    base_token = get_base_token()
    table_id = find_table_id(base_token, TABLE_NAME)
    if table_id:
        logger.info("检测到已存在比较表: %s", table_id)
    else:
        table_id = create_table(base_token)
        logger.info("已创建比较表: %s", table_id)

    ensure_field_renames(base_token, table_id)
    ensure_fields(base_token, table_id)
    configure_views(base_token, table_id)
    update_env_table_id(table_id)
    logger.info("已将 LARK_TABLE_ID 更新为: %s", table_id)
    logger.info("表格链接: https://bytedance.larkoffice.com/base/%s?table=%s", base_token, table_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
