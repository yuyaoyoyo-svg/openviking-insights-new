# OpenViking 项目洞察 - 快速操作手册

## 📋 目录

1. [第一次使用](#第一次使用)
2. [日常操作](#日常操作)
3. [查看数据](#查看数据)
4. [故障排除](#故障排除)
5. [高级配置](#高级配置)

---

## 🚀 第一次使用

### 步骤 1: 获取 GitHub Token

**⚠️ 这是最重要的步骤，没有 Token 无法采集数据！**

1. 打开浏览器，访问: https://github.com/settings/tokens
2. 点击右上角 "Generate new token (classic)" 按钮
3. 填写 Note: "OpenViking Insights"
4. 选择 Expiration: "No expiration" (或选择较长的过期时间)
5. 勾选权限:
   - ☑️ `public_repo` (访问公开仓库)
   - ☑️ `read:org` (读取组织信息，可选)
6. 滚动到页面底部，点击 "Generate token"
7. **立即复制 Token** (页面只会显示一次！)
   - Token 格式: `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

### 步骤 2: 验证 Token 是否有效

打开终端，运行:

```bash
# 将 ghp_xxxxx 替换为你复制的 Token
curl -H "Authorization: Bearer ghp_xxxxx" \
  https://api.github.com/user
```

如果看到 JSON 格式的用户信息，说明 Token 有效！

### 步骤 3: 运行数据采集

```bash
# 进入项目目录
cd /Users/bytedance/openviking_insights

# 方式 1: 使用运行脚本（推荐）
./run_local.sh ghp_你的token

# 方式 2: 直接运行
export GITHUB_TOKEN="ghp_你的token"
python3 main.py
```

### 步骤 4: 查看结果

1. **查看飞书多维表格**:
   - 打开由 `.env` 中 `LARK_BASE_TOKEN` 对应的飞书链接
   - 查看采集到的项目数据

2. **查看本地数据文件**:
   ```bash
   ls -lh data/
   # 查看 JSON 数据
   cat data/insights_2026-04-15.json | jq '.projects[0]'
   ```

---

## 🔄 日常操作

### 每日查看数据

1. 打开飞书多维表格看板
2. 查看 OpenViking 及竞品项目的数据变化
3. 查看三层校准分析结果:
   - 自我基准: 近7天 vs 前7天
   - 同类对标: 分位数排名
   - 分类阈值: 项目阶段评估

### 手动采集数据

如果需要立即采集最新数据:

```bash
cd /Users/bytedance/openviking_insights
export GITHUB_TOKEN="ghp_你的token"
python3 main.py
```

### 添加新的监控项目

编辑 `config/projects.json`:

```json
{
  "projects": [
    {
      "name": "新项目",
      "owner": "github用户名",
      "repo": "仓库名",
      "type": "peer"
    }
  ]
}
```

然后重新运行采集。

---

## 📊 查看数据

### 飞书多维表格

**访问地址**: 由 `.env` 中的 `LARK_BASE_TOKEN` 决定

**包含的数据字段**:
- 项目名称、项目标识
- Stars、Forks、Watchers
- Open Issues、Closed Issues
- Open PRs、Closed PRs
- Contributors、Recent Commits
- 社区活力评分、外部影响力评分
- 自我基准对比、同类对标分位数
- 项目阶段阈值、数据来源

### 本地数据文件

```bash
# 查看数据文件列表
ls -lh data/

# 查看原始采集数据
cat data/insights_YYYY-MM-DD.json

# 查看校准后数据
cat data/calibrated_YYYY-MM-DD.json

# 使用 jq 格式化查看
jq '.' data/insights_YYYY-MM-DD.json | less
```

---

## 🔧 故障排除

### 问题 1: GitHub Token 失效 (401 错误)

**症状**:
```
Error: 401 Unauthorized
{"message":"Bad credentials"}
```

**解决**:
1. 重新创建 GitHub Token (见 "第一次使用" 部分)
2. 使用新 Token 运行采集

### 问题 2: 速率限制 (403 错误)

**症状**:
```
Error: 403 Forbidden
{"message":"API rate limit exceeded"}
```

**解决**:
- 等待 1 小时后重试
- 使用已认证的 Token（已认证用户每小时 5000 次请求）
- 减少同时采集的项目数量

### 问题 3: 项目不存在 (404 错误)

**症状**:
```
Error: 404 Not Found
```

**解决**:
- 检查 `config/projects.json` 中的项目配置
- 确认 owner 和 repo 名称正确
- 确认项目是公开的

### 问题 4: 飞书同步失败

**症状**:
```
飞书同步失败: API call failed
```

**解决**:
1. 检查飞书 CLI 是否已登录:
   ```bash
   lark-cli auth status
   ```

2. 如未登录，重新授权:
   ```bash
   lark-cli auth login --domain base
   ```

3. 检查 Base Token 和 Table ID 是否正确

### 问题 5: 依赖安装失败

**症状**:
```
pip install 失败
```

**解决**:
```bash
# 更新 pip
pip install --upgrade pip

# 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

---

## ⚙️ 高级配置

### 自定义采集频率

编辑 `.github/workflows/daily-insights.yml`:

```yaml
on:
  schedule:
    # 每天 UTC 2:00 运行 (北京时间 10:00)
    - cron: '0 2 * * *'
    
    # 其他示例:
    # 每小时: '0 * * * *'
    # 每周一: '0 2 * * 1'
```

### 修改评分算法

编辑 `src/calibration.py` 中的评分权重:

```python
# 社区活力评分权重
vitality_weights = {
    'commits': 0.4,      # 40%
    'issues': 0.3,       # 30%
    'prs': 0.3          # 30%
}

# 外部影响力评分权重
influence_weights = {
    'stars': 0.5,        # 50%
    'forks': 0.3,        # 30%
    'watchers': 0.2      # 20%
}
```

### 添加自定义字段

编辑 `src/lark_sync.py` 中的字段映射:

```python
field_mapping = {
    # 添加你的自定义字段
    '你的字段名': {
        'source': 'metrics.xxx',
        'type': 'text'
    }
}
```

---

## 📞 获取帮助

如果遇到问题:

1. 查看详细文档: `README.md`
2. 查看 Token 指南: `docs/GITHUB_TOKEN_GUIDE.md`
3. 检查故障排除部分（本文档上一节）
4. 查看日志输出中的错误信息
5. 提交 GitHub Issue 寻求帮助

---

## 🎊 恭喜！

你已经完成了所有配置！现在你可以:

- ✅ 自动采集 GitHub 项目数据
- ✅ 进行三层校准分析
- ✅ 同步数据到飞书多维表格
- ✅ 每日自动生成项目洞察报告

**开始享受自动化的便利吧！** 🚀
