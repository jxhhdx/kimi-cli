#!/bin/bash
#
# 远程安装脚本 - 在其他机器上部署 kimi2
#
# 使用方法:
#   curl -fsSL https://raw.githubusercontent.com/jxhhdx/kimi-cli/custom/main/scripts/install-remote.sh | bash
#   或
#   wget -qO- https://raw.githubusercontent.com/jxhhdx/kimi-cli/custom/main/scripts/install-remote.sh | bash
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}ℹ${NC} $1"; }
log_success() { echo -e "${GREEN}✓${NC} $1"; }
log_warning() { echo -e "${YELLOW}⚠${NC} $1"; }
log_error() { echo -e "${RED}✗${NC} $1"; }

# Configuration
GITHUB_REPO="https://github.com/jxhhdx/kimi-cli"
INSTALL_DIR="${HOME}/.kimi-cli-custom"
BRANCH="custom/main"

echo "=========================================="
echo "Kimi CLI 魔改版 - 远程安装"
echo "=========================================="
echo ""

# 检查 Python 版本
log_info "检查 Python 版本..."
if ! command -v python3 &> /dev/null; then
    log_error "未找到 python3，请先安装 Python 3.10+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
REQUIRED_VERSION="3.10"

if [[ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]]; then
    log_error "需要 Python $REQUIRED_VERSION+，当前版本: $PYTHON_VERSION"
    exit 1
fi
log_success "Python 版本检查通过: $PYTHON_VERSION"

# 检查 git
if ! command -v git &> /dev/null; then
    log_error "未找到 git，请先安装 git"
    exit 1
fi

# 如果已存在，先备份
if [[ -d "$INSTALL_DIR" ]]; then
    log_warning "检测到已有安装，将更新到最新版本"
    BACKUP_DIR="${INSTALL_DIR}.backup.$(date +%Y%m%d-%H%M%S)"
    mv "$INSTALL_DIR" "$BACKUP_DIR"
    log_info "已备份到: $BACKUP_DIR"
fi

# 克隆仓库
log_info "从 GitHub 克隆代码..."
git clone --depth 1 --branch "$BRANCH" "$GITHUB_REPO" "$INSTALL_DIR"
log_success "代码克隆完成"

# 安装依赖
log_info "安装依赖..."
pip3 install --quiet --user \
    aiosmtplib>=3.0.0 \
    aioimaplib>=1.1.0 \
    email-validator>=2.0.0 \
    jinja2>=3.0.0 2>/dev/null || pip3 install --quiet \
    aiosmtplib>=3.0.0 \
    aioimaplib>=1.1.0 \
    email-validator>=2.0.0 \
    jinja2>=3.0.0
log_success "依赖安装完成"

# 创建 kimi2 启动脚本
log_info "创建 kimi2 命令..."

mkdir -p "$HOME/.local/bin"

# 检测 Python 路径
PYTHON_PATH=$(which python3)

cat > "$HOME/.local/bin/kimi2" << EOF
#!/bin/bash
#
# kimi2 - 魔改版 Kimi CLI 启动脚本
# 安装位置: $INSTALL_DIR
#

export KIMI_CUSTOM_DIR="$INSTALL_DIR"
export PYTHON="$PYTHON_PATH"

# 设置 Python 路径
export PYTHONPATH="\$KIMI_CUSTOM_DIR/src:\$KIMI_CUSTOM_DIR/packages:\$KIMI_CUSTOM_DIR/packages/kaos/src:\$KIMI_CUSTOM_DIR/packages/kosong/src:\$KIMI_CUSTOM_DIR/packages/kimi-code/src:\$PYTHONPATH"

# 运行魔改版
exec "\$PYTHON" -c "
import sys
sys.path.insert(0, '\$KIMI_CUSTOM_DIR/src')
sys.path.insert(0, '\$KIMI_CUSTOM_DIR/packages')
sys.path.insert(0, '\$KIMI_CUSTOM_DIR/packages/kaos/src')
sys.path.insert(0, '\$KIMI_CUSTOM_DIR/packages/kosong/src')
sys.path.insert(0, '\$KIMI_CUSTOM_DIR/packages/kimi-code/src')

# 预加载 mock 模块
import importlib.util
spec = importlib.util.spec_from_file_location('keyring', '\$KIMI_CUSTOM_DIR/packages/keyring_mock.py')
keyring = importlib.util.module_from_spec(spec)
spec.loader.exec_module(keyring)
sys.modules['keyring'] = keyring

# 运行 CLI
from kimi_cli.cli import cli
cli()
" "\$@"
EOF

chmod +x "$HOME/.local/bin/kimi2"
log_success "kimi2 命令已创建: $HOME/.local/bin/kimi2"

# 确保 PATH 包含 ~/.local/bin
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    log_warning "~/.local/bin 不在 PATH 中"
    echo ""
    echo "请添加以下行到你的 ~/.bashrc 或 ~/.zshrc:"
    echo 'export PATH="$HOME/.local/bin:$PATH"'
    echo ""
fi

# 创建配置文件
mkdir -p "$HOME/.kimi"

if [[ ! -f "$HOME/.kimi/config.toml" ]]; then
    cat > "$HOME/.kimi/config.toml" << 'EOF'
# Kimi CLI 魔改版配置
# GitHub: https://github.com/jxhhdx/kimi-cli/tree/custom/main

# 邮件通知设置
[notification]
# 发件邮箱
email_address = ""
# 邮箱授权码（不是密码）
email_password = ""
# 通知接收邮箱（可以是多个，用逗号分隔）
notify_email = ""

# 邮件服务设置（用于接收回复）
[mail]
# IMAP 服务器
imap_server = "imap.qq.com"
imap_port = 993
# 只处理这些邮箱发来的邮件
allowed_senders = []
EOF
    log_success "配置文件已创建: ~/.kimi/config.toml"
fi

# 验证安装
echo ""
log_info "验证安装..."

if command -v kimi2 &> /dev/null; then
    kimi2 --version 2>/dev/null || echo "版本检查跳过"
    log_success "kimi2 安装成功！"
else
    log_warning "kimi2 命令可能需要重新加载 shell 才能使用"
    echo "请运行: source ~/.bashrc 或 source ~/.zshrc"
fi

echo ""
echo "=========================================="
log_success "安装完成！"
echo "=========================================="
echo ""
echo "下一步:"
echo ""
echo "1. 配置邮件通知（编辑 ~/.kimi/config.toml）:"
echo "   或使用环境变量:"
echo "   export KIMI_EMAIL_ADDRESS='your-email@qq.com'"
echo "   export KIMI_EMAIL_PASSWORD='your-auth-code'"
echo "   export KIMI_NOTIFY_EMAIL='receiver@example.com'"
echo ""
echo "2. 测试邮件配置:"
echo "   kimi2 mail test"
echo ""
echo "3. 开始使用:"
echo "   kimi2 --print -y -p '你的任务'"
echo ""
echo "=========================================="
