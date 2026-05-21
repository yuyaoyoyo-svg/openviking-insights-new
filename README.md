# OpenViking 项目洞察自动化系统

自动化采集 GitHub 开源项目数据，进行三层校准分析（自我基准、同类对标、分类阈值），并同步到飞书多维表格。

## 📊 今日数据（2026-04-15）

### OpenViking 核心指标
- ⭐ **Stars**: 22,321
- 🍴 **Forks**: 1,632
- 📋 **Open Issues**: 161
- 👁️ **Watchers**: 22,321
- 💪 **社区活力评分**: 100/100
- 🌍 **外部影响力评分**: 100/100

### 同类对标排名（12个项目）
| 排名 | 项目 | Stars | 状态 |
|------|------|-------|------|
| 🥇 1 | openclaw | 357,857 | 竞品 |
| 🥈 2 | hermes-agent | 88,014 | 竞品 |
| 🥉 3 | deer-flow | 61,699 | 竞品 |
| 4 | mem0 | 53,113 | 竞品 |
| **5** | **OpenViking** | **22,321** | **✓ 你的项目** |

### 关键洞察
- 🏆 **项目阶段**: 领军期（Stars > 5000）
- 📊 **百分位数**: 66.7%（超过66.7%的竞品）
- 📈 **排名**: 第 5 名 / 12 个项目
- 🎯 **评估**: 中等水平（Top 50%）

---

## 🚀 快速开始

### GitHub Actions
- GitHub Actions 版本使用仓库 `Secrets` 驱动，不需要提交 `.env`、日志或运行产物
- 说明文档见 `docs/GITHUB_ACTIONS_SETUP.md`

### 当前运行策略
- 当前阶段仍以**本地日跑**为主，继续使用 `.env + lark-cli + gh auth`
- GitHub Actions 代码已经准备好，但暂时只做“可切换能力”保留
- 后续继任接手时，只需要按本 README 里的 GitHub 配置步骤补齐 `Secrets` 和权限，即可迁移到云端定时运行

### 1. 环境要求
- Python 3.8+
- GitHub Token (Fine-grained)
- 已安装并登录的 `lark-cli`
- `.env` 中的 `LARK_BASE_TOKEN` 和 `LARK_TABLE_ID`

### 2. 运行采集
```bash
cd openviking_insights

# 1. 配置 .env
# GITHUB_TOKEN=github_pat_xxx
# LARK_BASE_TOKEN=...

# 2. 确认飞书 CLI 已登录
lark-cli auth status

# 3. 首次创建新的比较表
python3 src/setup_compare_table.py

# 4. 执行全流程
./run_daily.sh
```

`./run_daily.sh` 当前包含 5 段：
- GitHub 快照采集
- 快照表同步
- OSSInsight 趋势同步
- OpenViking Traffic / 漏斗同步
- 当日报告输出

### 3. 查看数据
- **飞书表格**: 使用 `.env` 中的 `LARK_BASE_TOKEN` 访问对应链接
- **本地数据**: `data/insights_YYYY-MM-DD.json`

---

## GitHub 配置清单

这部分是给后续迁移到 GitHub Actions 时使用的。当前本地运行不依赖这些配置。

### 1. 需要在 GitHub 仓库里配置的 Secrets

进入仓库：

`Settings -> Secrets and variables -> Actions`

至少配置以下 `Secrets`：

- `OV_GITHUB_TOKEN`
  - 用于 `main.py` 采集 GitHub 基础数据
  - 也用于 `gh api` 导出 OpenViking traffic
- `LARK_APP_ID`
- `LARK_APP_SECRET`
- `LARK_BASE_TOKEN`
- `LARK_TABLE_ID`

可选 `Secrets`：

- `LARK_TRENDS_TABLE_ID`
  - 用于 OSSInsight 趋势表
- `LARK_OPENVIKING_TRAFFIC_TABLE_ID`
  - 用于 OpenViking Traffic(日) 表
- `LARK_OPENVIKING_FUNNEL_TABLE_ID`
  - 用于 OpenViking 漏斗(日) 表

说明：

- 如果只配了最小集合，主快照采集和主表同步可以跑
- 没配可选表 ID 时，对应步骤会自动跳过，不会影响主流程

### 2. GitHub Token 需要具备的能力

- 能读取 `config/projects.json` 里列出的目标仓库
- 能访问 `volcengine/OpenViking` 的 traffic 接口
- 建议使用单独的 PAT，不要复用个人日常 token

### 3. 飞书 / Lark 侧前置条件

- 飞书 App 已创建
- App 的 `App ID / App Secret` 已准备好
- App 已被加入目标 Base
- App 对目标表具有可读写权限
- `LARK_BASE_TOKEN`、各张表的 `table_id` 已确认无误

### 4. GitHub Actions 启用步骤

当继任准备切换到 GitHub Actions 时，按这个顺序做：

1. 把本仓库推到 GitHub
2. 在仓库 `Actions Secrets` 中填好上面的变量
3. 确认飞书 App 权限已经开通到对应 Base / table
4. 打开工作流文件：
   - [daily-insights.yml](file:///Users/bytedance/openviking_insights/.github/workflows/daily-insights.yml)
5. 在 GitHub Actions 页面手动执行一次 `workflow_dispatch`
6. 检查 Actions 日志、飞书表和 `artifacts`
7. 手动验证没问题后，再依赖定时触发

### 5. GitHub Actions 运行入口

- 工作流文件：
  - [daily-insights.yml](file:///Users/bytedance/openviking_insights/.github/workflows/daily-insights.yml)
- CI 入口脚本：
  - [run_github_actions.sh](file:///Users/bytedance/openviking_insights/run_github_actions.sh)
- GitHub Actions 专用说明：
  - [GITHUB_ACTIONS_SETUP.md](file:///Users/bytedance/openviking_insights/docs/GITHUB_ACTIONS_SETUP.md)

---

## 继任交接

### 需要打包给继任的内容

建议把下面这些直接打包成一个交接包：

- 代码仓库本身
  - 包含 `src/`、`config/`、`.github/workflows/`、文档
- 运行说明
  - 本 README
  - [QUICK_START.md](file:///Users/bytedance/openviking_insights/docs/QUICK_START.md)
  - [GITHUB_ACTIONS_SETUP.md](file:///Users/bytedance/openviking_insights/docs/GITHUB_ACTIONS_SETUP.md)
- 本地配置模板
  - [.env.example](file:///Users/bytedance/openviking_insights/.env.example)
- 表结构与流程脚本
  - [setup_compare_table.py](file:///Users/bytedance/openviking_insights/src/setup_compare_table.py)
  - [setup_trends_table.py](file:///Users/bytedance/openviking_insights/src/setup_trends_table.py)
  - [setup_openviking_traffic_table.py](file:///Users/bytedance/openviking_insights/src/setup_openviking_traffic_table.py)
  - [setup_openviking_funnel_table.py](file:///Users/bytedance/openviking_insights/src/setup_openviking_funnel_table.py)
- 修复/运维脚本
  - [check_snapshot_integrity.py](file:///Users/bytedance/openviking_insights/src/check_snapshot_integrity.py)
  - [dedupe_snapshot_records.py](file:///Users/bytedance/openviking_insights/src/dedupe_snapshot_records.py)
  - [fix_star_history_from_stargazers.py](file:///Users/bytedance/openviking_insights/src/fix_star_history_from_stargazers.py)

### 不要放进 GitHub 仓库的内容

这些内容应该继续留在本地或通过安全渠道单独交接：

- `.env`
- 任意真实 token / secret / app secret
- 本地 `logs/`
- 本地 `data/insights_*.json`
- 本地 `data/github-traffic/`
- 本地 `plist`
- 任意包含内部链接、账号状态或调试痕迹的临时文件

### 建议单独安全交接的敏感信息

这些不要写进仓库，建议通过密码管理器、企业安全文档或一对一安全渠道交接：

- GitHub PAT 的创建方式与权限范围
- `LARK_APP_ID`
- `LARK_APP_SECRET`
- `LARK_BASE_TOKEN`
- `LARK_TABLE_ID`
- `LARK_TRENDS_TABLE_ID`
- `LARK_OPENVIKING_TRAFFIC_TABLE_ID`
- `LARK_OPENVIKING_FUNNEL_TABLE_ID`
- 飞书 App 所属团队、管理员、权限申请路径

### 交接建议顺序

1. 先让继任在本机按 `.env` 跑通一次本地流程
2. 再带她确认飞书表、traffic 表、funnel 表分别对应哪几个 table ID
3. 最后再去 GitHub 上配置 `Secrets`，手动触发一次 Actions
4. Actions 验证通过后，再正式把日跑从本地迁到 GitHub

---

## 📁 项目结构

```
openviking_insights/
├── 📁 config/
│   └── projects.json              # 14个项目配置
├── 📁 data/                       # 数据存储
│   ├── insights_2026-04-15.json   # 今日采集数据
│   └── calibrated_2026-04-15.json # 校准分析结果
├── 📁 docs/                       # 文档
│   ├── GITHUB_TOKEN_GUIDE.md     # Token获取指南
│   └── QUICK_START.md            # 快速手册
├── 📁 src/                        # 核心模块
│   ├── github_collector.py       # GitHub数据采集
│   ├── calibration.py            # 三层校准计算
│   ├── lark_sync.py              # 飞书同步
│   ├── setup_compare_table.py    # 新比较表初始化
│   └── sync_to_lark_api.py       # 基于 lark-cli 的飞书同步
├── 📁 .github/workflows/          # 自动化部署
│   └── daily-insights.yml        # 每日定时任务
├── main.py                        # 主程序
├── run_local.sh                   # 运行脚本
└── README.md                      # 本文件
```

---

## 📊 三层校准说明

### 1. 自我基准（Self Benchmark）
- 对比：近7天 vs 前7天
- 输出：增长率 + 趋势分析
- 用途：了解项目自身成长速度

### 2. 同类对标（Peer Benchmark）
- 对比：与13个竞品项目
- 输出：分位数排名（0-100%）
- 用途：了解竞争地位

### 3. 分类阈值（Category Threshold）
- 评估：项目发展阶段
- 输出：种子期/成长期/成熟期/领军期
- 用途：了解项目成熟度

---

## 🔧 常用命令

```bash
# 运行完整采集
./run_daily.sh

# 首次创建或重建比较表
python3 src/setup_compare_table.py

# 仅采集 GitHub 数据
python3 main.py

# 导出 OpenViking Traffic 原始数据（依赖 gh auth login）
bash src/export_github_traffic.sh

# 初始化 OpenViking Traffic/漏斗表
python3 src/setup_openviking_traffic_table.py
python3 src/setup_openviking_funnel_table.py

# 同步 OpenViking Traffic 与漏斗数据
python3 src/sync_openviking_traffic.py
python3 src/sync_openviking_funnel.py

# 仅同步到飞书
python3 src/sync_to_lark_api.py

# 检查飞书 CLI 登录状态
lark-cli auth status

# 首次登录飞书 CLI
lark-cli auth login --recommend

# 查看数据
ls -lh data/
```

---

## ⚠️ 注意事项

### GitHub Token
- **使用 Fine-grained Personal Access Token**
- 需要 `contents:read`, `issues:read`, `metadata:read` 权限
- 添加 `volcengine/OpenViking` 仓库访问权限

### 飞书配置
- Base Token: 存放于 `.env` 的 `LARK_BASE_TOKEN`
- Table ID: 由 `python3 src/setup_compare_table.py` 创建后自动回写到 `.env`
- 同步依赖当前机器上已登录的 `lark-cli` 用户身份
- 如需重新登录，执行 `lark-cli auth login --recommend`

### 新比较表字段
- 仓库名称、仓库全名、生态位层级、项目类型、日期
- Stars、Forks、Watchers、Open Issues、Open PRs、Contributors
- 综合健康度、社区互动总量、外部吸引力指数(log+加权)、近期增长动力
  - 外部吸引力指数(log+加权)口径: log1p(Stars) + 2*log1p(Forks)（先对数压缩再加权，不纳入 Watchers）
  - 近期增长动力口径: 1*Stars日增量 + 2*Forks日增量 + 3*Contributors日增量
- 对比基准日期、采集间隔天数、Stars/Forks/Watchers/Open Issues/Open PRs/Contributors 日增量
  - 默认以前一天的 `insights_YYYY-MM-DD.json` 为基准；仅在前一天快照缺失时，回退到最近一次历史快照
- 访客→Star转化率、访客→克隆者转化率（依赖 GitHub traffic，当前默认显示为待补）
- 贡献者增长/Star增长比（Stars日增量 < 10 时显示 N/A，避免小分母放大）
- 贡献者总数/Star总数（更稳定的长期比值）
- 社区活力评分、外部影响力评分、语言、最后推送时间、GitHub链接

### OpenViking Traffic & 漏斗
- `src/export_github_traffic.sh`：通过 `gh api` 导出 OpenViking 的 views/clones/popular paths/referrers，并生成 `traffic_snapshot.json`
  - 本地默认优先使用 `gh auth login` 的 keyring 登录态
  - 在 GitHub Actions 中会改用 `GH_TOKEN / GITHUB_TOKEN`
- `src/setup_openviking_traffic_table.py` / `src/setup_openviking_funnel_table.py`：创建并维护两张飞书表，表 ID 自动写入 `.env`
- `src/sync_openviking_traffic.py`：将 snapshot 展开为按日 traffic 记录并 upsert 到 `OpenViking Traffic(日)`
- `src/sync_openviking_funnel.py`：将 traffic 与本地 `insights_YYYY-MM-DD.json` 融合，计算并 upsert 到 `OpenViking 漏斗(日)`
- 说明：漏斗表中的 `Stars日增量` / `Contributors日增量` 依赖同日 insights 快照；若历史日期缺少对应快照，这两列会暂时为空
- 两张表都会写入 `数据新鲜度说明`，明确提示 GitHub traffic 通常按 T+1 更新

---

## 📞 支持

如有问题：
1. 查看 `docs/QUICK_START.md` 故障排除
2. 检查日志输出
3. 联系项目维护者

---

**🎉 系统已完全就绪！开始享受自动化数据洞察吧！** 🚀

---

*最后更新: 2026-04-15*  
*版本: v1.0.0*
