#!/bin/bash
# OpenViking 项目洞察 - 每日数据更新脚本
# 用法: ./run_daily.sh

set -e

echo "============================================"
echo "OpenViking 项目洞察 - 每日数据更新"
echo "============================================"
echo ""

load_env_file() {
    local env_file="$1"
    local line key value

    while IFS= read -r line || [ -n "$line" ]; do
        [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
        line="${line#export }"
        [[ "$line" != *=* ]] && continue

        key="${line%%=*}"
        value="${line#*=}"
        key="${key//[[:space:]]/}"

        if [[ ! "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
            echo "❌ 错误: .env 中存在非法变量名: $key"
            return 1
        fi

        if [[ ${#value} -ge 2 ]]; then
            if [[ "${value:0:1}" == "\"" && "${value: -1}" == "\"" ]]; then
                value="${value:1:-1}"
            elif [[ "${value:0:1}" == "'" && "${value: -1}" == "'" ]]; then
                value="${value:1:-1}"
            fi
        fi

        printf -v "$key" '%s' "$value"
        export "$key"
    done < "$env_file"
}

# 设置工作目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 加载 .env
ENV_FILE="$SCRIPT_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ 错误: 未找到 .env 文件"
    echo "请在项目根目录创建 .env 并填写 GITHUB_TOKEN 等配置"
    exit 1
fi

load_env_file "$ENV_FILE" || exit 1

# 检查配置
if [ -z "$GITHUB_TOKEN" ]; then
    echo "❌ 错误: .env 中未设置 GITHUB_TOKEN"
    exit 1
fi

# 设置环境变量
export GITHUB_TOKEN

echo "✅ 配置检查完成"
echo ""

# 步骤1: 数据采集
echo "📊 步骤 1/5: 采集 GitHub 数据..."
python3 main.py
if [ $? -ne 0 ]; then
    echo "❌ 数据采集失败"
    exit 1
fi
echo "✅ 数据采集完成"
echo ""

# 步骤2: 同步到飞书
echo "☁️ 步骤 2/5: 同步到飞书多维表格..."
python3 src/sync_to_lark_api.py
if [ $? -ne 0 ]; then
    echo "⚠️ 飞书同步可能遇到问题，但数据采集已保存"
fi
echo "✅ 飞书同步完成"
echo ""

# 步骤3: 同步 OSSInsight 趋势
echo "📈 步骤 3/5: 同步 OSSInsight 趋势..."
python3 src/setup_trends_table.py || echo "⚠️ 趋势表初始化失败，跳过"
python3 src/sync_ossinsight_trends.py || echo "⚠️ OSSInsight 趋势同步失败，跳过"
echo "✅ OSSInsight 趋势同步完成"
echo ""

# 步骤4: 导出并同步 OpenViking Traffic / 漏斗
echo "🚦 步骤 4/5: 同步 OpenViking Traffic / 漏斗..."
if bash src/export_github_traffic.sh; then
    python3 src/setup_openviking_traffic_table.py || echo "⚠️ OpenViking Traffic(日) 表初始化失败，跳过"
    python3 src/sync_openviking_traffic.py || echo "⚠️ OpenViking Traffic(日) 同步失败，跳过"
    python3 src/setup_openviking_funnel_table.py || echo "⚠️ OpenViking 漏斗(日) 表初始化失败，跳过"
    python3 src/sync_openviking_funnel.py || echo "⚠️ OpenViking 漏斗(日) 同步失败，跳过"
else
    echo "⚠️ GitHub Traffic 导出失败，跳过 OpenViking Traffic / 漏斗同步"
fi
echo "✅ OpenViking Traffic / 漏斗步骤结束"
echo ""

# 步骤5: 数据巡检
echo "🔎 步骤 5/6: 巡检快照完整性..."
python3 src/check_snapshot_integrity.py "$(date +%Y-%m-%d)" || echo "⚠️ 巡检发现潜在数据问题，请检查上方 Findings"
echo "✅ 数据巡检完成"
echo ""

# 步骤6: 生成报告
echo "📋 步骤 6/6: 生成今日报告..."
python3 -c "
import json
from datetime import datetime

with open('data/insights_$(date +%Y-%m-%d).json', 'r') as f:
    data = json.load(f)

print('\\n📊 今日数据概览')
print('=' * 60)
print(f'采集项目数: {len(data[\"projects\"])}')
print(f'采集时间: {datetime.now().strftime(\"%Y-%m-%d %H:%M:%S\")}')
print('\\n🏆 排名 Top 5:')

sorted_projects = sorted(data['projects'], key=lambda x: x.get('stars', 0), reverse=True)[:5]
for i, p in enumerate(sorted_projects, 1):
    marker = '👈 你的项目' if p.get('type') == 'self' else ''
    print(f'  {i}. {p[\"name\"]:15s} ⭐ {p.get(\"stars\", 0):,} {marker}')

print('=' * 60)
" 2>/dev/null || echo "✅ 数据已保存"

echo ""
echo "============================================"
echo "✅ 每日更新完成！"
echo "============================================"
echo ""
echo "📁 数据文件:"
echo "  - data/insights_$(date +%Y-%m-%d).json"
echo "  - data/calibrated_$(date +%Y-%m-%d).json"
echo ""
if [ -n "$LARK_BASE_TOKEN" ]; then
    echo "📊 飞书表格:"
    echo "  https://bytedance.larkoffice.com/base/$LARK_BASE_TOKEN"
    echo ""
fi
