"""Email notification hook using SMTP.

This module provides the EmailHook class for sending email notifications
when tasks are completed.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

import aiosmtplib
from jinja2 import Template
from loguru import logger

from kimi_cli.hooks.base import HookConfig, HookResult, TaskCompletionHook, TaskContext


# Default email template
DEFAULT_EMAIL_TEMPLATE = """\
Subject: Kimi CLI Task {{ "Completed" if success else "Failed" }}

Task Execution Report
=====================

Status: {{ "✓ SUCCESS" if success else "✗ FAILED" }}
Duration: {{ "%.1f" | format(duration) }} seconds
Working Directory: {{ work_dir }}
Session: {{ session_id }}
{% if model %}Model: {{ model }}{% endif %}

Summary
-------
{{ result_summary }}

{% if not success and error %}
Error Details
-------------
{{ error }}
{% endif %}

---
Sent by Kimi CLI Custom
"""

# HTML email template
HTML_EMAIL_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: {{ "#4CAF50" if success else "#f44336" }}; color: white; padding: 10px; }
        .content { margin-top: 20px; }
        .field { margin: 10px 0; }
        .label { font-weight: bold; }
        pre { background: #f5f5f5; padding: 10px; overflow-x: auto; }
    </style>
</head>
<body>
    <div class="header">
        <h2>Task {{ "Completed" if success else "Failed" }}</h2>
    </div>
    <div class="content">
        <div class="field">
            <span class="label">Status:</span> 
            <span style="color: {{ "green" if success else "red" }};">
                {{ "✓ SUCCESS" if success else "✗ FAILED" }}
            </span>
        </div>
        <div class="field">
            <span class="label">Duration:</span> {{ "%.1f" | format(duration) }} seconds
        </div>
        <div class="field">
            <span class="label">Working Directory:</span> {{ work_dir }}
        </div>
        <div class="field">
            <span class="label">Session:</span> {{ session_id }}
        </div>
        {% if model %}
        <div class="field">
            <span class="label">Model:</span> {{ model }}
        </div>
        {% endif %}
        <div class="field">
            <span class="label">Summary:</span>
            <pre>{{ result_summary }}</pre>
        </div>
        {% if not success and error %}
        <div class="field">
            <span class="label">Error:</span>
            <pre style="color: red;">{{ error }}</pre>
        </div>
        {% endif %}
    </div>
    <hr>
    <p style="color: #666; font-size: 12px;">Sent by Kimi CLI Custom</p>
</body>
</html>
"""


@dataclass
class EmailConfig:
    """Configuration for email hook.
    
    Attributes:
        smtp_host: SMTP server hostname.
        smtp_port: SMTP server port (default: 587 for TLS).
        username: SMTP authentication username.
        password: SMTP authentication password.
        from_addr: From email address (defaults to username).
        to_addrs: List of recipient email addresses.
        use_tls: Whether to use TLS encryption (default: True).
        template: Custom email template (optional).
        html_template: Custom HTML template (optional).
        use_html: Whether to send HTML emails (default: False).
    """
    smtp_host: str
    smtp_port: int = 587
    username: str = ""
    password: str = ""
    from_addr: str = ""
    to_addrs: list[str] | None = None
    use_tls: bool = True
    template: str | None = None
    html_template: str | None = None
    use_html: bool = False
    
    def __post_init__(self) -> None:
        """Set defaults and resolve environment variables."""
        if not self.username:
            self.username = os.environ.get("SMTP_USERNAME", "")
        
        if not self.password:
            self.password = os.environ.get("SMTP_PASSWORD", "")
        
        if not self.from_addr:
            self.from_addr = self.username
        
        if self.to_addrs is None:
            to_env = os.environ.get("SMTP_TO", "")
            self.to_addrs = [addr.strip() for addr in to_env.split(",") if addr.strip()]
    
    @classmethod
    def from_hook_config(cls, config: HookConfig) -> EmailConfig:
        """Create EmailConfig from generic HookConfig.
        
        Args:
            config: The generic hook configuration.
            
        Returns:
            An EmailConfig instance.
        """
        cfg = config.config
        return cls(
            smtp_host=cfg.get("smtp_host", "localhost"),
            smtp_port=cfg.get("smtp_port", 587),
            username=cfg.get("username", ""),
            password=cfg.get("password", ""),
            from_addr=cfg.get("from_addr", ""),
            to_addrs=cfg.get("to_addrs"),
            use_tls=cfg.get("use_tls", True),
            template=cfg.get("template"),
            html_template=cfg.get("html_template"),
            use_html=cfg.get("use_html", False),
        )


class EmailHook(TaskCompletionHook):
    """Hook that sends email notifications via SMTP.
    
    Example configuration:
        ```toml
        [[hooks.task_completion.channels]]
        type = "email"
        name = "gmail-notify"
        enabled = true
        smtp_host = "smtp.gmail.com"
        smtp_port = 587
        username = "your@gmail.com"
        password = "${GMAIL_APP_PASSWORD}"
        to_addrs = ["receiver@example.com"]
        use_html = true
        ```
    """
    
    def __init__(self, config: HookConfig) -> None:
        """Initialize the email hook.
        
        Args:
            config: Configuration for this hook.
        """
        super().__init__(config)
        self.email_config = EmailConfig.from_hook_config(config)
        self.text_template = Template(
            config.config.get("template") or DEFAULT_EMAIL_TEMPLATE
        )
        self.html_template = Template(
            config.config.get("html_template") or HTML_EMAIL_TEMPLATE
        )
    
    async def on_complete(self, context: TaskContext) -> HookResult:
        """Send an email notification when a task completes.
        
        Args:
            context: The task completion context.
            
        Returns:
            A HookResult indicating whether the email was sent successfully.
        """
        try:
            # Validate configuration
            if not self.email_config.to_addrs:
                return HookResult(
                    success=False,
                    error="No recipient addresses configured",
                )
            
            if not self.email_config.from_addr:
                return HookResult(
                    success=False,
                    error="No sender address configured",
                )
            
            # Build email content
            template_data = {
                "success": context.success,
                "duration": context.duration,
                "work_dir": str(context.session.work_dir),
                "session_id": context.session.id,
                "model": context.metadata.get("model", "unknown"),
                "result_summary": context.result_summary,
                "error": context.metadata.get("error", ""),
            }
            
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"Kimi CLI Task {'Completed' if context.success else 'Failed'}"
            msg["From"] = self.email_config.from_addr
            msg["To"] = ", ".join(self.email_config.to_addrs)
            
            # Add text part
            text_content = self.text_template.render(**template_data)
            msg.attach(MIMEText(text_content, "plain", "utf-8"))
            
            # Add HTML part if enabled
            if self.email_config.use_html:
                html_content = self.html_template.render(**template_data)
                msg.attach(MIMEText(html_content, "html", "utf-8"))
            
            # Send email
            logger.debug(
                f"Sending email to {self.email_config.to_addrs} "
                f"via {self.email_config.smtp_host}:{self.email_config.smtp_port}"
            )
            
            async with aiosmtplib.SMTP(
                hostname=self.email_config.smtp_host,
                port=self.email_config.smtp_port,
                use_tls=self.email_config.use_tls,
            ) as smtp:
                if self.email_config.username and self.email_config.password:
                    await smtp.login(
                        self.email_config.username,
                        self.email_config.password,
                    )
                
                await smtp.send_message(msg)
            
            logger.info(f"Email notification sent to {self.email_config.to_addrs}")
            return HookResult(success=True)
            
        except aiosmtplib.SMTPException as e:
            logger.error(f"SMTP error sending email: {e}")
            return HookResult(success=False, error=f"SMTP error: {e}")
        except Exception as e:
            logger.exception(f"Failed to send email: {e}")
            return HookResult(success=False, error=f"Failed to send email: {e}")
