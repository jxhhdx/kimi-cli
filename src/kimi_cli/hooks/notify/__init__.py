"""Notification hooks for task completion.

This module provides various notification channels:
- Email via SMTP
- Webhook (generic HTTP endpoint)
- DingTalk (钉钉)
- WeChat Work (企业微信)
"""

from __future__ import annotations

from kimi_cli.hooks.notify.email import EmailHook
from kimi_cli.hooks.notify.webhook import WebhookHook

__all__ = [
    "EmailHook",
    "WebhookHook",
]
