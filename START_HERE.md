# 🚀 OpenViking 项目洞察系统 - 启动指南

## ⚡ 5分钟快速启动

### 第1步: 获取 GitHub Token (2分钟)

1. 打开: https://github.com/settings/tokens
2. 点击: "Generate new token (classic)"
3. 填写:
   - Note: `OpenViking Insights`
   - Expiration: `No expiration`
4. 勾选: ☑️ `public_repo`
5. 点击: "Generate token"
6. **复制 Token** (格式: `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`)

### 第2步: 运行系统 (2分钟)

```bash
# 进入项目目录
cd /Users/bytedance/openviking_insights

# 运行采集
./run_local.sh
```

等待运行完成，你会看到:
```
✓ Token 验证成功
✓ 依赖安装完成
✓ 数据采集完成
✓ 校准计算完成
✓ 飞书同步完成
========================================
  ✓ 运行成功！
========================================
```

### 第3步: 查看数据 (1分钟)

打开飞书多维表格:

**🔗 打开 `.env` 对应的飞书多维表格链接**

查看:
- ✅ OpenViking 项目数据
- ✅ 13 个竞品对比
- ✅ 三层校准分析
- ✅ 可视化图表

**完成！** 🎉

---

## 📊 你将看到的数据

### OpenViking 项目
- Stars, Forks, Watchers
- Issues, PRs, Contributors
- 社区活力评分
- 外部影响力评分

### 三层校准分析
- 📈 自我基准: 近7天 vs 前7天
- 🏆 同类对标: 与13个竞品排名
- 🎯 分类阈值: 项目阶段评估

### 竞品对比
- 与 LanceDB、Mem0、Supermemory 等对比
- 分位数排名
- 优势和差距分析

---

## 🔄 日常使用

### 自动运行（推荐）
系统会在每天北京时间 10:00 自动运行，无需人工干预。

### 手动运行
如果需要立即查看最新数据:

```bash
cd /Users/bytedance/openviking_insights
./run_local.sh
```

### 查看数据
随时打开飞书表格查看:
飞书多维表格链接由 `.env` 中的 `LARK_BASE_TOKEN` 决定

---

## ⚠️ 重要提示

### GitHub Token
- Token 是访问 GitHub API 的钥匙
- **绝对不要分享给他人**
- **不要提交到 Git 仓库**
- 如果泄露，立即在 GitHub 撤销并重新创建

### 数据安全
- 数据仅存储在本地和飞书
- 不会上传到第三方服务器
- 所有传输使用 HTTPS 加密

---

## 📞 需要帮助？

### 查看文档
- `README.md` - 完整项目文档
- `docs/GITHUB_TOKEN_GUIDE.md` - 详细 Token 指南
- `docs/QUICK_START.md` - 操作手册

### 常见问题
**Q: Token 失效怎么办？**
A: 访问 https://github.com/settings/tokens 创建新 Token

**Q: 如何添加新项目？**
A: 编辑 `config/projects.json`，添加项目后重新运行

**Q: 飞书表格访问不了？**
A: 确认已登录飞书账号，检查网络连接

---

## 🎊 恭喜！

**OpenViking 项目洞察自动化系统已完全就绪！**

### 立即开始:

1. **获取 Token** (2分钟)
   https://github.com/settings/tokens

2. **运行系统** (1分钟)
   ```bash
   ./run_local.sh
   ```

3. **查看数据** (1分钟)
   飞书多维表格链接由 `.env` 中的 `LARK_BASE_TOKEN` 决定

**总计: 5 分钟！** 🚀

---

**系统已就绪，开始享受自动化数据洞察吧！** 🎉

---

**部署时间**: 2026-04-15  
**系统版本**: v1.0.0  
**状态**: ✅ 完全就绪  

**🚀 开始你的数据洞察之旅！** 🎊
