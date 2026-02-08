"""Simplified email configuration for personal use.

This module provides a simple configuration for single-user email
notification and response handling.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class SimpleMailConfig:
    """Simple email configuration for single user.
    
    All settings can be provided via environment variables or
    configured directly.
    
    Example:
        ```python
        # Via environment variables
        export KIMI_EMAIL_ADDRESS="your@gmail.com"
        export KIMI_EMAIL_PASSWORD="your-app-password"
        
        # Or create directly
        config = SimpleMailConfig(
            email="your@gmail.com",
            password="your-password"
        )
        ```
    """
    
    # User's email address (for both sending and receiving)
    email: str = ""
    password: str = ""
    
    # SMTP settings (for sending notifications)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_use_tls: bool = True
    
    # IMAP settings (for receiving replies)
    imap_host: str = ""
    imap_port: int = 993
    imap_use_ssl: bool = True
    
    # Notification settings
    notify_on_success: bool = True
    notify_on_failure: bool = True
    
    def __post_init__(self):
        """Load from environment if not set."""
        if not self.email:
            self.email = os.environ.get("KIMI_EMAIL_ADDRESS", "")
        if not self.password:
            self.password = os.environ.get("KIMI_EMAIL_PASSWORD", "")
        
        # Auto-detect SMTP/IMAP settings based on email domain
        if self.email and not self.smtp_host:
            self._auto_configure()
    
    def _auto_configure(self):
        """Auto-configure based on email domain."""
        domain = self.email.split("@")[-1].lower()
        
        configs = {
            "gmail.com": {
                "smtp_host": "smtp.gmail.com",
                "smtp_port": 587,
                "imap_host": "imap.gmail.com",
                "imap_port": 993,
            },
            "qq.com": {
                "smtp_host": "smtp.qq.com",
                "smtp_port": 587,
                "imap_host": "imap.qq.com",
                "imap_port": 993,
            },
            "163.com": {
                "smtp_host": "smtp.163.com",
                "smtp_port": 465,
                "imap_host": "imap.163.com",
                "imap_port": 993,
            },
            "outlook.com": {
                "smtp_host": "smtp.office365.com",
                "smtp_port": 587,
                "imap_host": "outlook.office365.com",
                "imap_port": 993,
            },
            "hotmail.com": {
                "smtp_host": "smtp.office365.com",
                "smtp_port": 587,
                "imap_host": "outlook.office365.com",
                "imap_port": 993,
            },
        }
        
        if domain in configs:
            cfg = configs[domain]
            self.smtp_host = cfg["smtp_host"]
            self.smtp_port = cfg["smtp_port"]
            self.imap_host = cfg["imap_host"]
            self.imap_port = cfg["imap_port"]
    
    def is_configured(self) -> bool:
        """Check if configuration is complete."""
        return bool(
            self.email and 
            self.password and 
            self.smtp_host and 
            self.imap_host
        )
    
    def validate(self) -> tuple[bool, str]:
        """Validate configuration.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.email:
            return False, "Email address not configured"
        if not self.password:
            return False, "Email password not configured"
        if not self.smtp_host:
            return False, "SMTP host not configured (unknown email provider)"
        if not self.imap_host:
            return False, "IMAP host not configured (unknown email provider)"
        return True, ""


def get_simple_config() -> SimpleMailConfig:
    """Get configuration from environment.
    
    Returns:
        SimpleMailConfig instance with settings from environment variables.
    """
    return SimpleMailConfig()
