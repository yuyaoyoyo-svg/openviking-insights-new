#!/bin/bash
# 导出 OpenViking GitHub Traffic 原始数据
#
# 用法:
#   bash src/export_github_traffic.sh
#   bash src/export_github_traffic.sh volcengine OpenViking
#
# 前置条件:
#   1. gh 已安装
#   2. 本地可使用 gh auth 登录态，或在 CI 中提供 GH_TOKEN / GITHUB_TOKEN

set -euo pipefail

OWNER="${1:-volcengine}"
REPO="${2:-OpenViking}"
STAMP="$(date '+%Y-%m-%d_%H%M%S')"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
OUT_DIR="$ROOT_DIR/data/github-traffic/${OWNER}_${REPO}/${STAMP}"

mkdir -p "$OUT_DIR"

if ! command -v gh >/dev/null 2>&1; then
  echo "❌ 未找到 gh，请先安装 GitHub CLI"
  exit 1
fi

echo "📦 导出仓库 traffic: ${OWNER}/${REPO}"
echo "📁 输出目录: $OUT_DIR"

has_env_token() {
  [ -n "${GH_TOKEN:-}" ] || [ -n "${GITHUB_TOKEN:-}" ]
}

gh_auth_available() {
  gh auth status >/dev/null 2>&1
}

probe_traffic_api() {
  "$@" "repos/${OWNER}/${REPO}/traffic/views" --jq '.views[-1].timestamp' >/dev/null 2>&1
}

GH_API=()
AUTH_DESC=""

# 本地运行优先使用 gh keyring 登录态，避免 .env 里的 GITHUB_TOKEN 抢占 traffic API。
# CI/GitHub Actions 中则优先使用环境变量 token。
if [ "${OV_GH_PREFER_ENV:-0}" = "1" ]; then
  if ! has_env_token; then
    echo "❌ OV_GH_PREFER_ENV=1，但未提供 GH_TOKEN / GITHUB_TOKEN"
    exit 1
  fi
  GH_API=(gh api)
  AUTH_DESC="环境变量中的 GitHub Token"
elif [ "${GITHUB_ACTIONS:-}" = "true" ] || [ "${CI:-}" = "true" ]; then
  if has_env_token; then
    GH_API=(gh api)
    AUTH_DESC="CI 环境变量中的 GitHub Token"
  elif gh_auth_available; then
    GH_API=(env -u GH_TOKEN -u GITHUB_TOKEN gh api)
    AUTH_DESC="gh 本地登录态"
  else
    echo "❌ CI 环境未提供 GH_TOKEN / GITHUB_TOKEN，且 gh 当前未登录"
    exit 1
  fi
else
  if gh_auth_available; then
    GH_API=(env -u GH_TOKEN -u GITHUB_TOKEN gh api)
    AUTH_DESC="gh 本地登录态"
  elif has_env_token; then
    GH_API=(gh api)
    AUTH_DESC="环境变量中的 GitHub Token"
  else
    echo "❌ gh 当前未登录，且未提供 GH_TOKEN / GITHUB_TOKEN"
    exit 1
  fi
fi

if ! probe_traffic_api "${GH_API[@]}"; then
  if [ "$AUTH_DESC" != "gh 本地登录态" ] && gh_auth_available; then
    echo "⚠️ ${AUTH_DESC} 无法访问 traffic API，回退到 gh 本地登录态"
    GH_API=(env -u GH_TOKEN -u GITHUB_TOKEN gh api)
    AUTH_DESC="gh 本地登录态"
  elif [ "$AUTH_DESC" = "gh 本地登录态" ] && has_env_token; then
    echo "⚠️ gh 本地登录态无法访问 traffic API，回退到环境变量 Token"
    GH_API=(gh api)
    AUTH_DESC="环境变量中的 GitHub Token"
  else
    echo "❌ 当前可用认证方式均无法访问 traffic API"
    exit 1
  fi
fi

echo "🔐 使用${AUTH_DESC}调用 gh api"

"${GH_API[@]}" "repos/${OWNER}/${REPO}/traffic/views" > "$OUT_DIR/views.json"
"${GH_API[@]}" "repos/${OWNER}/${REPO}/traffic/clones" > "$OUT_DIR/clones.json"
"${GH_API[@]}" "repos/${OWNER}/${REPO}/traffic/popular/paths" > "$OUT_DIR/popular_paths.json"
"${GH_API[@]}" "repos/${OWNER}/${REPO}/traffic/popular/referrers" > "$OUT_DIR/referrers.json"

jq -n \
  --arg pulled_at "$(date '+%Y-%m-%dT%H:%M:%S%z')" \
  --arg repo "${OWNER}/${REPO}" \
  --arg source "gh api repos/${OWNER}/${REPO}/traffic/*" \
  --slurpfile views "$OUT_DIR/views.json" \
  --slurpfile clones "$OUT_DIR/clones.json" \
  --slurpfile paths "$OUT_DIR/popular_paths.json" \
  --slurpfile refs "$OUT_DIR/referrers.json" \
  '{
    pulled_at: $pulled_at,
    repo: $repo,
    source: $source,
    views: $views[0],
    clones: $clones[0],
    popular_paths: $paths[0],
    referrers: $refs[0]
  }' > "$OUT_DIR/traffic_snapshot.json"

cat > "$OUT_DIR/README.md" <<EOF
# ${REPO} GitHub Traffic Snapshot

- Repo: ${OWNER}/${REPO}
- Pulled At: $(date '+%Y-%m-%d %H:%M:%S %z')
- Source: gh api repos/${OWNER}/${REPO}/traffic/*

Files:
- views.json
- clones.json
- popular_paths.json
- referrers.json
- traffic_snapshot.json
EOF

echo "✅ 导出完成: $OUT_DIR"
