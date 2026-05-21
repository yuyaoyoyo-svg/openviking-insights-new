#!/usr/bin/env python3
"""
OpenViking 项目洞察 - 主程序
整合数据采集、校准计算和飞书同步
"""

import os
import sys
import json
import logging
from datetime import datetime, date
from pathlib import Path
import math

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from env_utils import load_env_file


def load_projects():
    """加载项目配置"""
    config_path = Path(__file__).parent / "config" / "projects.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_insights_date(file_path: Path) -> date | None:
    """从 insights 文件名中解析日期。"""
    try:
        return datetime.strptime(file_path.stem.replace("insights_", ""), "%Y-%m-%d").date()
    except ValueError:
        return None


def load_previous_projects(data_dir: Path, current_date: date) -> tuple[date | None, dict]:
    """优先加载昨天的快照；若缺失，则回退到当前日期之前最近一次快照。"""
    yesterday = current_date.fromordinal(current_date.toordinal() - 1)
    yesterday_file = data_dir / f"insights_{yesterday.isoformat()}.json"
    if yesterday_file.exists():
        with open(yesterday_file, "r", encoding="utf-8") as f:
            payload = json.load(f)
        previous_projects = {
            project.get("full_name", f"{project.get('owner', '')}/{project.get('repo', '')}"): project
            for project in payload.get("projects", [])
        }
        return yesterday, previous_projects

    candidates = []
    for file_path in data_dir.glob("insights_*.json"):
        snapshot_date = parse_insights_date(file_path)
        if snapshot_date and snapshot_date < current_date:
            candidates.append((snapshot_date, file_path))

    if not candidates:
        return None, {}

    previous_date, previous_file = max(candidates, key=lambda item: item[0])
    logger.warning("未找到昨天的快照，回退使用最近一次历史快照: %s", previous_date.isoformat())
    with open(previous_file, "r", encoding="utf-8") as f:
        payload = json.load(f)

    previous_projects = {
        project.get("full_name", f"{project.get('owner', '')}/{project.get('repo', '')}"): project
        for project in payload.get("projects", [])
    }
    return previous_date, previous_projects


def format_ratio_percent(numerator: float, denominator: float, decimals: int = 2) -> str:
    """按百分比格式化比值。"""
    if denominator <= 0:
        return "N/A"
    return f"{(numerator / denominator) * 100:.{decimals}f}%"


def add_snapshot_derived_metrics(metrics: list[dict]) -> list[dict]:
    """补充快照表中的综合性计算指标。"""
    for project in metrics:
        vitality = float(project.get("vitality_score", 0) or 0)
        influence = float(project.get("influence_score", 0) or 0)
        open_issues = float(project.get("open_issues", 0) or 0)
        open_prs = float(project.get("open_prs", 0) or 0)
        contributors = float(project.get("contributors_count", 0) or 0)
        stars = float(project.get("stars", 0) or 0)
        forks = float(project.get("forks", 0) or 0)
        stars_daily = float(project.get("stars_daily_delta", 0) or 0)
        forks_daily = float(project.get("forks_daily_delta", 0) or 0)
        contributors_daily = float(project.get("contributors_daily_delta", 0) or 0)

        project["overall_health_score"] = round((vitality + influence) / 2, 2)
        project["community_engagement_total"] = round(open_issues + open_prs + contributors, 2)
        # External attraction: log-compress to reduce scale dominance, then weight forks higher (stronger intent signal).
        # We intentionally do NOT include watchers here because it often overlaps with stars in GitHub API semantics.
        project["external_attraction_index"] = round(math.log1p(stars) + 2 * math.log1p(forks), 4)
        # Recent growth: weight deeper signals higher than lightweight attention.
        project["recent_growth_momentum"] = round(
            1.0 * stars_daily + 2.0 * forks_daily + 3.0 * contributors_daily, 2
        )

    return metrics


def enrich_metrics_with_history(metrics: list[dict], data_dir: Path, current_date: date) -> list[dict]:
    """基于最近一次快照补充按天折算的增量与可计算的转化率。"""
    previous_date, previous_projects = load_previous_projects(data_dir, current_date)
    if not previous_date:
        for project in metrics:
            project["baseline_date"] = ""
            project["days_since_last_snapshot"] = 0
            project["stars_daily_delta"] = 0
            project["forks_daily_delta"] = 0
            project["watchers_daily_delta"] = 0
            project["open_issues_daily_delta"] = 0
            project["open_prs_daily_delta"] = 0
            project["contributors_daily_delta"] = 0
            project["visitor_to_star_conversion"] = "待补traffic"
            project["visitor_to_cloner_conversion"] = "待补traffic"
            project["contributor_growth_star_growth_ratio"] = "N/A"
            project["contributors_to_star_total_ratio"] = format_ratio_percent(
                project.get("contributors_count", 0) or 0,
                project.get("stars", 0) or 0,
                decimals=4,
            )
        return add_snapshot_derived_metrics(metrics)

    days_gap = max((current_date - previous_date).days, 1)
    delta_fields = {
        "stars": "stars_daily_delta",
        "forks": "forks_daily_delta",
        "watchers": "watchers_daily_delta",
        "open_issues": "open_issues_daily_delta",
        "open_prs": "open_prs_daily_delta",
        "contributors_count": "contributors_daily_delta",
    }

    for project in metrics:
        full_name = project.get("full_name", f"{project.get('owner', '')}/{project.get('repo', '')}")
        baseline = previous_projects.get(full_name, {})
        project["baseline_date"] = previous_date.isoformat()
        project["days_since_last_snapshot"] = days_gap

        for source_field, delta_field in delta_fields.items():
            current_value = project.get(source_field, 0) or 0
            previous_value = baseline.get(source_field, 0) or 0
            daily_delta = round((current_value - previous_value) / days_gap, 2)
            project[delta_field] = daily_delta

        project["visitor_to_star_conversion"] = "待补traffic"
        project["visitor_to_cloner_conversion"] = "待补traffic"
        # 这是“增长比”而不是传统转化率；用阈值避免小分母放大
        stars_daily_delta = project.get("stars_daily_delta", 0) or 0
        if stars_daily_delta < 10:
            project["contributor_growth_star_growth_ratio"] = "N/A"
        else:
            project["contributor_growth_star_growth_ratio"] = format_ratio_percent(
                project.get("contributors_daily_delta", 0) or 0,
                stars_daily_delta,
            )

        project["contributors_to_star_total_ratio"] = format_ratio_percent(
            project.get("contributors_count", 0) or 0,
            project.get("stars", 0) or 0,
            decimals=4,
        )

    return add_snapshot_derived_metrics(metrics)


def collect_github_data(github_token):
    """采集 GitHub 数据"""
    from github_collector import GitHubCollector

    config = load_projects()
    collector = GitHubCollector(github_token)

    all_metrics = []

    for project in config["projects"]:
        try:
            logger.info(f"正在采集: {project['owner']}/{project['repo']}")
            metrics = collector.collect_basic_metrics(project["owner"], project["repo"])
            if metrics:
                metrics["type"] = project["type"]
                metrics["ecosystem_tier"] = project.get("ecosystem_tier", "更广义Agent生态位")
                all_metrics.append(metrics)
                logger.info(f"  ✓ Stars: {metrics.get('stars', 0)}")
        except Exception as e:
            logger.error(f"  ✗ 采集失败: {e}")

    return all_metrics


def main():
    """主函数"""
    load_env_file()

    logger.info("=" * 60)
    logger.info("OpenViking 项目洞察 - 数据采集与校准系统")
    logger.info("=" * 60)

    # 获取 GitHub Token
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        logger.error("错误: 未设置 GITHUB_TOKEN 环境变量")
        logger.info("请在项目根目录的 .env 文件中设置 GITHUB_TOKEN")
        return 1

    try:
        # 采集 GitHub 数据
        logger.info("\\n[步骤 1/2] 采集 GitHub 数据...")
        metrics = collect_github_data(github_token)
        logger.info(f"✓ 成功采集 {len(metrics)} 个项目的数据")

        # 保存数据
        logger.info("\\n[步骤 2/2] 保存数据...")
        data_dir = Path(__file__).parent / "data"
        data_dir.mkdir(exist_ok=True)

        target_date_str = os.getenv("OV_OVERRIDE_DATE", "").strip()
        if target_date_str:
            target_dt = datetime.strptime(target_date_str, "%Y-%m-%d")
        else:
            target_dt = datetime.now()

        date_str = target_dt.strftime("%Y-%m-%d")
        metrics = enrich_metrics_with_history(metrics, data_dir, target_dt.date())
        insights_file = data_dir / f"insights_{date_str}.json"

        with open(insights_file, "w", encoding="utf-8") as f:
            json.dump(
                {"collected_at": datetime.now().isoformat(), "projects": metrics},
                f,
                ensure_ascii=False,
                indent=2,
            )

        logger.info(f"✓ 数据已保存: {insights_file}")

        # 完成
        logger.info("\\n" + "=" * 60)
        logger.info("✓ 所有任务完成！")
        logger.info("=" * 60)
        logger.info(f"📊 采集项目: {len(metrics)} 个")
        logger.info(f"📁 数据文件: {insights_file}")
        logger.info("=" * 60)

        return 0

    except Exception as e:
        logger.error(f"\\n✗ 运行出错: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
