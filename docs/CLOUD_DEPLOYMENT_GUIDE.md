# 云服务器部署指南

**OpenViking 项目洞察**

---

## 📋 可行性确认

✅ **当前项目在云服务器上部署完全可行，甚至比 GitHub Actions 更可控**

---

## 🎯 云服务器部署 vs GitHub Actions 对比

| 维度 | GitHub Actions | 云服务器 |
|------|----------------|----------|
| 网络访问 | 外网访问稳定，但可能受 GitHub 限流 | 完全可控，适合内网网络或特定环境 |
| 环境配置 | 每次运行重新构建 | 一次配置，长期使用 |
| 可靠性 | 依赖 GitHub 服务状态 | 只依赖你自己的服务器 |
| 成本 | 免费（公开仓库）或付费（私有仓库） | 取决于你的服务器成本 |
| 复杂度 | 较低，但需要正确配置 Secrets | 中等，需要熟悉 Linux 环境 |
| 可定制性 | 有，但受限于 Actions 运行环境 | 极高，完全自由定制 |

---

## 🚀 云服务器部署步骤

### 前置准备

你需要：
1. 一台 Linux 云服务器（推荐 Ubuntu 20.04+，2核2G 足够）
2. 服务器上已经安装了：
   - Python 3.8+
   - git
   - curl
   - Node.js 16+（用于安装 lark-cli）
3. 飞书 App 的权限（建议用 `bot` 身份）

### 步骤 1: 拉取项目代码

```bash
# 在服务器上找一个合适的目录
cd ~

# 克隆项目（如果是私有仓库，需要先配置 git 认证）
git clone <你的项目仓库地址>
cd openviking_insights
```

### 步骤 2: 安装依赖

```bash
# 安装 Python 依赖
pip3 install -r requirements.txt

# 安装 Node.js（如果没有）
# Ubuntu/Debian
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# 或者用 nvm（更灵活）
# curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.5/install.sh | bash
# nvm install 18
# nvm use 18

# 安装 gh CLI（用于 GitHub traffic 导出）
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install gh

# 安装 lark-cli（官方推荐方式）
npm install -g @larksuite/cli
```

### 步骤 3: 配置环境变量

```bash
# 复制 .env.example 为 .env
cp .env.example .env

# 编辑 .env，填入你的配置
nano .env
```

你需要配置的关键项：
```bash
# GitHub Token（建议用有 repo 权限的 Personal Access Token）
GITHUB_TOKEN="<你的 GitHub Token>"

# 飞书配置（建议用 bot 身份）
LARK_APP_ID="<你的飞书 App ID>"
LARK_APP_SECRET="<你的飞书 App Secret>"
LARK_BASE_TOKEN="<你的飞书 Base Token>"
LARK_TABLE_ID="<你的主表 ID>"

# 可选配置
LARK_TRENDS_TABLE_ID="<趋势表 ID>"
LARK_OPENVIKING_TRAFFIC_TABLE_ID="<Traffic表 ID>"
LARK_OPENVIKING_FUNNEL_TABLE_ID="<Funnel表 ID>"
```

### 步骤 4: 认证登录

```bash
# 用 GitHub token 登录 gh CLI
gh auth login --with-token <<< "$GITHUB_TOKEN"

# 用飞书 bot 身份登录 lark-cli
lark-cli auth login --app-id "$LARK_APP_ID" --app-secret "$LARK_APP_SECRET"
```

### 步骤 5: 测试运行

```bash
# 先手工运行一次，确认一切正常
bash run_daily.sh
```

### 步骤 6: 配置定时任务（用 cron）

```bash
# 编辑 crontab
crontab -e
```

添加一行，比如每天晚上 22:00 运行：
```bash
0 22 * * * cd /home/你的用户名/openviking_insights && bash run_daily.sh >> logs/cron_run_daily.log 2>&1
```

**说明**：
- 调整 `0 22 * * *` 为你想要的运行时间
- `/home/你的用户名/openviking_insights` 换成你实际的项目路径
- `logs/cron_run_daily.log` 换成你想要的日志文件路径

### 步骤 7: 验证定时任务

```bash
# 查看 crontab 是否配置成功
crontab -l

# 查看 cron 日志（Ubuntu/Debian）
sudo tail -f /var/log/syslog
```

---

## 📝 注意事项

### 必须用 bot 身份

在云服务器上，不要用用户身份，建议全程用：
- GitHub Personal Access Token
- 飞书 App bot 身份

这样认证不会过期，长期稳定运行。

### 日志轮转

建议配置日志轮转，避免日志文件越来越大：
```bash
# 创建 logrotate 配置
sudo nano /etc/logrotate.d/openviking-insights
```

填入：
```
/home/你的用户名/openviking_insights/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644
}
```

### 数据备份

建议定期备份数据目录：
```bash
# 添加到 crontab，每天凌晨 3:00 备份
0 3 * * * tar -zcf /home/你的用户名/backups/openviking_insights_backup_$(date +\%Y\%m\%d).tar.gz -C /home/你的用户名/openviking_insights data
```

---

## 🤝 与本地运行的区别

| 本地运行 | 云服务器运行 |
|----------|--------------|
| 依赖你的电脑开机 | 7x24 稳定运行 |
| 可以用 GUI 工具调试 | 只能用命令行 |
| 适合临时修复和测试 | 适合长期自动化运行 |
| 可以用你的个人 GitHub 登录态 | 必须用长期 token 和 bot 身份 |

---

## 🎉 总结

云服务器部署是一个非常稳妥的方案，适合：
- 需要内网访问的环境
- 对可靠性要求高的场景
- 不想依赖外部服务的团队

按照这个指南，你可以在 15-30 分钟内完成部署。
