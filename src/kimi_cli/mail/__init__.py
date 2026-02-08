"""Email inbound processing system for kimi-cli.

This module provides functionality to receive and process emails,
extracting tasks from attachments and executing them.
"""

from __future__ import annotations

from kimi_cli.mail.client import IMAPClient
from kimi_cli.mail.models import Email, EmailAttachment, TaskRequest
from kimi_cli.mail.parser import EmailParser
from kimi_cli.mail.security import SecurityValidator

__all__ = [
    "IMAPClient",
    "Email",
    "EmailAttachment",
    "TaskRequest",
    "EmailParser",
    "SecurityValidator",
]
