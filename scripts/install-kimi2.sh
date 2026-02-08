#!/bin/bash
#
# 安装 kimi2 别名脚本
#
# 用法: ./install-kimi2.sh
#

set -e

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

KIMI_DIR="/Users/gaoxiang/Workspace2026/kimi-cli"
KIMI2_SCRIPT="$KIMI_DIR/scripts/kimi2"

echo "=== 安装 kimi2 别名 ==="
echo ""

# 检查脚本是否存在
if [[ ! -f "$KIMI2_SCRIPT" ]]; then
    echo "错误: 找不到 kimi2 脚本: $KIMI2_SCRIPT"
    exit 1
fi

# 确保脚本可执行
chmod +x "$KIMI2_SCRIPT"

# 检测 shell
SHELL_NAME=$(basename "$SHELL")
echo "检测到你的 shell: $SHELL_NAME"

# 根据 shell 选择配置文件
case "$SHELL_NAME" in
    zsh)
        SHELL_RC="$HOME/.zshrc"
        ;;
    bash)
        SHELL_RC="$HOME/.bashrc"
        ;;
    *)
        SHELL_RC="$HOME/.profile"
        ;;
esac

echo "配置文件: $SHELL_RC"
echo ""

# 检查是否已存在 kimi2 别名
if grep -q "alias kimi2=" "$SHELL_RC" 2>/dev/null; then
    echo "⚠️  发现已存在的 kimi2 别名，将更新..."
    # 删除旧别名
    sed -i.bak '/# kimi2 alias/,/alias kimi2=/d' "$SHELL_RC" 2>/dev/null || true
fi

# 添加别名到 shell 配置
cat >> "$SHELL_RC" << EOF

# kimi2 alias - 魔改版 Kimi CLI
alias kimi2="$KIMI2_SCRIPT"
EOF

echo -e "${GREEN}✓${NC} 别名已添加到 $SHELL_RC"
echo ""

# 创建软链接到 /usr/local/bin（可选）
if [[ -d "/usr/local/bin" && -w "/usr/local/bin" ]]; then
    ln -sf "$KIMI2_SCRIPT" /usr/local/bin/kimi2
    echo -e "${GREEN}✓${NC} 已创建软链接: /usr/local/bin/kimi2"
else
    echo "注意: 无法创建系统级软链接（需要权限）"
    echo "      使用别名方式即可"
fi

echo ""
echo "=== 安装完成 ==="
echo ""
echo "使用方法:"
echo "  1. 重新加载 shell 配置:"
echo "     source $SHELL_RC"
echo ""
echo "  2. 测试 kimi2:"
echo "     kimi2 --version"
echo "     kimi2 mail test"
echo ""
echo "  3. 配置邮件通知:"
echo "     export KIMI_EMAIL_ADDRESS='你的邮箱'"
echo "     export KIMI_EMAIL_PASSWORD='你的密码'"
echo "     export KIMI_NOTIFY_EMAIL='接收通知的邮箱'  # 可选"
echo ""
echo "提示:"
echo "  - kimi   = 官方原版"
echo "  - kimi2  = 魔改版（带邮件通知）"
echo ""
