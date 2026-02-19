#!/bin/bash
# Kimi2 Code CLI 安装脚本
# 用法: curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/kimi-cli/custom/main/scripts/install.sh | bash

set -e

REPO_URL="https://github.com/YOUR_USERNAME/kimi-cli.git"
BRANCH="custom/main"
INSTALL_DIR="${HOME}/.local/share/kimi2-cli"
BIN_DIR="${HOME}/.local/bin"

echo "🚀 正在安装 Kimi2 Code CLI..."

# 检测操作系统
detect_platform() {
    local _os
    _os=$(uname -s)
    case "$_os" in
        Linux*)     echo "linux";;
        Darwin*)    echo "macos";;
        *)          echo "unknown:$_os";;
    esac
}

PLATFORM=$(detect_platform)
if [[ "$PLATFORM" == unknown:* ]]; then
    echo "❌ 不支持的操作系统: ${PLATFORM#unknown:}"
    exit 1
fi

echo "📋 检测到操作系统: $PLATFORM"

# 检查依赖
check_dependencies() {
    if ! command -v git &> /dev/null; then
        echo "❌ 错误: 需要 git，请先安装"
        exit 1
    fi
    
    if ! command -v python3 &> /dev/null; then
        echo "❌ 错误: 需要 Python 3.10+，请先安装 Python"
        exit 1
    fi
}

check_dependencies

# 安装 uv（如果没有）
install_uv() {
    if command -v uv &> /dev/null; then
        echo "✅ uv 已安装: $(uv --version)"
        return
    fi
    
    echo "📦 正在安装 uv..."
    curl -LsSf https://astral.sh/uv/install.sh | bash
    
    # 重新加载 shell 配置以获取 uv
    export PATH="${HOME}/.cargo/bin:${PATH}"
    
    if ! command -v uv &> /dev/null; then
        echo "⚠️  uv 安装完成，但需要重新加载 shell 配置"
        echo "   请运行: source ~/.bashrc 或 source ~/.zshrc"
        echo "   然后重新运行此脚本"
        exit 1
    fi
    
    echo "✅ uv 安装完成: $(uv --version)"
}

install_uv

# 克隆或更新代码
install_or_update() {
    if [ -d "${INSTALL_DIR}/.git" ]; then
        echo "🔄 发现已有安装，正在更新..."
        cd "${INSTALL_DIR}"
        git fetch origin
        git checkout "${BRANCH}" 2>/dev/null || git checkout -b "${BRANCH}" origin/"${BRANCH}"
        git pull origin "${BRANCH}"
    else
        echo "📥 正在克隆代码..."
        rm -rf "${INSTALL_DIR}"
        mkdir -p "$(dirname "$INSTALL_DIR")"
        git clone --branch "${BRANCH}" --depth 1 "${REPO_URL}" "${INSTALL_DIR}"
        cd "${INSTALL_DIR}"
    fi
}

install_or_update

# 创建虚拟环境并安装
echo "🔧 正在安装依赖（这可能需要几分钟）..."
uv sync --frozen

# 确保 bin 目录存在
mkdir -p "${BIN_DIR}"

# 创建启动器脚本
cat > "${BIN_DIR}/kimi2" << EOF
#!/bin/bash
# Kimi2 Code CLI 启动器
export KIMI2_SHARE_DIR="\${HOME}/.kimi2"
exec "${INSTALL_DIR}/.venv/bin/kimi2" "\$@"
EOF

chmod +x "${BIN_DIR}/kimi2"

# 检查 PATH
if [[ ":$PATH:" != *":${BIN_DIR}:"* ]]; then
    echo ""
    echo "⚠️  警告: ${BIN_DIR} 不在 PATH 中"
    echo ""
    echo "请将以下行添加到你的 shell 配置文件:"
    echo "  export PATH=\"${BIN_DIR}:\$PATH\""
    echo ""
    echo "然后运行: source ~/.bashrc 或 source ~/.zshrc"
else
    echo "✅ ${BIN_DIR} 已在 PATH 中"
fi

# 验证安装
echo ""
echo "🧪 验证安装..."
if "${BIN_DIR}/kimi2" --version; then
    echo ""
    echo "✅ Kimi2 Code CLI 安装成功！"
    echo ""
    echo "使用方法:"
    echo "  kimi2 --version       查看版本"
    echo "  kimi2 --help          查看帮助"
    echo "  kimi2                 启动交互模式"
    echo "  kimi2 --prompt 'xxx'  执行单次任务"
    echo ""
    echo "配置目录: ~/.kimi2"
    echo "更新命令: 在 ${INSTALL_DIR} 目录下运行 git pull && uv sync --frozen"
    echo ""
else
    echo "❌ 安装验证失败"
    exit 1
fi
