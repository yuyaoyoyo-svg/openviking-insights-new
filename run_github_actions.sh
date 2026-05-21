#!/bin/bash
# GitHub Actions entrypoint.

set -euo pipefail

ROOT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$ROOT_DIR"

export GITHUB_ACTIONS="${GITHUB_ACTIONS:-true}"
export CI="${CI:-true}"
export LARK_IDENTITY="${LARK_IDENTITY:-bot}"
export OV_GH_PREFER_ENV="${OV_GH_PREFER_ENV:-1}"
export WRITE_ENV_UPDATES=0

echo "============================================"
echo "OpenViking Insights - GitHub Actions"
echo "============================================"
echo "LARK_IDENTITY=$LARK_IDENTITY"

python3 main.py

if [[ -n "${LARK_BASE_TOKEN:-}" && -n "${LARK_TABLE_ID:-}" ]]; then
  python3 src/sync_to_lark_api.py
else
  echo "⚠️ Skip snapshot sync: missing LARK_BASE_TOKEN or LARK_TABLE_ID"
fi

if [[ -n "${LARK_BASE_TOKEN:-}" && -n "${LARK_TRENDS_TABLE_ID:-}" ]]; then
  python3 src/sync_ossinsight_trends.py
else
  echo "⚠️ Skip OSSInsight sync: missing LARK_TRENDS_TABLE_ID"
fi

if bash src/export_github_traffic.sh; then
  if [[ -n "${LARK_BASE_TOKEN:-}" && -n "${LARK_OPENVIKING_TRAFFIC_TABLE_ID:-}" ]]; then
    python3 src/sync_openviking_traffic.py
  else
    echo "⚠️ Skip traffic table sync: missing LARK_OPENVIKING_TRAFFIC_TABLE_ID"
  fi

  if [[ -n "${LARK_BASE_TOKEN:-}" && -n "${LARK_OPENVIKING_FUNNEL_TABLE_ID:-}" ]]; then
    python3 src/sync_openviking_funnel.py
  else
    echo "⚠️ Skip funnel sync: missing LARK_OPENVIKING_FUNNEL_TABLE_ID"
  fi
else
  echo "⚠️ GitHub traffic export failed"
fi

python3 src/check_snapshot_integrity.py

echo "✅ GitHub Actions run completed"
