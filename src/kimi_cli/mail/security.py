"""Security validation for email processing.

This module provides security checks for inbound emails including
whitelist validation, command filtering, and sandbox restrictions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger

from kimi_cli.mail.models import Email, TaskRequest, TaskType


@dataclass
class WhitelistEntry:
    """A whitelisted email address with specific permissions.
    
    Attributes:
        email: The email address.
        name: Optional name/identifier for this entry.
        dkim_required: Whether DKIM verification is required.
        allowed_commands: List of allowed slash commands (empty = all).
        denied_commands: List of denied slash commands.
        allowed_working_dirs: Allowed working directories.
        max_attachment_size: Maximum attachment size in bytes.
        auto_execute: Whether to auto-execute tasks from this sender.
    """
    email: str
    name: str = ""
    dkim_required: bool = True
    allowed_commands: list[str] = field(default_factory=list)
    denied_commands: list[str] = field(default_factory=lambda: [
        "/git push --force",
        "/shell rm -rf",
        "/shell sudo",
    ])
    allowed_working_dirs: list[Path] = field(default_factory=list)
    max_attachment_size: int = 10 * 1024 * 1024  # 10MB
    auto_execute: bool = False


@dataclass
class SecurityConfig:
    """Configuration for security validation.
    
    Attributes:
        enabled: Whether security checks are enabled.
        whitelist: List of whitelisted entries.
        block_patterns: Regex patterns to block in content.
        max_total_attachment_size: Max total size for all attachments.
        require_auto_prefix: Require [AUTO] prefix for processing.
        sandbox_mode: Whether to run in sandbox mode.
    """
    enabled: bool = True
    whitelist: list[WhitelistEntry] = field(default_factory=list)
    block_patterns: list[str] = field(default_factory=lambda: [
        r"rm\s+-rf\s+/",
        r"curl\s+.*\|\s*bash",
        r"curl\s+.*\|\s*sh",
        r"wget\s+.*\|\s*bash",
        r"wget\s+.*\|\s*sh",
        r"eval\s*\(",
        r"exec\s*\(",
        r"os\.system\s*\(",
        r"subprocess\.call\s*\(",
    ])
    max_total_attachment_size: int = 50 * 1024 * 1024  # 50MB
    require_auto_prefix: bool = True
    sandbox_mode: bool = True


class SecurityValidator:
    """Validates emails and tasks for security compliance.
    
    This class performs various security checks on inbound emails
    to ensure they meet the configured security policy.
    
    Example:
        ```python
        config = SecurityConfig(
            whitelist=[WhitelistEntry(email="trusted@example.com")]
        )
        validator = SecurityValidator(config)
        
        if validator.validate_email(email):
            task = extract_task(email)
            if validator.validate_task(task, email):
                # Safe to process
                pass
        ```
    """
    
    # Dangerous shell commands that should be blocked
    DANGEROUS_COMMANDS = {
        "rm -rf /",
        "rm -rf /*",
        "> /dev/sda",
        "dd if=/dev/zero",
        "mkfs.",
        "fdisk",
        "format c:",
    }
    
    # Read-only commands that are safe
    READONLY_COMMANDS = {
        "/review",
        "/doc",
        "/explain",
        "/search",
        "/help",
    }
    
    def __init__(self, config: SecurityConfig | None = None) -> None:
        """Initialize the security validator.
        
        Args:
            config: Security configuration. Uses defaults if None.
        """
        self.config = config or SecurityConfig()
        self._block_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.config.block_patterns
        ]
    
    def validate_email(self, email: Email) -> bool:
        """Validate an email for security compliance.
        
        Performs the following checks:
        1. Whitelist validation
        2. [AUTO] prefix check (if required)
        3. Content pattern matching
        
        Args:
            email: The email to validate.
            
        Returns:
            True if email passes all checks.
        """
        if not self.config.enabled:
            logger.debug("Security checks disabled, allowing email")
            return True
        
        # Check whitelist
        if not self._check_whitelist(email):
            logger.warning(
                f"Email from {email.from_address} rejected: not in whitelist"
            )
            return False
        
        # Check [AUTO] prefix
        if self.config.require_auto_prefix and not email.is_auto_task():
            logger.info(
                f"Email from {email.from_address} ignored: missing [AUTO] prefix"
            )
            return False
        
        # Check content for dangerous patterns
        if self._check_dangerous_patterns(email):
            logger.warning(
                f"Email from {email.from_address} rejected: dangerous content detected"
            )
            return False
        
        # Check attachment sizes
        if not self._check_attachment_sizes(email):
            logger.warning(
                f"Email from {email.from_address} rejected: attachments too large"
            )
            return False
        
        logger.debug(f"Email from {email.from_address} passed security checks")
        return True
    
    def validate_task(
        self,
        task: TaskRequest,
        email: Email,
    ) -> tuple[bool, str]:
        """Validate a task request for security compliance.
        
        Args:
            task: The task to validate.
            email: The source email.
            
        Returns:
            Tuple of (is_valid, reason).
        """
        if not self.config.enabled:
            return True, ""
        
        # Get whitelist entry for this sender
        entry = self._get_whitelist_entry(email.from_address)
        if not entry:
            return False, "Sender not in whitelist"
        
        # Check command permissions
        command = task.to_command().split()[0] if task.to_command() else ""
        
        if entry.denied_commands:
            for denied in entry.denied_commands:
                if denied.lower() in command.lower():
                    return False, f"Command '{denied}' is not allowed"
        
        if entry.allowed_commands:
            # Specific commands are allowed
            allowed = [cmd.lower() for cmd in entry.allowed_commands]
            if command.lower() not in allowed:
                # Check if it's a read-only command (always allowed)
                if command not in self.READONLY_COMMANDS:
                    return False, f"Command '{command}' not in allowed list"
        
        # Check working directory restrictions
        if entry.allowed_working_dirs and task.working_dir:
            task_path = Path(task.working_dir).resolve()
            allowed = False
            for allowed_dir in entry.allowed_working_dirs:
                try:
                    allowed_path = Path(allowed_dir).resolve()
                    if task_path == allowed_path or allowed_path in task_path.parents:
                        allowed = True
                        break
                except Exception:
                    continue
            if not allowed:
                return False, f"Working directory {task.working_dir} not allowed"
        
        # Auto-execute check
        if task.auto_execute and not entry.auto_execute:
            return False, "Auto-execute not allowed for this sender"
        
        return True, ""
    
    def should_require_confirmation(self, task: TaskRequest) -> tuple[bool, str]:
        """Determine if a task requires explicit confirmation.
        
        Args:
            task: The task to check.
            
        Returns:
            Tuple of (requires_confirmation, reason).
        """
        # Read-only tasks don't need confirmation
        if task.is_readonly():
            return False, ""
        
        # Tasks with file modifications need confirmation
        if task.task_type in (TaskType.CODE, TaskType.REFACTOR, TaskType.FIX):
            return True, "Task will modify files"
        
        # Tasks with many attachments need confirmation
        if len(task.attachments) > 5:
            return True, f"Many attachments ({len(task.attachments)} files)"
        
        # Large attachments need confirmation
        total_size = sum(att.size for att in task.attachments)
        if total_size > 1024 * 1024:  # 1MB
            return True, f"Large attachments ({total_size / 1024 / 1024:.1f}MB)"
        
        return False, ""
    
    def _check_whitelist(self, email: Email) -> bool:
        """Check if sender is in whitelist.
        
        Args:
            email: The email to check.
            
        Returns:
            True if sender is whitelisted.
        """
        if not self.config.whitelist:
            # No whitelist = allow all (not recommended)
            return True
        
        sender = email.from_address.lower()
        for entry in self.config.whitelist:
            if entry.email.lower() == sender:
                return True
        
        return False
    
    def _get_whitelist_entry(self, email_address: str) -> WhitelistEntry | None:
        """Get whitelist entry for an email address.
        
        Args:
            email_address: The email address.
            
        Returns:
            WhitelistEntry if found, None otherwise.
        """
        sender = email_address.lower()
        for entry in self.config.whitelist:
            if entry.email.lower() == sender:
                return entry
        return None
    
    def _check_dangerous_patterns(self, email: Email) -> bool:
        """Check email content for dangerous patterns.
        
        Args:
            email: The email to check.
            
        Returns:
            True if dangerous patterns found.
        """
        content = f"{email.subject}\n{email.body_text}"
        
        for pattern in self._block_patterns:
            if pattern.search(content):
                logger.warning(f"Dangerous pattern matched: {pattern.pattern}")
                return True
        
        return False
    
    def _check_attachment_sizes(self, email: Email) -> bool:
        """Check if attachment sizes are within limits.
        
        Args:
            email: The email to check.
            
        Returns:
            True if sizes are acceptable.
        """
        total_size = sum(att.size for att in email.attachments)
        
        if total_size > self.config.max_total_attachment_size:
            logger.warning(
                f"Total attachment size {total_size} exceeds limit "
                f"{self.config.max_total_attachment_size}"
            )
            return False
        
        # Check per-sender limits
        entry = self._get_whitelist_entry(email.from_address)
        if entry:
            for att in email.attachments:
                if att.size > entry.max_attachment_size:
                    logger.warning(
                        f"Attachment {att.filename} size {att.size} exceeds "
                        f"limit {entry.max_attachment_size}"
                    )
                    return False
        
        return True
    
    def sanitize_command(self, command: str) -> str:
        """Sanitize a command string.
        
        Removes potentially dangerous elements from commands.
        
        Args:
            command: The command to sanitize.
            
        Returns:
            Sanitized command.
        """
        # Remove shell operators that could be dangerous
        sanitized = command
        
        # Block command chaining
        dangerous_ops = [";", "&&", "||", "|", "`", "$()"]
        for op in dangerous_ops:
            if op in sanitized:
                logger.warning(f"Removed dangerous operator '{op}' from command")
                sanitized = sanitized.replace(op, " ")
        
        return sanitized.strip()
