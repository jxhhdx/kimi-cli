#!/bin/bash
#
# Install script for kimi-cli-custom (modified version)
#
# This script:
# 1. Backs up the current official version (if installed)
# 2. Installs the custom version from source
# 3. Creates initial configuration
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${HOME}/.kimi-cli-backup"
KIMI_CONFIG_DIR="${HOME}/.kimi"

echo "=========================================="
echo "Kimi CLI Custom - Installation Script"
echo "=========================================="
echo ""

# Check Python version
log_info "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
REQUIRED_VERSION="3.12"

if [[ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]]; then
    log_error "Python $REQUIRED_VERSION+ is required, found $PYTHON_VERSION"
    exit 1
fi

log_success "Python version check passed: $PYTHON_VERSION"

# Detect current installation
log_info "Detecting current Kimi CLI installation..."

if command -v kimi &> /dev/null; then
    CURRENT_PATH=$(which kimi)
    CURRENT_VERSION=$(kimi --version 2>/dev/null || echo "unknown")
    
    echo "  Current: $CURRENT_VERSION"
    echo "  Path:    $CURRENT_PATH"
    
    # Backup if it's official
    if [[ "$CURRENT_VERSION" != *"custom"* ]]; then
        mkdir -p "$BACKUP_DIR"
        BACKUP_NAME="kimi-official-$(date +%Y%m%d-%H%M%S)"
        cp "$CURRENT_PATH" "$BACKUP_DIR/$BACKUP_NAME"
        log_success "Backed up official version to: $BACKUP_DIR/$BACKUP_NAME"
    else
        log_warning "Custom version already installed, will overwrite"
    fi
else
    log_info "No existing Kimi CLI installation found"
fi

# Install dependencies
log_info "Installing dependencies..."

pip install --quiet \
    aiosmtplib>=3.0.0 \
    aioimaplib>=1.1.0 \
    email-validator>=2.0.0

log_success "Dependencies installed"

# Install custom version
log_info "Installing custom Kimi CLI from: $REPO_DIR"

cd "$REPO_DIR"

# Check if in virtual environment
if [[ -n "${VIRTUAL_ENV:-}" ]]; then
    pip install -e . --force-reinstall
else
    pip install --user -e . --force-reinstall
fi

# Verify installation
log_info "Verifying installation..."

NEW_VERSION=$(kimi --version 2>/dev/null || echo "unknown")
NEW_PATH=$(which kimi)

if [[ "$NEW_VERSION" == *"custom"* ]]; then
    log_success "Installation successful!"
    echo ""
    echo "Version: $NEW_VERSION"
    echo "Path:    $NEW_PATH"
else
    log_warning "Installation may have issues"
    echo "Version: $NEW_VERSION (expected to contain 'custom')"
    echo "Path:    $NEW_PATH"
fi

# Create initial configuration
log_info "Creating initial configuration..."

mkdir -p "$KIMI_CONFIG_DIR"

# Check if config already exists
if [[ -f "$KIMI_CONFIG_DIR/config.toml" ]]; then
    log_warning "Config already exists at: $KIMI_CONFIG_DIR/config.toml"
    log_info "New options have been added. See docs for configuration details."
else
    cat > "$KIMI_CONFIG_DIR/config.toml" << 'EOF'
# Kimi CLI Custom Configuration
# Documentation: https://github.com/yourusername/kimi-cli-custom

[hooks.task_completion]
# Enable task completion notifications
enabled = false

# Example: Email notification
# [[hooks.task_completion.channels]]
# type = "email"
# name = "gmail-notify"
# enabled = true
# smtp_host = "smtp.gmail.com"
# smtp_port = 587
# username = "your-email@gmail.com"
# password = "${GMAIL_APP_PASSWORD}"  # Use environment variable
# to_addrs = ["your-phone@txt.att.net"]
# use_html = false

# Example: Webhook notification (Slack)
# [[hooks.task_completion.channels]]
# type = "webhook"
# name = "slack-notify"
# enabled = true
# url = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
# payload_template = """
# {"text": "Kimi task {{ 'completed' if success else 'failed' }}: {{ result_summary[:100] }}"}
# """

[inbound_mail]
# Enable email inbound processing
enabled = false

# IMAP server configuration
# imap_host = "imap.gmail.com"
# imap_port = 993
# username = "your-email@gmail.com"
# password = "${GMAIL_APP_PASSWORD}"
# mailbox = "INBOX"

# Security settings
# require_auto_prefix = true  # Only process emails with [AUTO] prefix
# sandbox_mode = true

# Whitelist (only these senders can trigger tasks)
# [[inbound_mail.whitelist]]
# email = "trusted-colleague@company.com"
# auto_execute = false  # Require confirmation for this sender
#
# [[inbound_mail.whitelist]]
# email = "your-second-email@gmail.com"
# auto_execute = true   # Auto-execute read-only tasks
EOF

    log_success "Created initial config at: $KIMI_CONFIG_DIR/config.toml"
fi

# Create environment template
cat > "$KIMI_CONFIG_DIR/.env.example" << 'EOF'
# Kimi CLI Custom - Environment Variables
# Copy this file to .env and fill in your values

# Email notification settings
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_TO=receiver@example.com

# Email inbound settings
KIMI_EMAIL_USERNAME=your-email@gmail.com
KIMI_EMAIL_PASSWORD=your-app-password
KIMI_MAIL_WHITELIST=trusted@example.com,colleague@company.com

# API settings (if needed)
KIMI_API_KEY=your-api-key
EOF

echo ""
echo "=========================================="
log_success "Installation complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Configure notifications (optional):"
echo "   Edit: ~/.kimi/config.toml"
echo ""
echo "2. Set up environment variables:"
echo "   cp ~/.kimi/.env.example ~/.kimi/.env"
echo "   # Edit ~/.kimi/.env with your credentials"
echo ""
echo "3. Test the installation:"
echo "   kimi --version"
echo "   kimi mail test  # If using email features"
echo ""
echo "4. To switch back to official version:"
echo "   kimi-cli-manager use official"
echo ""
echo "For more information:"
echo "   kimi-cli-manager help"
echo ""
