"""Simplified email hook for personal use.

This module provides a simple email hook that sends notifications
to a single configured email address.
"""

from __future__ import annotations

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib
from jinja2 import Template
from loguru import logger

from kimi_cli.hooks.base import HookResult, TaskCompletionHook, TaskContext
from kimi_cli.mail.simple_config import get_simple_config


# Simple notification template
NOTIFICATION_TEMPLATE = """\
Kimi Task {{ "✓ Completed" if success else "✗ Failed" }}

{% if success %}
✓ Task completed successfully in {{ "%.1f" | format(duration) }} seconds
{% else %}
✗ Task failed after {{ "%.1f" | format(duration) }} seconds
{% endif %}
Working Directory: {{ work_dir }}
Session: {{ session_id[:8] }}

{{ result_summary }}

---
Reply to this email to continue the session.
"""


class SimpleEmailHook(TaskCompletionHook):
    """Simple email hook for personal notifications.
    
    This hook sends email notifications to the configured personal
    email address when tasks are completed.
    
    Configuration via environment variables:
        export KIMI_EMAIL_ADDRESS="your@gmail.com"
        export KIMI_EMAIL_PASSWORD="your-app-password"
    
    Or configure directly in code.
    """
    
    def __init__(self, config=None):
        """Initialize with simple config."""
        self.config = config or get_simple_config()
        self.template = Template(NOTIFICATION_TEMPLATE)
    
    @property
    def name(self) -> str:
        return "simple-email"
    
    @property
    def enabled(self) -> bool:
        return self.config.is_configured()
    
    def should_trigger(self, context: TaskContext) -> bool:
        """Only trigger if configured."""
        if not self.config.is_configured():
            return False
        
        if context.success and not self.config.notify_on_success:
            return False
        
        if not context.success and not self.config.notify_on_failure:
            return False
        
        return True
    
    async def on_complete(self, context: TaskContext) -> HookResult:
        """Send notification email."""
        try:
            # Validate config
            is_valid, error = self.config.validate()
            if not is_valid:
                logger.warning(f"Email config invalid: {error}")
                return HookResult(success=False, error=error)
            
            # Build message
            template_data = {
                "success": context.success,
                "duration": context.duration,
                "work_dir": str(context.session.work_dir),
                "session_id": context.session.id,
                "result_summary": context.result_summary,
            }
            
            text_content = self.template.render(**template_data)
            
            # Create email
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"Kimi: Task {'Completed' if context.success else 'Failed'}"
            msg["From"] = self.config.email
            msg["To"] = self.config.notify_email  # Send to notify_email
            msg["Reply-To"] = self.config.email  # Reply to sender
            
            msg.attach(MIMEText(text_content, "plain", "utf-8"))
            
            # Send via SMTP
            logger.debug(f"Sending email to {self.config.notify_email}")
            
            # Use direct TLS for port 465 (QQ), STARTTLS for port 587 (Gmail)
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            if self.config.smtp_port == 465:
                # Port 465 - Direct TLS (QQ, 163)
                smtp = aiosmtplib.SMTP(
                    hostname=self.config.smtp_host,
                    port=self.config.smtp_port,
                    use_tls=True,
                    tls_context=ssl_context,
                )
                await smtp.connect()
            else:
                # Port 587 - STARTTLS (Gmail, Outlook)
                smtp = aiosmtplib.SMTP(
                    hostname=self.config.smtp_host,
                    port=self.config.smtp_port,
                    use_tls=False,
                )
                await smtp.connect()
                await smtp.starttls(tls_context=ssl_context)
            
            await smtp.login(self.config.email, self.config.password)
            await smtp.send_message(msg)
            await smtp.quit()
            
            logger.info(f"Notification sent to {self.config.email}")
            return HookResult(success=True)
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return HookResult(success=False, error=str(e))


# Backward compatibility
EmailHook = SimpleEmailHook
