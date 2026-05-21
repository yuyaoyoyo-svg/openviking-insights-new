"""
飞书多维表格同步模块
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict
import subprocess

from env_utils import load_env_file

logger = logging.getLogger(__name__)

load_env_file()


class LarkSync:
    """飞书数据同步器"""

    def __init__(self, base_token: str = None, table_id: str = None):
        self.base_token = base_token or os.getenv("LARK_BASE_TOKEN")
        self.table_id = table_id or os.getenv("LARK_TABLE_ID")

    def sync_project_data(self, metrics: Dict) -> bool:
        """同步单个项目数据到飞书"""
        try:
            if not self.base_token or not self.table_id:
                logger.error("缺少飞书配置，请检查 .env 中的 LARK_BASE_TOKEN 和 LARK_TABLE_ID")
                return False

            # 构建字段映射
            fields = {
                "仓库名称": metrics.get("name", ""),
                "仓库全名": metrics.get(
                    "full_name", f"{metrics.get('owner', '')}/{metrics.get('repo', '')}"
                ),
                "生态位层级": metrics.get("ecosystem_tier", "更广义Agent生态位"),
                "项目类型": "OpenViking" if metrics.get("type") == "self" else "Peer",
                "日期": datetime.now().strftime("%Y-%m-%d"),
                "Stars": metrics.get("stars", 0),
                "Forks": metrics.get("forks", 0),
                "Open PRs": metrics.get("open_prs", 0),
                "Open Issues": metrics.get("open_issues", 0),
                "Watchers": metrics.get("watchers", 0),
                "Contributors": metrics.get("contributors_count", 0),
                "社区活力评分": metrics.get("vitality_score", 0),
                "外部影响力评分": metrics.get("influence_score", 0),
                "综合健康度": metrics.get("overall_health_score", 0),
                "社区互动总量": metrics.get("community_engagement_total", 0),
                "外部吸引力指数(log+加权)": metrics.get("external_attraction_index", 0),
                "语言": metrics.get("language", ""),
                "最后推送时间": metrics.get("pushed_at", ""),
                "GitHub链接": metrics.get("github_url", ""),
            }

            # 使用 lark-cli 命令行工具插入数据
            cmd = [
                "lark-cli",
                "base",
                "+record-batch-create",
                "--base-token",
                self.base_token,
                "--table-id",
                self.table_id,
                "--json",
                json.dumps({"fields": list(fields.keys()), "rows": [[fields[k] for k in fields]]}, ensure_ascii=False),
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                logger.info(f"  ✓ 已同步: {metrics.get('name')}")
                return True
            else:
                logger.error(f"  ✗ 同步失败: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"  ✗ 同步异常: {e}")
            return False


if __name__ == "__main__":
    # 测试代码
    import os

    logging.basicConfig(level=logging.INFO)

    # 创建测试数据
    test_metrics = {
        "name": "TestProject",
        "owner": "testowner",
        "repo": "testrepo",
        "type": "self",
        "stars": 100,
        "forks": 50,
        "open_issues": 10,
        "watchers": 100,
        "size_kb": 1024,
        "vitality_score": 75.5,
        "influence_score": 80.0,
    }

    # 测试同步
    sync = LarkSync()
    result = sync.sync_project_data(test_metrics)

    if result:
        print("✓ 测试同步成功")
    else:
        print("✗ 测试同步失败")
