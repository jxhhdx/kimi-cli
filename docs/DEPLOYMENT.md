# Kimi CLI 魔改版 - 部署文档

> **GitHub**: https://github.com/jxhhdx/kimi-cli/tree/custom/main  
> **分支**: `custom/main`  
> **版本**: 1.9.0-custom

---

## 📋 目录

1. [系统要求](#-系统要求)
2. [快速部署](#-快速部署)
3. [详细安装步骤](#-详细安装步骤)
4. [配置指南](#-配置指南)
5. [验证安装](#-验证安装)
6. [多机器部署](#-多机器部署)
7. [升级与维护](#-升级与维护)
8. [卸载](#-卸载)
9. [故障排查](#-故障排查)

---

## 💻 系统要求

| 项目 | 要求 |
|------|------|
| **操作系统** | Linux / macOS / WSL (Windows) |
| **Python** | >= 3.10 |
| **Git** | 任意版本 |
| **网络** | 可访问 GitHub 和邮件服务器 |
| **磁盘空间** | ~50MB |

### 检查环境

```bash
# 检查 Python 版本
python3 --version  # 需 >= 3.10

# 检查 Git
git --version

# 检查网络 (GitHub)
curl -I https://github.com
```

---

## 🚀 快速部署

### 方式一：一键安装（推荐）

```bash
# 使用 curl
curl -fsSL https://raw.githubusercontent.com/jxhhdx/kimi-cli/custom/main/scripts/install-remote.sh | bash

# 或使用 wget
wget -qO- https://raw.githubusercontent.com/jxhhdx/kimi-cli/custom/main/scripts/install-remote.sh | bash
```

安装完成后，配置环境变量即可使用。

### 方式二：手动安装

```bash
# 1. 克隆代码
git clone --depth 1 -b custom/main https://github.com/jxhhdx/kimi-cli.git ~/.kimi-cli-custom

# 2. 安装依赖
pip3 install --user aiosmtplib aioimaplib jinja2 email-validator

# 3. 创建启动脚本
mkdir -p ~/.local/bin
cat > ~/.local/bin/kimi2 << 'SCRIPT'
#!/bin/bash
export KIMI_CUSTOM_DIR="$HOME/.kimi-cli-custom"
export PYTHONPATH="$KIMI_CUSTOM_DIR/src:$KIMI_CUSTOM_DIR/packages:$PYTHONPATH"
python3 -c "
import sys
sys.path.insert(0, '$KIMI_CUSTOM_DIR/src')
sys.path.insert(0, '$KIMI_CUSTOM_DIR/packages')
from kimi_cli.cli import cli
cli()
" "$@"
SCRIPT
chmod +x ~/.local/bin/kimi2

# 4. 确保 PATH 包含 ~/.local/bin
export PATH="$HOME/.local/bin:$PATH"
```

---

## 🔧 详细安装步骤

### 步骤 1：准备环境

```bash
# 创建配置目录
mkdir -p ~/.kimi

# 检查 Python 版本
python3 --version
```

### 步骤 2：下载代码

```bash
# 方式 A：git 克隆（推荐，便于更新）
git clone --depth 1 -b custom/main \
    https://github.com/jxhhdx/kimi-cli.git \
    ~/.kimi-cli-custom

# 方式 B：下载 zip（如果无法使用 git）
curl -L -o /tmp/kimi-cli.zip \
    https://github.com/jxhhdx/kimi-cli/archive/refs/heads/custom/main.zip
unzip /tmp/kimi-cli.zip -d /tmp/
mv /tmp/kimi-cli-custom-main ~/.kimi-cli-custom
```

### 步骤 3：安装依赖

```bash
pip3 install --user \
    aiosmtplib>=3.0.0 \
    aioimaplib>=1.1.0 \
    jinja2>=3.0.0 \
    email-validator>=2.0.0
```

### 步骤 4：创建启动脚本

```bash
mkdir -p ~/.local/bin

cat > ~/.local/bin/kimi2 << 'EOF'
#!/bin/bash
#
# kimi2 - 魔改版 Kimi CLI 启动脚本
#

export KIMI_CUSTOM_DIR="${HOME}/.kimi-cli-custom"
PYTHON="${PYTHON:-$(which python3)}"

# 设置 Python 路径
export PYTHONPATH="${KIMI_CUSTOM_DIR}/src:${KIMI_CUSTOM_DIR}/packages:${PYTHONPATH}"

exec "${PYTHON}" -c "
import sys
sys.path.insert(0, '${KIMI_CUSTOM_DIR}/src')
sys.path.insert(0, '${KIMI_CUSTOM_DIR}/packages')

# 预加载 mock keyring 模块
import importlib.util
spec = importlib.util.spec_from_file_location(
    'keyring', 
    '${KIMI_CUSTOM_DIR}/packages/keyring_mock.py'
)
if spec and spec.loader:
    keyring = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(keyring)
    sys.modules['keyring'] = keyring

from kimi_cli.cli import cli
cli()
" "$@"
EOF

chmod +x ~/.local/bin/kimi2
```

### 步骤 5：添加到 PATH

```bash
# 检查 ~/.local/bin 是否在 PATH
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    # 添加到 shell 配置
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
    # 或 ~/.zshrc（如果使用 zsh）
    # echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
fi

# 立即生效
export PATH="$HOME/.local/bin:$PATH"
```

---

## ⚙️ 配置指南

### 环境变量配置（推荐）

编辑 `~/.bashrc` 或 `~/.zshrc`：

```bash
# =====================================
# Kimi CLI 魔改版配置
# =====================================

# 发件邮箱配置（用于发送通知）
export KIMI_EMAIL_ADDRESS="your-email@qq.com"
export KIMI_EMAIL_PASSWORD="your-auth-code"  # 不是登录密码，是授权码

# 通知接收邮箱（任务完成后发到这里）
export KIMI_NOTIFY_EMAIL="receiver@example.com"

# 可选：IMAP 配置（用于接收邮件回复）
export KIMI_IMAP_SERVER="imap.qq.com"
export KIMI_IMAP_PORT="993"
```

### 配置文件方式

创建 `~/.kimi/config.toml`：

```toml
# Kimi CLI 魔改版配置

[notification]
email_address = "your-email@qq.com"
email_password = "your-auth-code"
notify_email = "receiver@example.com"

[mail]
imap_server = "imap.qq.com"
imap_port = 993
allowed_senders = ["trusted@example.com"]

[hooks.task_completion]
enabled = true

[[hooks.task_completion.channels]]
type = "email"
name = "default"
enabled = true
smtp_host = "smtp.qq.com"
smtp_port = 587
username = "your-email@qq.com"
password = "your-auth-code"
to_addrs = ["receiver@example.com"]
```

### 邮箱授权码获取

| 邮箱 | 授权码获取方式 |
|------|---------------|
| **QQ邮箱** | 设置 → 账户 → 开启 SMTP → 生成授权码 |
| **163邮箱** | 设置 → POP3/SMTP → 开启服务 → 获取授权码 |
| **Gmail** | 账户 → 安全性 → 应用专用密码 |
| **Outlook** | 账户 → 安全性 → 应用密码 |

---

## ✅ 验证安装

### 1. 检查命令

```bash
# 检查 kimi2 是否可执行
which kimi2

# 查看版本
kimi2 --version
# 预期输出包含 "custom"
```

### 2. 测试邮件配置

```bash
# 测试邮件发送
kimi2 mail test

# 预期输出：
# ✓ SMTP connection OK
# ✓ Authentication successful
# ✓ Test email sent
```

### 3. 运行测试任务

```bash
# 创建临时目录
cd /tmp

# 运行简单任务（带邮件通知）
kimi2 --print -y -p "创建一个 Python 脚本，输出 'Hello World'"

# 检查是否收到邮件通知
```

---

## 🖥️ 多机器部署

### 场景 1：批量部署到多台服务器

创建部署脚本 `deploy-kimi2.sh`：

```bash
#!/bin/bash
# deploy-kimi2.sh - 批量部署到多台机器

SERVERS=(
    "user@server1.example.com"
    "user@server2.example.com"
    "user@server3.example.com"
)

for server in "${SERVERS[@]}"; do
    echo "部署到: $server"
    
    ssh "$server" '
        # 一键安装
        curl -fsSL https://raw.githubusercontent.com/jxhhdx/kimi-cli/custom/main/scripts/install-remote.sh | bash
        
        # 配置环境变量（根据实际情况修改）
        echo "export KIMI_EMAIL_ADDRESS=\"your-email@qq.com\"" >> ~/.bashrc
        echo "export KIMI_EMAIL_PASSWORD=\"your-auth-code\"" >> ~/.bashrc
        echo "export KIMI_NOTIFY_EMAIL=\"receiver@example.com\"" >> ~/.bashrc
        
        # 验证
        source ~/.bashrc
        kimi2 --version
    '
done

echo "批量部署完成！"
```

### 场景 2：Docker 部署

创建 `Dockerfile`：

```dockerfile
FROM python:3.12-slim

# 安装依赖
RUN pip install --no-cache-dir \
    aiosmtplib aioimaplib jinja2 email-validator

# 克隆代码
RUN git clone --depth 1 -b custom/main \
    https://github.com/jxhhdx/kimi-cli.git /opt/kimi-cli-custom

# 创建启动脚本
RUN echo '#!/bin/bash\n\
export KIMI_CUSTOM_DIR=/opt/kimi-cli-custom\n\
export PYTHONPATH=/opt/kimi-cli-custom/src:/opt/kimi-cli-custom/packages\n\
python3 -c "import sys; sys.path.insert(0, \"/opt/kimi-cli-custom/src\"); from kimi_cli.cli import cli; cli()" \"\$@\"' \
    > /usr/local/bin/kimi2 && chmod +x /usr/local/bin/kimi2

# 设置工作目录
WORKDIR /workspace

ENTRYPOINT ["kimi2"]
```

构建和运行：

```bash
# 构建镜像
docker build -t kimi2:latest .

# 运行（带环境变量）
docker run -it \
    -e KIMI_EMAIL_ADDRESS="your@qq.com" \
    -e KIMI_EMAIL_PASSWORD="your-auth-code" \
    -e KIMI_NOTIFY_EMAIL="receiver@example.com" \
    -v $(pwd):/workspace \
    kimi2:latest --print -y -p "你的任务"
```

### 场景 3：CI/CD 集成

GitHub Actions 示例：

```yaml
# .github/workflows/kimi-task.yml
name: Run Kimi Task

on:
  push:
    branches: [main]

jobs:
  kimi-task:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Install kimi2
        run: |
          curl -fsSL https://raw.githubusercontent.com/jxhhdx/kimi-cli/custom/main/scripts/install-remote.sh | bash
          echo "$HOME/.local/bin" >> $GITHUB_PATH
      
      - name: Run Kimi Task
        env:
          KIMI_EMAIL_ADDRESS: ${{ secrets.KIMI_EMAIL }}
          KIMI_EMAIL_PASSWORD: ${{ secrets.KIMI_PASSWORD }}
          KIMI_NOTIFY_EMAIL: ${{ secrets.NOTIFY_EMAIL }}
        run: |
          kimi2 --print -y -p "Review the code changes"
```

---

## 🔄 升级与维护

### 升级到新版本

```bash
# 方法 1：使用安装脚本重新安装（推荐）
curl -fsSL https://raw.githubusercontent.com/jxhhdx/kimi-cli/custom/main/scripts/install-remote.sh | bash

# 方法 2：手动更新
cd ~/.kimi-cli-custom
git pull origin custom/main

# 重新安装依赖
pip3 install --user --upgrade aiosmtplib aioimaplib jinja2
```

### 查看当前版本

```bash
# 查看 kimi2 版本
kimi2 --version

# 查看代码版本
cd ~/.kimi-cli-custom && git log --oneline -5
```

### 备份配置

```bash
# 备份配置和代码
tar czf ~/kimi2-backup-$(date +%Y%m%d).tar.gz \
    ~/.kimi-cli-custom \
    ~/.kimi/
```

---

## 🗑️ 卸载

```bash
# 1. 删除代码目录
rm -rf ~/.kimi-cli-custom

# 2. 删除启动脚本
rm -f ~/.local/bin/kimi2

# 3. 删除配置（可选）
rm -rf ~/.kimi/

# 4. 清理环境变量（从 ~/.bashrc 或 ~/.zshrc 中删除相关行）
```

---

## 🔍 故障排查

### 问题 1：kimi2 命令未找到

```bash
# 检查文件是否存在
ls -la ~/.local/bin/kimi2

# 检查 PATH
echo $PATH | grep ".local/bin"

# 手动添加 PATH
export PATH="$HOME/.local/bin:$PATH"
```

### 问题 2：邮件发送失败

```bash
# 检查网络连接
ping smtp.qq.com

# 检查授权码是否正确
# QQ邮箱需要使用授权码，不是登录密码

# 手动测试 SMTP
python3 -c "
import aiosmtplib
import asyncio

async def test():
    try:
        client = aiosmtplib.SMTP('smtp.qq.com', 587)
        await client.connect()
        await client.starttls()
        await client.login('your@qq.com', 'your-auth-code')
        print('✓ SMTP 连接成功')
        await client.quit()
    except Exception as e:
        print(f'✗ 错误: {e}')

asyncio.run(test())
"
```

### 问题 3：Python 模块导入错误

```bash
# 检查 Python 路径
echo $PYTHONPATH

# 手动设置
export PYTHONPATH="$HOME/.kimi-cli-custom/src:$HOME/.kimi-cli-custom/packages:$PYTHONPATH"

# 检查依赖是否安装
pip3 list | grep -E "aiosmtplib|aioimaplib|jinja2"

# 重新安装依赖
pip3 install --force-reinstall --user aiosmtplib aioimaplib jinja2
```

### 问题 4：GitHub 访问失败

```bash
# 检查网络
curl -I https://github.com

# 使用代理（如果需要）
export HTTPS_PROXY=http://proxy.example.com:8080

# 或使用国内镜像（如果有）
git clone --depth 1 -b custom/main \
    https://ghproxy.com/https://github.com/jxhhdx/kimi-cli.git \
    ~/.kimi-cli-custom
```

### 问题 5：权限错误

```bash
# 修复权限
chmod +x ~/.local/bin/kimi2
chmod -R u+rw ~/.kimi-cli-custom

# 如果安装在系统目录，可能需要 sudo
# 但推荐使用 --user 安装到用户目录
```

---

## 📞 获取帮助

- **GitHub Issues**: https://github.com/jxhhdx/kimi-cli/issues
- **查看日志**: `kimi2 --verbose --print -y -p "test"`
- **检查配置**: `cat ~/.kimi/config.toml`

---

*文档版本: 1.0*  
*最后更新: 2026-02-08*
