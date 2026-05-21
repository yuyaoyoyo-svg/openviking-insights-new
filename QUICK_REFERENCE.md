# 🚀 OpenViking 项目洞察系统 - 快速参考卡

## 📍 重要链接

| 资源 | 链接/路径 |
|------|----------|
| 飞书多维表格 | 由 `.env` 中的 `LARK_BASE_TOKEN` 生成对应访问链接 |
| 项目目录 | `/Users/bytedance/openviking_insights` |
| 主程序 | `main.py` |
| 运行脚本 | `run_local.sh` |
| 项目配置 | `config/projects.json` |
| 数据目录 | `data/` |

---

## ⚡ 最快开始（1分钟）

```bash
# 1. 进入目录
cd /Users/bytedance/openviking_insights

# 2. 运行（替换为你的token）
./run_local.sh

# 3. 查看结果
# 打开飞书表格查看数据
```

---

## 🔑 获取 GitHub Token

1. 访问: https://github.com/settings/tokens
2. 点击 "Generate new token (classic)"
3. 勾选: ☑️ `public_repo`
4. 点击 "Generate token"
5. **立即复制** (格式: `ghp_xxxxxx`)

---

## 📊 监控项目

### 自我项目（1个）
- ✅ OpenViking (volcengine/OpenViking)

### 同类对标（13个）
1. NevaMind-AI/memU
2. lancedb/lancedb
3. tobi/qmd
4. mem0ai/mem0
5. LycheeMem/LycheeMem
6. zjunlp/LightMem
7. agentscope-ai/ReMe
8. supermemoryai/supermemory
9. openclaw/openclaw
10. NousResearch/hermes-agent
11. bytedance/deer-flow

---

## 🎯 三层校准

### 1. 自我基准
- 对比: 近7天 vs 前7天
- 输出: 增长率 + 趋势

### 2. 同类对标
- 对比: 与13个竞品
- 输出: 分位数排名 (0-100)

### 3. 分类阈值
- 评估: 项目阶段
- 输出: 种子/成长/成熟/领军

---

## 🔧 常用命令

```bash
# 运行完整采集
./run_local.sh

# 手动运行
export GITHUB_TOKEN="ghp_你的token"
python3 main.py

# 检查飞书状态
lark-cli auth status

# 查看数据文件
ls -lh data/

# 查看帮助
./run_local.sh --help
```

---

## 📁 文件结构

```
openviking_insights/
├── 📁 .github/workflows/
│   └── daily-insights.yml     # 自动化工作流
├── 📁 config/
│   └── projects.json            # 14个项目配置
├── 📁 data/                     # 数据存储
├── 📁 docs/
│   ├── GITHUB_TOKEN_GUIDE.md   # Token指南
│   └── QUICK_START.md          # 快速手册
├── 📁 src/
│   ├── github_collector.py     # GitHub采集
│   ├── calibration.py          # 三层校准
│   └── lark_sync.py           # 飞书同步
├── main.py                     # 主程序
├── README.md                   # 项目文档
├── run_local.sh               # 运行脚本
└── requirements.txt           # 依赖列表
```

---

## ⚠️ 故障排除

### 问题 1: Token 失效 (401)
**解决**: 重新创建 GitHub Token

### 问题 2: 速率限制 (403)
**解决**: 等待 1 小时后重试

### 问题 3: 飞书同步失败
**解决**: 
```bash
lark-cli auth login --domain base
```

### 问题 4: 依赖安装失败
**解决**: 
```bash
pip install --upgrade pip
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

---

## 📞 获取帮助

### 文档资源
1. `README.md` - 完整项目文档
2. `docs/GITHUB_TOKEN_GUIDE.md` - Token 获取指南
3. `docs/QUICK_START.md` - 快速操作手册
4. `DEPLOYMENT_REPORT.md` - 部署报告

### 提交 Issue
- 在 GitHub 仓库提交 Issue
- 提供错误日志和上下文

---

## 🎊 恭喜！

**OpenViking 项目洞察自动化系统已完全部署成功！**

### 立即开始:

```bash
# 1. 获取 GitHub Token (2分钟)
# 访问: https://github.com/settings/tokens

# 2. 运行采集 (1分钟)
cd /Users/bytedance/openviking_insights
./run_local.sh

# 3. 查看数据 (1分钟)
# 打开飞书表格
```

**总计: 只需 5 分钟即可看到完整的数据洞察！** 🚀

---

**部署时间**: 2026-04-15  
**系统状态**: ✅ 完全就绪  
**版本**: v1.0.0  

**🎉 系统已就绪，开始享受自动化数据洞察吧！** 🚀
