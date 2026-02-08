#!/bin/bash
#
# Kimi CLI Manager - Version switcher for official and custom builds
#
# Usage:
#   kimi-cli-manager status              # Show current version
#   kimi-cli-manager use custom          # Switch to custom version
#   kimi-cli-manager use official        # Switch to official version
#   kimi-cli-manager update-official     # Update official repo from upstream
#   kimi-cli-manager merge-upstream      # Merge upstream into custom
#   kimi-cli-manager install-dev         # Install dev dependencies and test env
#

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CUSTOM_DIR="${KIMI_CUSTOM_DIR:-/Users/gaoxiang/Workspace2026/kimi-cli-custom}"
OFFICIAL_DIR="${KIMI_OFFICIAL_DIR:-/Users/gaoxiang/Workspace2026/kimi-cli}"
BACKUP_DIR="${HOME}/.kimi-cli-backup"
VENV_DIR="${HOME}/.kimi-cli-venv"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

# Get current kim version info
get_current_info() {
    local kimi_path version version_type
    
    if ! command -v kimi &> /dev/null; then
        echo "not_installed"
        return
    fi
    
    kimi_path=$(which kimi)
    version=$(kimi --version 2>/dev/null || echo "unknown")
    
    if [[ "$version" == *"custom"* ]] || [[ "$kimi_path" == *"custom"* ]]; then
        version_type="custom"
    else
        version_type="official"
    fi
    
    echo "${version_type}|${version}|${kimi_path}"
}

# Show status
cmd_status() {
    log_info "Checking Kimi CLI status..."
    
    local info
    info=$(get_current_info)
    
    if [[ "$info" == "not_installed" ]]; then
        log_warning "Kimi CLI is not installed"
        return 1
    fi
    
    IFS='|' read -r version_type version path <<< "$info"
    
    echo ""
    echo "Current Version:"
    echo "  Type:    $version_type"
    echo "  Version: $version"
    echo "  Path:    $path"
    echo ""
    
    # Check custom repo
    if [[ -d "$CUSTOM_DIR" ]]; then
        log_success "Custom repo found at: $CUSTOM_DIR"
        cd "$CUSTOM_DIR"
        if git rev-parse --git-dir &>/dev/null; then
            local branch commit
            branch=$(git branch --show-current 2>/dev/null || echo "unknown")
            commit=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
            echo "  Branch:  $branch"
            echo "  Commit:  $commit"
        fi
    else
        log_warning "Custom repo not found at: $CUSTOM_DIR"
    fi
    
    # Check official repo
    if [[ -d "$OFFICIAL_DIR" ]]; then
        log_success "Official repo found at: $OFFICIAL_DIR"
    else
        log_warning "Official repo not found at: $OFFICIAL_DIR"
    fi
    
    # Check backup
    if [[ -d "$BACKUP_DIR" ]]; then
        local backup_count
        backup_count=$(find "$BACKUP_DIR" -name "kimi-official-*" 2>/dev/null | wc -l)
        echo ""
        log_info "Backups found: $backup_count"
    fi
}

# Switch to custom version
cmd_use_custom() {
    log_info "Switching to custom version..."
    
    # Check if custom repo exists
    if [[ ! -d "$CUSTOM_DIR" ]]; then
        log_error "Custom repo not found at: $CUSTOM_DIR"
        echo "Clone it first: git clone <your-fork> $CUSTOM_DIR"
        return 1
    fi
    
    # Backup current version if it's official
    local current_info
    current_info=$(get_current_info)
    
    if [[ "$current_info" != "not_installed" ]]; then
        IFS='|' read -r version_type version _ <<< "$current_info"
        
        if [[ "$version_type" == "official" ]]; then
            mkdir -p "$BACKUP_DIR"
            local backup_name="kimi-official-$(date +%Y%m%d-%H%M%S)"
            
            if command -v kimi &> /dev/null; then
                cp "$(which kimi)" "$BACKUP_DIR/$backup_name" 2>/dev/null || true
                log_success "Backed up official version to: $BACKUP_DIR/$backup_name"
            fi
        fi
    fi
    
    # Install custom version
    log_info "Installing custom version from: $CUSTOM_DIR"
    cd "$CUSTOM_DIR"
    
    # Check if we're in a virtual environment
    if [[ -n "${VIRTUAL_ENV:-}" ]]; then
        pip install -e . --force-reinstall --no-deps
    else
        # Install to user site
        pip install --user -e . --force-reinstall --no-deps
    fi
    
    # Verify installation
    local new_version
    new_version=$(kimi --version 2>/dev/null || echo "unknown")
    
    if [[ "$new_version" == *"custom"* ]]; then
        log_success "Successfully switched to custom version: $new_version"
    else
        log_warning "Version doesn't contain 'custom': $new_version"
        log_info "You may need to restart your shell or check PATH"
    fi
}

# Switch to official version
cmd_use_official() {
    log_info "Switching to official version..."
    
    # Uninstall custom version
    pip uninstall kimi-cli -y 2>/dev/null || true
    
    # Install from PyPI
    log_info "Installing official version from PyPI..."
    pip install --user kimi-cli
    
    # Verify
    local new_version
    new_version=$(kimi --version 2>/dev/null || echo "unknown")
    
    if [[ "$new_version" != *"custom"* ]]; then
        log_success "Successfully switched to official version: $new_version"
    else
        log_warning "Version still contains 'custom': $new_version"
    fi
}

# Update official repo from upstream
cmd_update_official() {
    log_info "Updating official repo..."
    
    if [[ ! -d "$OFFICIAL_DIR" ]]; then
        log_error "Official repo not found at: $OFFICIAL_DIR"
        return 1
    fi
    
    cd "$OFFICIAL_DIR"
    
    # Check if it's a git repo
    if ! git rev-parse --git-dir &>/dev/null; then
        log_error "Not a git repository: $OFFICIAL_DIR"
        return 1
    fi
    
    # Fetch upstream
    log_info "Fetching from upstream..."
    git fetch upstream
    
    # Checkout main and merge
    git checkout main
    git merge upstream/main --no-edit
    
    log_success "Official repo updated"
}

# Merge upstream into custom
cmd_merge_upstream() {
    log_info "Merging upstream into custom repo..."
    
    if [[ ! -d "$CUSTOM_DIR" ]]; then
        log_error "Custom repo not found at: $CUSTOM_DIR"
        return 1
    fi
    
    cd "$CUSTOM_DIR"
    
    # Check if it's a git repo
    if ! git rev-parse --git-dir &>/dev/null; then
        log_error "Not a git repository: $CUSTOM_DIR"
        return 1
    fi
    
    # Fetch upstream
    log_info "Fetching from upstream..."
    git fetch upstream
    
    # Checkout custom branch and merge
    git checkout custom/main
    
    # Attempt merge
    if git merge upstream/main --no-edit; then
        log_success "Successfully merged upstream into custom/main"
    else
        log_error "Merge conflicts detected!"
        echo ""
        echo "Please resolve conflicts manually:"
        echo "  1. cd $CUSTOM_DIR"
        echo "  2. Resolve conflicts in the indicated files"
        echo "  3. git add <resolved-files>"
        echo "  4. git commit"
        echo ""
        return 1
    fi
}

# Install dev environment
cmd_install_dev() {
    log_info "Setting up development environment..."
    
    # Check if custom repo exists
    if [[ ! -d "$CUSTOM_DIR" ]]; then
        log_error "Custom repo not found at: $CUSTOM_DIR"
        return 1
    fi
    
    cd "$CUSTOM_DIR"
    
    # Install dev dependencies
    log_info "Installing development dependencies..."
    pip install -e ".[dev]"
    
    # Start Docker test environment
    if command -v docker-compose &> /dev/null || command -v docker &> /dev/null; then
        log_info "Starting Docker test environment..."
        
        if [[ -f "scripts/docker/docker-compose.test.yml" ]]; then
            docker-compose -f scripts/docker/docker-compose.test.yml up -d
            log_success "Docker test environment started"
            echo ""
            echo "Test mail servers:"
            echo "  SMTP: localhost:3025"
            echo "  IMAP: localhost:3143"
            echo "  Web UI: http://localhost:8080"
        else
            log_warning "Docker compose file not found"
        fi
    else
        log_warning "Docker not found, skipping test environment"
    fi
    
    log_success "Development environment ready!"
}

# Show help
cmd_help() {
    cat << 'EOF'
Kimi CLI Manager

USAGE:
    kimi-cli-manager <command> [options]

COMMANDS:
    status              Show current version and repo status
    use custom          Switch to custom (modified) version
    use official        Switch to official PyPI version
    update-official     Update official repo from upstream
    merge-upstream      Merge upstream changes into custom repo
    install-dev         Setup development environment and test services
    help                Show this help message

ENVIRONMENT VARIABLES:
    KIMI_CUSTOM_DIR     Path to custom repo (default: ~/Workspace2026/kimi-cli-custom)
    KIMI_OFFICIAL_DIR   Path to official repo (default: ~/Workspace2026/kimi-cli)

EXAMPLES:
    # Check current status
    kimi-cli-manager status

    # Switch to custom version
    kimi-cli-manager use custom

    # Update and merge upstream changes
    kimi-cli-manager update-official
    kimi-cli-manager merge-upstream

    # Setup development environment
    kimi-cli-manager install-dev
EOF
}

# Main
case "${1:-}" in
    status)
        cmd_status
        ;;
    use)
        case "${2:-}" in
            custom)
                cmd_use_custom
                ;;
            official)
                cmd_use_official
                ;;
            *)
                log_error "Unknown version: ${2:-}"
                echo "Usage: kimi-cli-manager use {custom|official}"
                exit 1
                ;;
        esac
        ;;
    update-official)
        cmd_update_official
        ;;
    merge-upstream)
        cmd_merge_upstream
        ;;
    install-dev)
        cmd_install_dev
        ;;
    help|--help|-h)
        cmd_help
        ;;
    *)
        log_error "Unknown command: ${1:-}"
        echo ""
        cmd_help
        exit 1
        ;;
esac
