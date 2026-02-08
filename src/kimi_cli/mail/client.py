"""IMAP client for receiving emails.

This module provides an async IMAP client for fetching and monitoring emails.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING

import aioimaplib
from loguru import logger

if TYPE_CHECKING:
    from kimi_cli.mail.models import Email


@dataclass
class IMAPConfig:
    """Configuration for IMAP connection.
    
    Attributes:
        host: IMAP server hostname.
        port: IMAP server port (default: 993).
        username: Authentication username.
        password: Authentication password.
        use_ssl: Whether to use SSL/TLS (default: True).
        mailbox: Mailbox to monitor (default: INBOX).
        mark_seen: Whether to mark fetched emails as seen.
    """
    host: str
    port: int = 993
    username: str = ""
    password: str = ""
    use_ssl: bool = True
    mailbox: str = "INBOX"
    mark_seen: bool = True


class IMAPClient:
    """Async IMAP client for fetching emails.
    
    This client supports both one-time fetching and idle monitoring.
    
    Example:
        ```python
        config = IMAPConfig(
            host="imap.gmail.com",
            username="your@gmail.com",
            password="app_password"
        )
        
        async with IMAPClient(config) as client:
            # Fetch unread emails
            emails = await client.fetch_unseen()
            
            # Or start idle monitoring
            async for email in client.idle_listen():
                process_email(email)
        ```
    """
    
    def __init__(self, config: IMAPConfig) -> None:
        """Initialize the IMAP client.
        
        Args:
            config: IMAP connection configuration.
        """
        self.config = config
        self._client: aioimaplib.IMAP4_SSL | aioimaplib.IMAP4 | None = None
        self._connected = False
    
    async def __aenter__(self) -> IMAPClient:
        """Async context manager entry.
        
        Returns:
            The connected client.
        """
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.disconnect()
    
    async def connect(self) -> None:
        """Connect to the IMAP server.
        
        Raises:
            ConnectionError: If connection fails.
            AuthenticationError: If authentication fails.
        """
        try:
            logger.debug(f"Connecting to IMAP {self.config.host}:{self.config.port}")
            
            # Create client with or without SSL
            if self.config.use_ssl:
                self._client = aioimaplib.IMAP4_SSL(
                    host=self.config.host,
                    port=self.config.port,
                )
            else:
                self._client = aioimaplib.IMAP4(
                    host=self.config.host,
                    port=self.config.port,
                )
            
            await self._client.wait_hello_from_server()
            
            # Login
            await self._client.login(
                self.config.username,
                self.config.password,
            )
            
            # Select mailbox
            await self._client.select(self.config.mailbox)
            
            self._connected = True
            logger.info(f"Connected to IMAP server: {self.config.host}")
            
        except Exception as e:
            logger.error(f"Failed to connect to IMAP server: {e}")
            raise ConnectionError(f"IMAP connection failed: {e}")
    
    async def disconnect(self) -> None:
        """Disconnect from the IMAP server."""
        if self._client and self._connected:
            try:
                await self._client.logout()
                logger.debug("Disconnected from IMAP server")
            except Exception as e:
                logger.debug(f"Error during disconnect: {e}")
            finally:
                self._connected = False
                self._client = None
    
    async def fetch_unseen(self, limit: int = 50) -> list[Email]:
        """Fetch unseen emails from the mailbox.
        
        Args:
            limit: Maximum number of emails to fetch.
            
        Returns:
            List of Email objects.
            
        Raises:
            ConnectionError: If not connected.
        """
        if not self._connected or not self._client:
            raise ConnectionError("Not connected to IMAP server")
        
        from kimi_cli.mail.parser import EmailParser
        
        emails = []
        
        try:
            # Search for unseen messages
            response = await self._client.search("UNSEEN")
            if response.result != "OK":
                logger.warning(f"Search failed: {response}")
                return []
            
            # Parse message IDs
            message_ids = response.lines[0].decode().split()
            
            if not message_ids:
                logger.debug("No unseen messages")
                return []
            
            logger.info(f"Found {len(message_ids)} unseen messages")
            
            # Limit number of messages to fetch
            message_ids = message_ids[:limit]
            
            # Fetch each message
            for msg_id in message_ids:
                try:
                    email = await self._fetch_message(msg_id)
                    if email:
                        emails.append(email)
                except Exception as e:
                    logger.error(f"Failed to fetch message {msg_id}: {e}")
            
            logger.info(f"Fetched {len(emails)} emails")
            return emails
            
        except Exception as e:
            logger.exception(f"Error fetching unseen emails: {e}")
            raise
    
    async def _fetch_message(self, msg_id: str) -> Email | None:
        """Fetch a single message by ID.
        
        Args:
            msg_id: The message ID.
            
        Returns:
            Parsed Email object or None if failed.
        """
        if not self._client:
            return None
        
        from kimi_cli.mail.parser import EmailParser
        
        # Fetch the full message
        response = await self._client.fetch(
            msg_id,
            "(RFC822)"
        )
        
        if response.result != "OK":
            logger.warning(f"Failed to fetch message {msg_id}: {response}")
            return None
        
        # Parse the message
        raw_message = response.lines[1]
        email = EmailParser.parse_bytes(raw_message)
        
        # Mark as seen if configured
        if self.config.mark_seen:
            await self._client.store(msg_id, "+FLAGS", "(\\Seen)")
        
        return email
    
    async def idle_listen(self, timeout: float = 30.0) -> None:
        """Enter IDLE mode and listen for new messages.
        
        This is a generator that yields when new messages arrive.
        Note: This method doesn't actually yield emails due to IDLE protocol
        limitations. Instead, use it as a signal to fetch new messages.
        
        Args:
            timeout: IDLE timeout in seconds.
            
        Yields:
            None when new messages may be available.
        """
        if not self._connected or not self._client:
            raise ConnectionError("Not connected to IMAP server")
        
        try:
            logger.info("Entering IDLE mode")
            
            while True:
                # Start IDLE
                idle = await self._client.idle_start(timeout=timeout)
                
                # Wait for IDLE response
                msg = await self._client.wait_server_push()
                
                # Stop IDLE
                self._client.idle_done()
                await asyncio.wait_for(idle, timeout=timeout)
                
                # Check if we got a new message notification
                if msg and b"EXISTS" in msg:
                    logger.debug("New message notification received")
                    yield None
                    
        except asyncio.TimeoutError:
            logger.debug("IDLE timeout, no new messages")
        except Exception as e:
            logger.error(f"IDLE mode error: {e}")
            raise
    
    async def check_connection(self) -> bool:
        """Check if the connection is still alive.
        
        Returns:
            True if connected and responsive.
        """
        if not self._client or not self._connected:
            return False
        
        try:
            # Send a NOOP to check connection
            response = await self._client.noop()
            return response.result == "OK"
        except Exception:
            return False
