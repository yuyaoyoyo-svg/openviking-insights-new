#!/usr/bin/env python3
"""
通过 lark-cli 将采集结果同步到飞书多维表格。
"""

import json
import os
import logging
import subprocess
import time
from datetime import datetime
from pathlib import Path

from env_utils import load_env_file
from lark_cli_utils import ensure_lark_cli_ready, get_lark_identity, lark_base_cmd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_env_file()


def parse_insights_date(file_path: Path):
    try:
        return datetime.strptime(file_path.stem.replace("insights_", ""), "%Y-%m-%d")
    except ValueError:
        return datetime.fromtimestamp(file_path.stat().st_mtime)


def get_lark_config():
    """读取飞书同步所需配置。"""
    config = {
        "base_token": os.getenv("LARK_BASE_TOKEN", ""),
        "table_id": os.getenv("LARK_TABLE_ID", ""),
    }

    missing = [name for name, value in config.items() if not value]
    if missing:
        logger.error("缺少飞书配置: %s", ", ".join(missing))
        return None

    return config


def sync_to_lark_bitable(records):
    """使用已登录的 lark-cli 用户身份同步数据到飞书多维表格。"""
    config = get_lark_config()
    if not config:
        return False

    if not ensure_lark_cli_ready():
        return False

    return sync_to_lark_via_cli(records, config)


def sync_to_lark_via_cli(records, config):
    """使用 lark-cli 身份写入飞书多维表格。"""
    if not records:
        logger.info("没有需要同步的记录")
        return True

    fields = list(records[0]["fields"].keys())
    rows = []
    for record in records:
        row = [record["fields"].get(field, "") for field in fields]
        rows.append(row)

    payload = {"fields": fields, "rows": rows}
    cmd = lark_base_cmd(
        "+record-batch-create", base_token=config["base_token"], table_id=config["table_id"]
    )
    cmd.extend(["--json", json.dumps(payload, ensure_ascii=False)])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except Exception as exc:
        logger.error("lark-cli 写入异常: %s", exc)
        return False

    if result.returncode == 0:
        logger.info("✓ 已通过 lark-cli(%s) 写入 %s 条记录", get_lark_identity(), len(records))
        return True

    logger.error("lark-cli 写入失败: %s", result.stderr.strip() or result.stdout.strip())
    return False


def list_existing_records(base_token: str, table_id: str) -> dict:
    """获取当前表所有记录并建立 key -> record_id 映射。key = 仓库全名|日期(yyyy-MM-dd)."""
    cmd = lark_base_cmd("+record-list", base_token=base_token, table_id=table_id)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        logger.warning("读取现有记录失败，后续将直接追加: %s", result.stderr.strip() or result.stdout.strip())
        return {}

    try:
        payload = json.loads(result.stdout)
    except Exception:
        return {}

    data = payload.get("data", {})
    field_names = data.get("fields", [])
    record_ids = data.get("record_id_list", [])
    rows = data.get("data", [])

    try:
        full_name_idx = field_names.index("仓库全名")
        date_idx = field_names.index("日期")
    except ValueError:
        return {}

    mapping = {}
    for rec_id, row in zip(record_ids, rows):
        full_name = row[full_name_idx]
        date_value = row[date_idx]
        # 日期字段在 record-list 输出里可能是 "YYYY-MM-DD 00:00:00" 或 ISO 字符串
        date_str = str(date_value).split(" ")[0].split("T")[0]
        mapping[f"{full_name}|{date_str}"] = rec_id
    return mapping


def list_table_field_names(base_token: str, table_id: str) -> set[str]:
    cmd = lark_base_cmd("+field-list", base_token=base_token, table_id=table_id)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        return set()
    try:
        payload = json.loads(result.stdout)
    except Exception:
        return set()
    items = payload.get("data", {}).get("items") or payload.get("data", {}).get("fields") or []
    return {it.get("field_name") or it.get("name") for it in items if (it.get("field_name") or it.get("name"))}


def batch_upsert_records(base_token: str, table_id: str, records: list[dict]) -> bool:
    """按 key(仓库全名+日期) 更新已有记录，否则新增。"""
    existing = list_existing_records(base_token, table_id)
    table_fields = list_table_field_names(base_token, table_id)

    to_create = []
    to_update = []

    for record in records:
        fields = record["fields"]
        full_name = fields.get("仓库全名", "")
        date_str = str(fields.get("日期", "")).split(" ")[0].split("T")[0]
        key = f"{full_name}|{date_str}"
        rec_id = existing.get(key)
        if rec_id:
            to_update.append((rec_id, fields))
        else:
            to_create.append(record)

    ok = True
    if to_create:
        ok = ok and sync_to_lark_via_cli(to_create, {"base_token": base_token, "table_id": table_id})

    # lark-cli 当前 batch update 仅支持同一 patch 套到多条记录；这里每条记录字段不同，所以逐条更新最稳。
    for rec_id, patch_fields in to_update:
        update_patch = {
            "仓库名称": patch_fields.get("仓库名称", ""),
            "仓库全名": patch_fields.get("仓库全名", ""),
            "生态位层级": patch_fields.get("生态位层级", "OpenViking同生态位"),
            "项目类型": patch_fields.get("项目类型", "Peer"),
            "日期": patch_fields.get("日期", ""),
            "Stars": patch_fields.get("Stars", 0),
            "Forks": patch_fields.get("Forks", 0),
            "Watchers": patch_fields.get("Watchers", 0),
            "Open Issues": patch_fields.get("Open Issues", 0),
            "Open PRs": patch_fields.get("Open PRs", 0),
            "Contributors": patch_fields.get("Contributors", 0),
            "社区活力评分": patch_fields.get("社区活力评分", 0),
            "外部影响力评分": patch_fields.get("外部影响力评分", 0),
            "综合健康度": patch_fields.get("综合健康度", 0),
            "社区互动总量": patch_fields.get("社区互动总量", 0),
            "外部吸引力指数(log+加权)": patch_fields.get("外部吸引力指数(log+加权)", 0),
            "外部吸引力指数": patch_fields.get("外部吸引力指数(log+加权)", 0),
            "语言": patch_fields.get("语言", ""),
            "最后推送时间": patch_fields.get("最后推送时间", ""),
            "GitHub链接": patch_fields.get("GitHub链接", ""),
            "对比基准日期": patch_fields.get("对比基准日期", ""),
            "采集间隔天数": patch_fields.get("采集间隔天数", 0),
            "Stars日增量": patch_fields.get("Stars日增量", 0),
            "Forks日增量": patch_fields.get("Forks日增量", 0),
            "Watchers日增量": patch_fields.get("Watchers日增量", 0),
            "Open Issues日增量": patch_fields.get("Open Issues日增量", 0),
            "Open PRs日增量": patch_fields.get("Open PRs日增量", 0),
            "Contributors日增量": patch_fields.get("Contributors日增量", 0),
            "近期增长动力": patch_fields.get("近期增长动力", 0),
            "访客→Star转化率": patch_fields.get("访客→Star转化率", "待补traffic"),
            "访客→克隆者转化率": patch_fields.get("访客→克隆者转化率", "待补traffic"),
            # 兼容旧字段名与新字段名，实际落表时会过滤不存在字段
            "贡献者增长/Star增长比": patch_fields.get("贡献者增长/Star增长比", "N/A"),
            "Star→贡献者转化率": patch_fields.get("贡献者增长/Star增长比", "N/A"),
            "贡献者总数/Star总数": patch_fields.get("贡献者总数/Star总数", "N/A"),
        }
        # 只保留当前表确实存在的字段，避免 not_found
        if table_fields:
            update_patch = {k: v for k, v in update_patch.items() if k in table_fields}
        cmd = lark_base_cmd("+record-batch-update", base_token=base_token, table_id=table_id)
        cmd.extend(
            [
                "--json",
                json.dumps(
                    {"record_id_list": [rec_id], "patch": update_patch},
                    ensure_ascii=False,
                ),
            ]
        )
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            msg = result.stderr.strip() or result.stdout.strip()
            # 限流时做简单退避重试
            if "limited" in msg or "800004135" in msg:
                for attempt in (1, 2, 3):
                    time.sleep(attempt)
                    retry = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                    if retry.returncode == 0:
                        break
                    msg = retry.stderr.strip() or retry.stdout.strip()
                else:
                    logger.error("更新失败(%s): %s", rec_id, msg)
                    ok = False
            else:
                logger.error("更新失败(%s): %s", rec_id, msg)
                ok = False

    if to_update:
        logger.info("✓ 已更新 %s 条记录", len(to_update))
    return ok


def main():
    # 优先读取当天采集结果，不存在时回退到最新 insights 文件
    data_dir = Path("data")
    today_file = data_dir / f"insights_{datetime.now().strftime('%Y-%m-%d')}.json"

    if today_file.exists():
        insights_file = today_file
    else:
        candidates = sorted(data_dir.glob("insights_*.json"))
        if not candidates:
            logger.error("未找到可同步的 insights 数据文件")
            return False
        insights_file = max(candidates, key=lambda path: (parse_insights_date(path), path.stat().st_mtime))

    with open(insights_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    logger.info(f"准备同步 {len(data['projects'])} 个项目到飞书，数据文件: {insights_file}")

    # 准备记录
    records = []
    today_str = datetime.now().strftime("%Y-%m-%d")
    for project in data["projects"]:
        record = {
            "fields": {
                "仓库名称": project.get("name", ""),
                "仓库全名": project.get("full_name", f"{project.get('owner', '')}/{project.get('repo', '')}"),
                "生态位层级": project.get("ecosystem_tier", "更广义Agent生态位"),
                "项目类型": "OpenViking" if project.get("type") == "self" else "Peer",
                "日期": today_str,
                "Stars": project.get("stars", 0),
                "Forks": project.get("forks", 0),
                "Watchers": project.get("watchers", 0),
                "Open Issues": project.get("open_issues", 0),
                "Open PRs": project.get("open_prs", 0),
                "Contributors": project.get("contributors_count", 0),
                "社区活力评分": project.get("vitality_score", 0),
                "外部影响力评分": project.get("influence_score", 0),
                "综合健康度": project.get("overall_health_score", 0),
                "社区互动总量": project.get("community_engagement_total", 0),
                "外部吸引力指数(log+加权)": project.get("external_attraction_index", 0),
                "语言": project.get("language", ""),
                "最后推送时间": project.get("pushed_at", ""),
                "GitHub链接": project.get("github_url", ""),
                "对比基准日期": project.get("baseline_date", ""),
                "采集间隔天数": project.get("days_since_last_snapshot", 0),
                "Stars日增量": project.get("stars_daily_delta", 0),
                "Forks日增量": project.get("forks_daily_delta", 0),
                "Watchers日增量": project.get("watchers_daily_delta", 0),
                "Open Issues日增量": project.get("open_issues_daily_delta", 0),
                "Open PRs日增量": project.get("open_prs_daily_delta", 0),
                "Contributors日增量": project.get("contributors_daily_delta", 0),
                "近期增长动力": project.get("recent_growth_momentum", 0),
                "访客→Star转化率": project.get("visitor_to_star_conversion", "待补traffic"),
                "访客→克隆者转化率": project.get("visitor_to_cloner_conversion", "待补traffic"),
                "贡献者增长/Star增长比": project.get("contributor_growth_star_growth_ratio", "N/A"),
                "贡献者总数/Star总数": project.get("contributors_to_star_total_ratio", "N/A"),
            }
        }
        records.append(record)

    # 同步到飞书（upsert）
    config = get_lark_config()
    if not config:
        return False

    table_fields = list_table_field_names(config["base_token"], config["table_id"])
    if table_fields:
        for record in records:
            record["fields"] = {k: v for k, v in record["fields"].items() if k in table_fields}

    success = batch_upsert_records(config["base_token"], config["table_id"], records)

    if success:
        logger.info("✓ 飞书同步完成！")
        logger.info(
            "📊 查看数据: https://bytedance.larkoffice.com/base/%s",
            get_lark_config()["base_token"],
        )
    else:
        logger.error("✗ 飞书同步失败")

    return success


if __name__ == "__main__":
    main()
