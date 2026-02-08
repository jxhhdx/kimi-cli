"""Data models for email processing.

This module defines the data structures used for representing
emails, attachments, and task requests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class TaskType(Enum):
    """Types of tasks that can be requested via email."""
    
    REVIEW = "review"
    CODE = "code"
    REFACTOR = "refactor"
    FIX = "fix"
    DOC = "doc"
    TEST = "test"
    CUSTOM = "custom"
    UNKNOWN = "unknown"


@dataclass
class EmailAttachment:
    """Represents an email attachment.
    
    Attributes:
        filename: Name of the attached file.
        content: Binary content of the attachment.
        content_type: MIME type of the attachment.
        size: Size in bytes.
    """
    filename: str
    content: bytes
    content_type: str = "application/octet-stream"
    size: int = 0
    
    def __post_init__(self) -> None:
        """Calculate size from content if not provided."""
        if not self.size and self.content:
            self.size = len(self.content)
    
    def is_code_file(self) -> bool:
        """Check if this attachment is a code file.
        
        Returns:
            True if the file extension indicates a code file.
        """
        code_extensions = {
            ".py", ".js", ".ts", ".jsx", ".tsx",
            ".java", ".kt", ".scala",
            ".c", ".cpp", ".cc", ".h", ".hpp",
            ".cs", ".vb",
            ".go", ".rs", ".swift",
            ".rb", ".php", ".pl",
            ".sh", ".bash", ".zsh",
            ".sql", ".yaml", ".yml", ".json",
            ".md", ".rst", ".txt",
            ".html", ".css", ".scss", ".less",
        }
        suffix = Path(self.filename).suffix.lower()
        return suffix in code_extensions
    
    def is_archive(self) -> bool:
        """Check if this attachment is an archive.
        
        Returns:
            True if the file is a zip/tar archive.
        """
        archive_extensions = {".zip", ".tar", ".gz", ".tgz", ".bz2", ".7z", ".rar"}
        suffix = Path(self.filename).suffix.lower()
        return suffix in archive_extensions


@dataclass
class Email:
    """Represents a parsed email.
    
    Attributes:
        message_id: Unique message identifier.
        subject: Email subject line.
        from_address: Sender email address.
        from_name: Sender display name.
        to_addresses: List of recipient addresses.
        date: Email date.
        body_text: Plain text body.
        body_html: HTML body (if available).
        attachments: List of attachments.
        headers: Raw email headers.
        flags: IMAP flags.
    """
    message_id: str
    subject: str
    from_address: str
    from_name: str = ""
    to_addresses: list[str] = field(default_factory=list)
    date: datetime | None = None
    body_text: str = ""
    body_html: str = ""
    attachments: list[EmailAttachment] = field(default_factory=list)
    headers: dict[str, str] = field(default_factory=dict)
    flags: list[str] = field(default_factory=list)
    
    def has_attachments(self) -> bool:
        """Check if email has attachments.
        
        Returns:
            True if there are attachments.
        """
        return len(self.attachments) > 0
    
    def get_code_attachments(self) -> list[EmailAttachment]:
        """Get only code file attachments.
        
        Returns:
            List of code file attachments.
        """
        return [att for att in self.attachments if att.is_code_file()]
    
    def is_auto_task(self) -> bool:
        """Check if subject indicates an auto-executable task.
        
        Returns:
            True if subject starts with [AUTO].
        """
        return self.subject.strip().upper().startswith("[AUTO]")


@dataclass
class TaskRequest:
    """Represents a task extracted from an email.
    
    Attributes:
        task_type: Type of task.
        description: Task description from email.
        working_dir: Suggested working directory.
        attachments: Files to process.
        auto_execute: Whether auto-execution is allowed.
        requires_confirmation: Whether confirmation is required.
        confirmation_reason: Reason for requiring confirmation.
        metadata: Additional metadata.
    """
    task_type: TaskType
    description: str
    working_dir: Path | None = None
    attachments: list[EmailAttachment] = field(default_factory=list)
    auto_execute: bool = False
    requires_confirmation: bool = True
    confirmation_reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_command(self) -> str:
        """Convert task to a CLI command string.
        
        Returns:
            Command string for kimi.
        """
        # Build command based on task type
        if self.task_type == TaskType.REVIEW:
            files = " ".join(att.filename for att in self.attachments)
            return f"/review {files}"
        elif self.task_type == TaskType.CODE:
            return f"/code {self.description}"
        elif self.task_type == TaskType.REFACTOR:
            files = " ".join(att.filename for att in self.attachments)
            return f"/refactor {files}\n\n{self.description}"
        elif self.task_type == TaskType.FIX:
            return f"/fix {self.description}"
        elif self.task_type == TaskType.DOC:
            files = " ".join(att.filename for att in self.attachments)
            return f"/doc {files}"
        else:
            # Custom task
            return self.description
    
    def is_readonly(self) -> bool:
        """Check if this is a read-only task.
        
        Returns:
            True for review/doc tasks.
        """
        return self.task_type in (TaskType.REVIEW, TaskType.DOC)
