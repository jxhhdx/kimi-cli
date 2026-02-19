# Kimi2 Code CLI - 定制版使用说明

这是 [Kimi Code CLI](https://github.com/MoonshotAI/kimi-cli) 的定制版本，添加了任务完成通知和邮件接收处理功能。

## ✨ 与官方版本的区别

| 特性 | 官方 `kimi` | 定制版 `kimi2` |
|------|-------------|----------------|
| 命令名 | `kimi` | `kimi2` |
| 配置目录 | `~/.kimi` | `~/.kimi2` |
| 任务完成通知 | ❌ | ✅ (邮件/Webhook) |
| 邮件接收处理 | ❌ | ✅ (IMAP) |
| 与官方冲突 | - | ❌ 完全独立 |

## 🚀 安装方法

### 方式一：从源码安装（推荐开发者）

```bash
# 1. 克隆仓库
git clone https://github.com/YOUR_USERNAME/kimi-cli.git
cd kimi-cli

# 2. 安装依赖
uv sync --frozen

# 3. 创建命令链接
ln -sf "$(pwd)/.venv/bin/kimi2" ~/.local/bin/kimi2
```

### 方式二：使用 pip 安装（如果发布到 PyPI）

```bash
pip install kimi2-cli
```

## 📝 使用方法

```bash
# 启动交互模式
kimi2

# 单次执行
kimi2 --prompt "帮我写一个 Python 脚本"

# YOLO 模式（无需确认）
kimi2 --yolo --prompt "修改配置文件"

# 查看版本
kimi2 --version
```

## ⚙️ 配置

### 配置文件位置

- **主配置**: `~/.kimi2/config.toml`
- **日志**: `~/.kimi2/logs/`
- **会话**: `~/.kimi2/sessions/`

### 任务完成通知配置

编辑 `~/.kimi2/config.toml`：

```toml
default_model = "kimi-k2.5"

[hooks.task_completion]
enabled = true

[[hooks.task_completion.channels]]
type = "email"
smtp_host = "smtp.gmail.com"
username = "your@gmail.com"
password = "${GMAIL_APP_PASSWORD}"  # 从环境变量读取
to = "receiver@example.com"
```

## 🔄 更新代码

### 更新定制版（保留你的修改）

```bash
# 1. 拉取官方最新代码
git fetch origin main

# 2. 合并到定制分支（只会有 3 个文件可能有冲突）
git merge origin/main

# 冲突文件通常只有：
# - pyproject.toml（入口命令）
# - src/kimi_cli/share.py（配置目录）
# - src/kimi_cli/constant.py（版本号）

# 3. 重新安装
uv sync --frozen
```

## 🏗️ 开发说明

### 文件结构

```
src/kimi_cli/          # 保持与官方相同的模块名
├── cli/__init__.py    # 入口，已修改为显示 kimi2 版本
├── share.py           # 配置目录改为 ~/.kimi2
├── constant.py        # 版本标识改为 kimi2
└── ...                # 其他文件与官方保持一致
```

### 合并策略

当你需要合并官方最新代码时：

1. 官方代码修改了功能代码 → **自动合并，无冲突**
2. 官方修改了 `pyproject.toml` 的依赖 → **可能需要手动解决**
3. 官方修改了版本号 → **保留定制版的版本标识**

```bash
# 推荐合并流程
git fetch origin main
git merge origin/main

# 如果冲突，按以下优先级解决：
# 1. pyproject.toml: 保留 kimi2 的入口命令，接受官方的依赖更新
# 2. share.py: 保留 ~/.kimi2 配置目录
# 3. constant.py: 保留定制版版本标识

uv sync --frozen
```

## 📄 许可证

与官方 Kimi Code CLI 相同的许可证。

## 🙏 致谢

基于 [MoonshotAI/kimi-cli](https://github.com/MoonshotAI/kimi-cli) 构建。
