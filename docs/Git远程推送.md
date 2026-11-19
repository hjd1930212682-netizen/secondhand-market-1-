# Git 远程推送配置（GitHub）

当前状态：本地仓库 `main` 分支已有 D1 提交，但**尚未配置远程仓库**，也没有可用的 GitHub 凭据
（`ssh -T git@github.com` 返回 `Permission denied (publickey)`）。

配好下面任意一种方式后，每日自动任务会在提交完成后自动 `git push`。

## 方式一：SSH（推荐，一次配置长期可用）

本机已有公钥 `C:\Users\13230\.ssh\id_ed25519.pub`，只需把公钥加到 GitHub。

**第 1 步：复制公钥**

```bash
cat ~/.ssh/id_ed25519.pub
```

复制输出的整行（以 `ssh-ed25519` 开头）。

**第 2 步：添加到 GitHub**

网页打开 https://github.com/settings/keys → `New SSH key` → Title 填 `课程项目-笔记本` →
Key 粘贴刚才复制的内容 → `Add SSH key`。

**第 3 步：验证**

```bash
ssh -T git@github.com
```

出现 `Hi 你的用户名! You've successfully authenticated` 即成功（提示 `does not provide shell access` 属正常）。

**第 4 步：在 GitHub 新建仓库**

https://github.com/new → Repository name 填 `secondhand-market` →
选择 **Private**（课程作业建议私有，答辩前再决定是否公开）→
**不要**勾选 `Add a README file`、`.gitignore`、`license`（否则推送会冲突）→ `Create repository`。

**第 5 步：绑定并首次推送**

```bash
cd "C:/Users/13230/Desktop/操作系统/secondhand-market"
git remote add origin git@github.com:你的用户名/secondhand-market.git
git push -u origin main
```

## 方式二：HTTPS + 个人访问令牌

GitHub 已不支持密码推送，必须用 Personal Access Token（PAT）。

**第 1 步**：https://github.com/settings/tokens → `Generate new token (classic)` →
勾选 `repo` 权限 → 生成后立即复制（只显示一次）。

**第 2 步**：

```bash
cd "C:/Users/13230/Desktop/操作系统/secondhand-market"
git remote add origin https://github.com/你的用户名/secondhand-market.git
git push -u origin main
# 用户名填 GitHub 用户名，密码粘贴刚才的 token
```

**第 3 步（可选）**：避免每次输入

```bash
git config --global credential.helper manager
```

Windows 下首次输入后由凭据管理器保存。

## 配好之后的每日流程

```bash
git add <当日范围内的文件>          # 按 docs/Git提交计划.md
git -c user.name="郝津德" -c user.email="haojinde@stu.edu.cn" commit -m "feat(模块): 说明"
git push origin main               # 推到 GitHub
```

每日 20:00 的自动任务已包含这一步：**有 `origin` 就推送，没有则跳过并在汇报里提示**，
推送失败（凭据失效、网络不通）会明确报错，不会静默忽略。

## 常见问题

| 现象 | 原因 | 处理 |
|---|---|---|
| `Permission denied (publickey)` | 公钥没加到 GitHub，或加到了别的账号 | 重做方式一第 1-3 步 |
| `remote origin already exists` | 已配置过远程 | `git remote set-url origin <新地址>` |
| `Updates were rejected` | 远程仓库初始化过 README | `git pull --rebase origin main` 后再推 |
| `Support for password authentication was removed` | 用了账号密码 | 改用 token（方式二） |
| 推送很慢或超时 | 网络问题 | 配置代理，或改用 HTTPS + 凭据管理器 |

## 提交历史怎么给老师看

- 本地：`git log --graph --pretty=format:"%ad | %an | %s" --date=format:"%Y-%m-%d %H:%M"`
- 线上：仓库页面 `Commits`，可看到四个成员名字与分散的提交时间
- 报告配图：截 `git log --graph` 与 GitHub 提交列表各一张，对应第 4.5 节
