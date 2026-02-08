"""Email parser for extracting content and attachments.

This module provides functionality to parse raw email data into
structured Email objects.
"""

from __future__ import annotations

import email
import re
from email.message import Message
from email.policy import default
from pathlib import Path
from typing import Any

from loguru import logger

from kimi_cli.mail.models import Email, EmailAttachment, TaskRequest, TaskType


class EmailParser:
    """Parser for email messages.
    
    This class provides methods to parse raw email bytes or strings
    into structured Email objects.
    """
    
    # Patterns for extracting task type from subject
    TASK_PATTERNS = {
        TaskType.REVIEW: re.compile(r"review|检查|审查", re.IGNORECASE),
        TaskType.CODE: re.compile(r"code|实现|编写|create", re.IGNORECASE),
        TaskType.REFACTOR: re.compile(r"refactor|重构|优化", re.IGNORECASE),
        TaskType.FIX: re.compile(r"fix|修复|fix.*bug|debug", re.IGNORECASE),
        TaskType.DOC: re.compile(r"doc|文档|documentation|comment", re.IGNORECASE),
        TaskType.TEST: re.compile(r"test|测试|unittest", re.IGNORECASE),
    }
    
    @classmethod
    def parse_bytes(cls, data: bytes) -> Email:
        """Parse email from bytes.
        
        Args:
            data: Raw email bytes.
            
        Returns:
            Parsed Email object.
        """
        msg = email.message_from_bytes(data, policy=default)
        return cls._parse_message(msg)
    
    @classmethod
    def parse_string(cls, data: str) -> Email:
        """Parse email from string.
        
        Args:
            data: Raw email string.
            
        Returns:
            Parsed Email object.
        """
        msg = email.message_from_string(data, policy=default)
        return cls._parse_message(msg)
    
    @classmethod
    def _parse_message(cls, msg: Message) -> Email:
        """Parse an email.message.Message object.
        
        Args:
            msg: The message object.
            
        Returns:
            Parsed Email object.
        """
        # Extract basic headers
        message_id = msg.get("Message-ID", "")
        subject = msg.get("Subject", "")
        
        # Parse From header
        from_header = msg.get("From", "")
        from_address, from_name = cls._parse_address(from_header)
        
        # Parse To header
        to_header = msg.get("To", "")
        to_addresses = cls._parse_address_list(to_header)
        
        # Parse date
        date_str = msg.get("Date")
        date = cls._parse_date(date_str) if date_str else None
        
        # Extract all headers
        headers = {k: v for k, v in msg.items()}
        
        # Parse body and attachments
        body_text, body_html, attachments = cls._extract_parts(msg)
        
        return Email(
            message_id=message_id,
            subject=subject,
            from_address=from_address,
            from_name=from_name,
            to_addresses=to_addresses,
            date=date,
            body_text=body_text,
            body_html=body_html,
            attachments=attachments,
            headers=headers,
        )
    
    @classmethod
    def _parse_address(cls, addr_str: str) -> tuple[str, str]:
        """Parse an email address string.
        
        Args:
            addr_str: Address string like "Name <email@example.com>"
            
        Returns:
            Tuple of (email, name).
        """
        import email.utils
        
        parsed = email.utils.parseaddr(addr_str)
        return parsed[1], parsed[0]
    
    @classmethod
    def _parse_address_list(cls, addr_str: str) -> list[str]:
        """Parse a list of email addresses.
        
        Args:
            addr_str: Comma-separated address string.
            
        Returns:
            List of email addresses.
        """
        import email.utils
        
        addresses = email.utils.getaddresses([addr_str])
        return [addr for name, addr in addresses if addr]
    
    @classmethod
    def _parse_date(cls, date_str: str) -> Any:
        """Parse a date string.
        
        Args:
            date_str: Date string from email header.
            
        Returns:
            datetime object or None.
        """
        import email.utils
        from datetime import datetime
        
        try:
            parsed = email.utils.parsedate_to_datetime(date_str)
            return parsed
        except Exception as e:
            logger.debug(f"Failed to parse date '{date_str}': {e}")
            return None
    
    @classmethod
    def _extract_parts(cls, msg: Message) -> tuple[str, str, list[EmailAttachment]]:
        """Extract body parts and attachments from message.
        
        Args:
            msg: The message object.
            
        Returns:
            Tuple of (text_body, html_body, attachments).
        """
        text_body = ""
        html_body = ""
        attachments = []
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = part.get("Content-Disposition", "")
                
                # Skip multipart container
                if content_type.startswith("multipart/"):
                    continue
                
                # Check if this is an attachment
                is_attachment = (
                    "attachment" in content_disposition or
                    part.get_filename() is not None
                )
                
                if is_attachment:
                    # Extract attachment
                    filename = part.get_filename() or "unnamed"
                    payload = part.get_payload(decode=True) or b""
                    
                    attachment = EmailAttachment(
                        filename=filename,
                        content=payload,
                        content_type=content_type,
                    )
                    attachments.append(attachment)
                    
                elif content_type == "text/plain":
                    # Plain text body
                    charset = part.get_content_charset() or "utf-8"
                    try:
                        text_body = part.get_payload(decode=True).decode(charset)
                    except Exception as e:
                        logger.debug(f"Failed to decode text body: {e}")
                        text_body = part.get_payload() or ""
                        
                elif content_type == "text/html":
                    # HTML body
                    charset = part.get_content_charset() or "utf-8"
                    try:
                        html_body = part.get_payload(decode=True).decode(charset)
                    except Exception as e:
                        logger.debug(f"Failed to decode HTML body: {e}")
                        html_body = part.get_payload() or ""
        else:
            # Single part message
            content_type = msg.get_content_type()
            charset = msg.get_content_charset() or "utf-8"
            
            try:
                payload = msg.get_payload(decode=True)
                if payload:
                    content = payload.decode(charset)
                    if content_type == "text/html":
                        html_body = content
                    else:
                        text_body = content
            except Exception as e:
                logger.debug(f"Failed to decode single part: {e}")
                text_body = msg.get_payload() or ""
        
        return text_body, html_body, attachments
    
    @classmethod
    def extract_task(cls, email: Email) -> TaskRequest:
        """Extract a task request from an email.
        
        This method analyzes the email subject and body to determine
        the type of task being requested.
        
        Args:
            email: The parsed email.
            
        Returns:
            A TaskRequest object.
        """
        subject = email.subject
        body = email.body_text or email.body_html
        
        # Remove [AUTO] prefix from subject
        clean_subject = re.sub(r"^\[AUTO\]\s*", "", subject, flags=re.IGNORECASE)
        
        # Try to determine task type from subject
        task_type = cls._detect_task_type(clean_subject)
        
        # Build description
        description_parts = []
        if clean_subject:
            description_parts.append(clean_subject)
        if body:
            # Truncate body if too long
            body_preview = body[:500] + "..." if len(body) > 500 else body
            description_parts.append(body_preview)
        
        description = "\n\n".join(description_parts) if description_parts else "Process attached files"
        
        # Extract code attachments
        code_attachments = email.get_code_attachments()
        
        # Determine if auto-execution is allowed
        # Read-only tasks (review, doc) can auto-execute
        auto_execute = task_type in (TaskType.REVIEW, TaskType.DOC)
        requires_confirmation = not auto_execute
        
        return TaskRequest(
            task_type=task_type,
            description=description,
            attachments=code_attachments,
            auto_execute=auto_execute,
            requires_confirmation=requires_confirmation,
            confirmation_reason="" if auto_execute else "Task involves file modifications",
            metadata={
                "from": email.from_address,
                "subject": email.subject,
                "message_id": email.message_id,
                "total_attachments": len(email.attachments),
                "code_attachments": len(code_attachments),
            },
        )
    
    @classmethod
    def _detect_task_type(cls, text: str) -> TaskType:
        """Detect task type from text.
        
        Args:
            text: Text to analyze (usually subject line).
            
        Returns:
            Detected TaskType.
        """
        text_lower = text.lower()
        
        # Check for slash commands
        if text_lower.startswith("/"):
            command = text_lower.split()[0]
            command_map = {
                "/review": TaskType.REVIEW,
                "/code": TaskType.CODE,
                "/refactor": TaskType.REFACTOR,
                "/fix": TaskType.FIX,
                "/doc": TaskType.DOC,
                "/test": TaskType.TEST,
            }
            return command_map.get(command, TaskType.CUSTOM)
        
        # Check patterns
        for task_type, pattern in cls.TASK_PATTERNS.items():
            if pattern.search(text):
                return task_type
        
        # Default to custom if we have attachments, otherwise unknown
        return TaskType.UNKNOWN
