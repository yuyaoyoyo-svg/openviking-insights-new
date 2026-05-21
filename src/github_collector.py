#!/usr/bin/env python3
"""
GitHub 数据采集模块
负责采集 GitHub 仓库的各项指标数据
"""

import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import time
import logging
import re

logger = logging.getLogger(__name__)


class GitHubCollector:
    """GitHub 数据采集器"""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: str):
        self.token = token
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "OpenViking-Insights/1.0",
            }
        )
        self.rate_limit_remaining = 5000
        self.rate_limit_reset = 0

    def _check_rate_limit(self):
        """检查并处理速率限制"""
        if self.rate_limit_remaining < 10:
            wait_time = max(0, self.rate_limit_reset - time.time())
            if wait_time > 0:
                logger.warning(f"Rate limit hit, waiting {wait_time:.0f} seconds")
                time.sleep(wait_time + 1)

    def _update_rate_limit(self, headers: dict):
        """更新速率限制信息"""
        self.rate_limit_remaining = int(headers.get("X-RateLimit-Remaining", 5000))
        self.rate_limit_reset = int(headers.get("X-RateLimit-Reset", 0))

    def _make_request(self, url: str, **kwargs) -> Optional[requests.Response]:
        """发送请求并处理错误"""
        self._check_rate_limit()

        try:
            response = self.session.get(url, **kwargs)
            self._update_rate_limit(response.headers)

            if response.status_code == 200:
                return response
            elif response.status_code == 404:
                logger.warning(f"Resource not found: {url}")
                return None
            elif response.status_code == 403:
                logger.error(f"Rate limit exceeded: {url}")
                time.sleep(60)
                return None
            else:
                logger.error(f"Request failed: {url}, status: {response.status_code}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            return None

    def get_repository_info(self, owner: str, repo: str) -> Dict:
        """获取仓库基本信息"""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}"
        response = self._make_request(url)

        if response:
            data = response.json()
            return {
                "name": data.get("name", ""),
                "full_name": data.get("full_name", ""),
                "description": data.get("description", ""),
                "stars": data.get("stargazers_count", 0),
                "forks": data.get("forks_count", 0),
                "open_issues": data.get("open_issues_count", 0),
                "watchers": data.get("watchers_count", 0),
                "created_at": data.get("created_at", ""),
                "updated_at": data.get("updated_at", ""),
                "pushed_at": data.get("pushed_at", ""),
                "size": data.get("size", 0),
                "language": data.get("language", ""),
                "license": data.get("license", {}).get("name", "")
                if data.get("license")
                else "",
                "archived": data.get("archived", False),
                "topics": data.get("topics", []),
            }
        return {}

    def _get_last_page_count(self, response: requests.Response) -> int:
        """通过分页 Link 头估算总条数。"""
        link = response.headers.get("Link", "")
        match = re.search(r'[?&]page=(\d+)>; rel="last"', link)
        if match:
            return int(match.group(1))
        return len(response.json())

    def get_open_prs_count(self, owner: str, repo: str) -> int:
        """获取打开中的 PR 数量。"""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/pulls?state=open&per_page=1"
        response = self._make_request(url)
        if not response:
            return 0
        return self._get_last_page_count(response)

    def get_open_issues_count(self, owner: str, repo: str) -> int:
        """获取打开中的 Issue 数量，不包含 PR。"""
        url = f"{self.BASE_URL}/search/issues?q=repo:{owner}/{repo}+type:issue+state:open"
        response = self._make_request(url)
        if not response:
            return 0
        return response.json().get("total_count", 0)

    def get_contributors_count(self, owner: str, repo: str) -> int:
        """获取贡献者数量。"""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/contributors?per_page=1&anon=false"
        response = self._make_request(url)
        if not response:
            return 0
        return self._get_last_page_count(response)

    def collect_basic_metrics(self, owner: str, repo: str) -> Dict:
        """采集基础指标"""
        logger.info(f"Collecting basic metrics for {owner}/{repo}")

        info = self.get_repository_info(owner, repo)

        if not info:
            logger.warning(f"Failed to get repository info for {owner}/{repo}")
            return {}

        open_prs = self.get_open_prs_count(owner, repo)
        open_issues = self.get_open_issues_count(owner, repo)
        contributors_count = self.get_contributors_count(owner, repo)

        # 计算社区活力评分 (0-100)
        vitality_score = min(
            100,
            (
                min(40, open_issues * 0.5)
                + min(30, info.get("forks", 0) * 0.1)
                + min(30, info.get("watchers", 0) * 0.1)
            ),
        )

        # 计算外部影响力评分 (0-100)
        influence_score = min(
            100,
            (
                min(50, info.get("stars", 0) * 0.01)
                + min(30, info.get("forks", 0) * 0.02)
                + min(20, info.get("watchers", 0) * 0.02)
            ),
        )

        return {
            "owner": owner,
            "repo": repo,
            "name": info.get("name", ""),
            "full_name": info.get("full_name", ""),
            "description": info.get("description", ""),
            "stars": info.get("stars", 0),
            "forks": info.get("forks", 0),
            "open_issues": open_issues,
            "open_prs": open_prs,
            "watchers": info.get("watchers", 0),
            "contributors_count": contributors_count,
            "size_kb": info.get("size", 0),
            "language": info.get("language", ""),
            "license": info.get("license", ""),
            "topics": info.get("topics", []),
            "created_at": info.get("created_at", ""),
            "updated_at": info.get("updated_at", ""),
            "pushed_at": info.get("pushed_at", ""),
            "github_url": f"https://github.com/{owner}/{repo}",
            "vitality_score": round(vitality_score, 1),
            "influence_score": round(influence_score, 1),
            "collected_at": datetime.now().isoformat(),
        }


if __name__ == "__main__":
    import os

    logging.basicConfig(level=logging.INFO)

    # 从环境变量获取 token
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("请设置 GITHUB_TOKEN 环境变量")
        exit(1)

    # 测试采集
    collector = GitHubCollector(token)
    metrics = collector.collect_basic_metrics("volcengine", "OpenViking")

    print(json.dumps(metrics, indent=2, ensure_ascii=False, default=str))
