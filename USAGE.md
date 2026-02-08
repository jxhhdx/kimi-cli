# Kimi CLI 魔改版 - 使用指南

## 🚀 快速开始

### 1. 安装 kimi2 命令

```bash
cd /Users/gaoxiang/Workspace2026/kimi-cli
./scripts/install-kimi2.sh

# 重新加载 shell 配置
source ~/.zshrc  # 或 ~/.bashrc
```

### 2. 配置邮件通知

```bash
# 添加到 ~/.zshrc 或 ~/.bashrc
export KIMI_EMAIL_ADDRESS="1490960584@qq.com"
export KIMI_EMAIL_PASSWORD="iemigwydobhjbagh"
export KIMI_NOTIFY_EMAIL="igaoxian@foxmail.com"
```

### 3. 测试

```bash
# 测试邮件配置
kimi2 mail test

# 发送测试邮件
kimi2 mail send-test
```

---

## 📋 命令对比

| 命令 | 说明 |
|------|------|
| `kimi` | 官方原版 kimi-cli |
| `kimi2` | 魔改版（带邮件通知功能） |

---

## 🔔 邮件通知功能

### 任务完成后自动通知

```bash
# 运行任务（完成后自动发邮件通知）
kimi2 --print -y -p "帮我优化这段代码"

# 任务完成 → 自动发送邮件到 igaoxian@foxmail.com
```

### 检查邮件回复

```bash
# 检查是否有新的邮件回复
kimi2 mail check
```

### 支持的邮箱

- Gmail (`gmail.com`)
- QQ邮箱 (`qq.com`)
- 163邮箱 (`163.com`)
- Outlook/Hotmail (`outlook.com`)

---

## ⚙️ 完整配置示例

```bash
# ~/.zshrc 或 ~/.bashrc

# 魔改版路径
export KIMI_EMAIL_ADDRESS="1490960584@qq.com"
export KIMI_EMAIL_PASSWORD="你的授权码"
export KIMI_NOTIFY_EMAIL="igaoxian@foxmail.com"

# kimi2 别名（已自动添加）
# alias kimi2="/Users/gaoxiang/Workspace2026/kimi-cli/scripts/kimi2"
```

---

## 📝 使用示例

### 示例 1: 运行任务并接收通知

```bash
# 在 /tmp 目录运行任务
cd /tmp

# 运行任务（完成后自动邮件通知）
kimi2 --print -y -p "创建一个 Python 脚本，计算斐波那契数列"

# 检查邮箱，收到通知邮件
# 邮件主题: "Kimi: Task Completed"
```

### 示例 2: 通过邮件回复继续任务

```bash
# 1. 收到任务完成邮件
# 2. 回复邮件: "请添加注释说明"
# 3. 运行检查命令
kimi2 mail check

# 4. kimi 读取回复并继续处理
```

### 示例 3: 检查邮件配置

```bash
kimi2 mail test
# 输出:
# ✓ SMTP connection OK
# ✓ IMAP connection OK
# ✓ Configuration valid!
```

---

## 🔧 故障排除

### 问题: kimi2 命令未找到

```bash
# 手动添加别名
alias kimi2="/Users/gaoxiang/Workspace2026/kimi-cli/scripts/kimi2"
```

### 问题: 邮件发送失败

1. 检查邮箱授权码是否正确
2. QQ邮箱需要使用授权码而非密码
3. 检查邮箱是否开启 SMTP/IMAP 服务

### 问题: 无法加载模块

```bash
# 确保 Python 版本 >= 3.10
python3 --version

# 安装必要依赖
pip install aiosmtplib aioimaplib jinja2
```

---

## 🎉 完成！

现在你可以：
- 使用 `kimi` 运行官方原版
- 使用 `kimi2` 运行魔改版（带邮件通知）
- 任务完成后自动收到邮件通知
- 回复邮件后继续任务
