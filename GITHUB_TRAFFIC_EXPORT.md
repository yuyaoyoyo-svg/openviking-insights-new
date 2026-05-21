# GitHub Traffic 数据拉取说明

本文档说明如何拉取 GitHub 仓库 `Insights -> Traffic` 页面对应的数据，包括：

- `views`
- `clones`
- `popular paths`
- `popular referrers`

文中的示例以 `volcengine/OpenViking` 为例，但命令同样适用于其他仓库。

## 1. 先说结论

如果要通过命令行拉取 GitHub Traffic 数据，通常需要满足两个条件：

- 你的 GitHub 账号对目标仓库有足够权限
- `gh` 或 `curl` 请求里带有 GitHub 认证信息

`gh` 可以不手动写 token，但前提是你已经登录过 `gh`。

## 2. 需要什么权限

截至 `2026-04-21`，GitHub Traffic 接口不是匿名接口。

### 2.1 账号权限

你的 GitHub 账号通常需要对目标仓库具备 `push` / `write` 级别访问，才能：

- 在 Web 页面打开 `https://github.com/<owner>/<repo>/graphs/traffic`
- 通过 REST API 拉取 traffic 数据

如果只是普通只读访问者，通常看不到这些数据，也无法正常调 API。

### 2.2 Token 权限

如果你使用的是当前 GitHub 主推的 `fine-grained PAT` 或 `GitHub App token`，GitHub 文档对 traffic 接口要求的仓库权限是：

- `Administration: Read`

如果你使用的是传统 `classic PAT`：

- 实际上常见做法是使用 `repo` scope
- 但 classic PAT 权限更宽，不是当前推荐方式

更稳妥的建议是：

- 优先使用 `fine-grained PAT`
- 只授权目标仓库
- 给该仓库授予 `Administration: Read`

## 3. 可以不用 token 吗

分情况看：

- 浏览器查看 Traffic 页面：可以不手动输入 token，但你必须已经登录 GitHub，浏览器会使用登录态 cookie
- `gh api` 拉取：可以不手动在命令里写 token，但你必须先执行过 `gh auth login`
- `curl` 直接拉取：通常需要显式带 token
- 匿名访问：不行

所以严格来说，不是“不要认证”，而是“认证信息是否由 `gh` 或浏览器替你管理”。

## 4. 安装 gh

如果本机还没有 `gh`，先安装 GitHub CLI。

macOS:

```bash
brew install gh
```

安装后确认版本：

```bash
gh --version
```

## 5. gh 怎么登录

### 5.1 推荐方式：浏览器登录

执行：

```bash
gh auth login
```

交互过程中建议这样选：

1. `GitHub.com`
2. `HTTPS`
3. `Login with a web browser`

完成后检查登录状态：

```bash
gh auth status
```

如果看到当前账号为 active account，就说明 `gh` 已经能代表这个账号访问 GitHub API。

### 5.2 使用 PAT 登录

如果你不想走浏览器交互，也可以直接用 token 登录。

先把 token 放进环境变量：

```bash
export GH_PAT="your_token_here"
```

然后执行：

```bash
printf '%s' "$GH_PAT" | gh auth login --with-token
```

登录完成后同样检查：

```bash
gh auth status
```

### 5.3 多账号时切换

如果本机登录了多个账号，可以先看状态：

```bash
gh auth status
```

必要时重新登录，或退出后重新登录：

```bash
gh auth logout
gh auth login
```

## 6. 直接拉取 Traffic 数据

下面这四个接口就是 Traffic 页面最常用的数据源。

### 6.1 views

```bash
gh api repos/volcengine/OpenViking/traffic/views
```

写入文件：

```bash
gh api repos/volcengine/OpenViking/traffic/views > views.json
```

### 6.2 clones

```bash
gh api repos/volcengine/OpenViking/traffic/clones > clones.json
```

### 6.3 popular paths

```bash
gh api repos/volcengine/OpenViking/traffic/popular/paths > popular_paths.json
```

### 6.4 popular referrers

```bash
gh api repos/volcengine/OpenViking/traffic/popular/referrers > referrers.json
```

## 7. 一次性导出到本地目录

下面这段命令会把四类数据导出到一个带时间戳的目录中。

```bash
STAMP="$(date '+%Y-%m-%d_%H%M%S')"
OUT_DIR="data/github-traffic/${STAMP}"

mkdir -p "$OUT_DIR"

gh api repos/volcengine/OpenViking/traffic/views > "$OUT_DIR/views.json"
gh api repos/volcengine/OpenViking/traffic/clones > "$OUT_DIR/clones.json"
gh api repos/volcengine/OpenViking/traffic/popular/paths > "$OUT_DIR/popular_paths.json"
gh api repos/volcengine/OpenViking/traffic/popular/referrers > "$OUT_DIR/referrers.json"

echo "exported to $OUT_DIR"
```

如果要改成别的仓库，只需要替换这段路径里的仓库名：

```text
repos/<owner>/<repo>/traffic/...
```

例如：

```bash
gh api repos/octocat/Hello-World/traffic/views
```

## 8. 导出后快速查看摘要

### 8.1 看 views 摘要

```bash
jq '{count, uniques, days: (.views|length), latest: .views[-1]}' views.json
```

### 8.2 看 clones 摘要

```bash
jq '{count, uniques, days: (.clones|length), latest: .clones[-1]}' clones.json
```

### 8.3 看热门页面前 5 条

```bash
jq '.[0:5]' popular_paths.json
```

### 8.4 看来源前 10 条

```bash
jq '.' referrers.json
```

## 9. 合并成一个 snapshot 文件

如果你希望把四份 JSON 合并成一个文件，可以用：

```bash
jq -n \
  --arg pulled_at "$(date '+%Y-%m-%dT%H:%M:%S%z')" \
  --arg repo "volcengine/OpenViking" \
  --slurpfile views views.json \
  --slurpfile clones clones.json \
  --slurpfile paths popular_paths.json \
  --slurpfile refs referrers.json \
  '{
    pulled_at: $pulled_at,
    repo: $repo,
    views: $views[0],
    clones: $clones[0],
    popular_paths: $paths[0],
    referrers: $refs[0]
  }' > traffic_snapshot.json
```

## 10. 也可以用 curl

如果你不用 `gh`，也可以直接调用 GitHub REST API。

先准备 token：

```bash
export GITHUB_TOKEN="your_token_here"
```

然后调用：

```bash
curl -sS \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  https://api.github.com/repos/volcengine/OpenViking/traffic/views
```

其他三个接口：

```bash
curl -sS \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  https://api.github.com/repos/volcengine/OpenViking/traffic/clones

curl -sS \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  https://api.github.com/repos/volcengine/OpenViking/traffic/popular/paths

curl -sS \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  https://api.github.com/repos/volcengine/OpenViking/traffic/popular/referrers
```

## 11. 常见报错

### 11.1 `404 Not Found`

常见原因：

- 仓库名写错
- 当前账号对仓库没有足够权限
- token 没有覆盖这个仓库

### 11.2 `403 Forbidden`

常见原因：

- token 权限不够
- 组织仓库禁用了 classic PAT
- fine-grained PAT 没有 `Administration: Read`

### 11.3 `Must have push access to repository`

说明账号本身对仓库权限不够。这个问题不是换命令能解决的，需要仓库管理员授予更高权限。

### 11.4 `error connecting to api.github.com`

常见原因：

- 当前环境网络受限
- 代理配置有问题
- CI / 沙箱环境不允许外网访问

## 12. 推荐的最小操作流程

如果目标是“最快把 Traffic 数据拉到本地”，建议按下面顺序做：

1. 安装 `gh`
2. 执行 `gh auth login`
3. 用浏览器方式登录到有仓库权限的 GitHub 账号
4. 执行 `gh auth status` 确认 active account
5. 运行四条 `gh api repos/<owner>/<repo>/traffic/...` 命令
6. 把结果保存到本地目录

最常用的一组命令如下：

```bash
STAMP="$(date '+%Y-%m-%d_%H%M%S')"
OUT_DIR="data/github-traffic/${STAMP}"

mkdir -p "$OUT_DIR"

gh auth status
gh api repos/volcengine/OpenViking/traffic/views > "$OUT_DIR/views.json"
gh api repos/volcengine/OpenViking/traffic/clones > "$OUT_DIR/clones.json"
gh api repos/volcengine/OpenViking/traffic/popular/paths > "$OUT_DIR/popular_paths.json"
gh api repos/volcengine/OpenViking/traffic/popular/referrers > "$OUT_DIR/referrers.json"
```

## 13. 参考文档

- Viewing traffic to a repository  
  https://docs.github.com/en/repositories/viewing-activity-and-data-for-your-repository/viewing-traffic-to-a-repository
- REST API endpoints for repository traffic  
  https://docs.github.com/en/rest/metrics/traffic
- Managing your personal access tokens  
  https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens
