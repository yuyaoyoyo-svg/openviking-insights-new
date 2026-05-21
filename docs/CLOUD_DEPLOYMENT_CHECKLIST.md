# 云服务器部署 - 极简检查清单

---

## ✅ 你需要准备的（必须）

| 项目 | 说明 |
|------|------|
| **一台 Linux 云服务器** | 推荐 Ubuntu 20.04+，2核2G 足够 |
| **GitHub Personal Access Token** | 要有 `repo` 权限，用于 traffic 接口 |
| **飞书 App** | 要有 `bot` 身份，已加入目标 Base |
| **飞书 Base/表权限** | `bot` 对目标表要有读写权限 |
| **云服务器 SSH 权限** | 你要能登录到这台服务器 |

---

## ❌ 你不需要准备的

| 项目 | 原因 |
|------|------|
| **新机器** | 现有 Linux 云服务器就能用 |
| **新代码** | 当前项目已经适配，无需改动 |
| **复杂 CI/CD** | 简单的 `cron` 定时任务就够了 |
| **持续维护** | 一次配置，长期稳定 |

---

## 🚀 快速部署 6 步

### 1. 拉代码
```bash
cd ~
git clone <你的项目仓库地址>
cd openviking_insights
```

### 2. 装依赖
```bash
pip3 install -r requirements.txt

# 安装 Node.js（如果没有）
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# 安装 gh CLI
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install gh

# 安装 lark-cli（官方推荐方式）
npm install -g @larksuite/cli
```

### 3. 配环境
```bash
cp .env.example .env
nano .env  # 填入你的配置
```

### 4. 登账号
```bash
# GitHub
gh auth login --with-token <<< "$GITHUB_TOKEN"

# 飞书
lark-cli auth login --app-id "$LARK_APP_ID" --app-secret "$LARK_APP_SECRET"
```

### 5. 试运行
```bash
bash run_daily.sh
```

### 6. 加定时
```bash
crontab -e
# 添加一行（每天 22:00 运行）
0 22 * * * cd /home/你的用户名/openviking_insights && bash run_daily.sh >> logs/cron_run_daily.log 2>&1
```

---

## 📊 部署成功检查项

- [ ] 云服务器 SSH 登录成功
- [ ] `python3 --version` ≥ 3.8
- [ ] `gh --version` 正常显示
- [ ] `lark-cli --version` 正常显示
- [ ] `.env` 已配置并填写
- [ ] 手工运行 `bash run_daily.sh` 成功
- [ ] `cron` 定时任务已添加
- [ ] 检查日志目录正常

---

## 🎯 推荐配置

| 配置项 | 推荐值 |
|--------|--------|
| 操作系统 | Ubuntu 20.04+ |
| CPU | 2 核 |
| 内存 | 2 GB |
| 磁盘 | 20 GB（足够存历史数据） |
| 运行时间 | 每天晚上 22:00 一次 |

---

## 📖 详细文档

如果需要更详细的指导，请查看：
- [CLOUD_DEPLOYMENT_GUIDE.md](./CLOUD_DEPLOYMENT_GUIDE.md)
- [README.md](../README.md)
