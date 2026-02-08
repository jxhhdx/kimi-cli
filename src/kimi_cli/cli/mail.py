"""Mail commands for kimi-cli.

This module provides CLI commands for email processing:
- mail-server: Run a daemon that monitors email inbox
- mail-check: One-time check for new emails
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import typer
from loguru import logger

from kimi_cli.mail.client import IMAPClient, IMAPConfig
from kimi_cli.mail.models import TaskRequest
from kimi_cli.mail.parser import EmailParser
from kimi_cli.mail.security import SecurityConfig, SecurityValidator, WhitelistEntry

# Create CLI
cli = typer.Typer(
    name="mail",
    help="Email inbound processing commands.",
    no_args_is_help=True,
)


@dataclass
class MailGlobalConfig:
    """Global configuration for mail commands."""
    
    imap_host: str = "imap.gmail.com"
    imap_port: int = 993
    username: str = ""
    password: str = ""
    mailbox: str = "INBOX"
    
    # Security settings
    whitelist: list[str] | None = None
    require_auto_prefix: bool = True
    sandbox_mode: bool = True
    
    # Processing settings
    working_dir: Path | None = None
    mark_seen: bool = True
    
    @classmethod
    def from_env(cls) -> MailGlobalConfig:
        """Load configuration from environment variables."""
        return cls(
            imap_host=os.environ.get("KIMI_IMAP_HOST", "imap.gmail.com"),
            imap_port=int(os.environ.get("KIMI_IMAP_PORT", "993")),
            username=os.environ.get("KIMI_EMAIL_USERNAME", ""),
            password=os.environ.get("KIMI_EMAIL_PASSWORD", ""),
            mailbox=os.environ.get("KIMI_MAILBOX", "INBOX"),
            whitelist=os.environ.get("KIMI_MAIL_WHITELIST", "").split(",") or None,
            require_auto_prefix=os.environ.get("KIMI_REQUIRE_AUTO", "true").lower() == "true",
            sandbox_mode=os.environ.get("KIMI_SANDBOX", "true").lower() == "true",
            working_dir=Path(os.environ.get("KIMI_MAIL_WORKING_DIR", Path.cwd())),
            mark_seen=os.environ.get("KIMI_MARK_SEEN", "true").lower() == "true",
        )


def _get_security_config(config: MailGlobalConfig) -> SecurityConfig:
    """Create security config from global config."""
    whitelist_entries = []
    
    if config.whitelist:
        for email in config.whitelist:
            email = email.strip()
            if email:
                whitelist_entries.append(WhitelistEntry(
                    email=email,
                    dkim_required=False,  # TODO: Add DKIM verification
                ))
    
    return SecurityConfig(
        enabled=True,
        whitelist=whitelist_entries,
        require_auto_prefix=config.require_auto_prefix,
        sandbox_mode=config.sandbox_mode,
    )


def _get_imap_config(config: MailGlobalConfig) -> IMAPConfig:
    """Create IMAP config from global config."""
    return IMAPConfig(
        host=config.imap_host,
        port=config.imap_port,
        username=config.username,
        password=config.password,
        mailbox=config.mailbox,
        mark_seen=config.mark_seen,
    )


async def _process_email(
    email,
    validator: SecurityValidator,
    working_dir: Path,
    dry_run: bool = False,
) -> bool:
    """Process a single email.
    
    Args:
        email: The email to process.
        validator: Security validator.
        working_dir: Working directory for tasks.
        dry_run: If True, don't actually execute tasks.
        
    Returns:
        True if processed successfully.
    """
    from rich.console import Console
    from rich.table import Table
    
    console = Console()
    
    # Security check
    if not validator.validate_email(email):
        console.print(f"[red]✗[/red] Security check failed for email from {email.from_address}")
        return False
    
    # Extract task
    task = EmailParser.extract_task(email)
    
    # Additional task validation
    is_valid, reason = validator.validate_task(task, email)
    if not is_valid:
        console.print(f"[red]✗[/red] Task validation failed: {reason}")
        return False
    
    # Check if confirmation is required
    needs_confirm, confirm_reason = validator.should_require_confirmation(task)
    if needs_confirm and not dry_run:
        console.print(f"[yellow]⚠[/yellow] Task requires confirmation: {confirm_reason}")
        # TODO: Implement confirmation flow (send email back for confirmation)
        console.print(f"   Task: {task.to_command()[:60]}...")
        return False
    
    # Display task info
    table = Table(title=f"Task from {email.from_address}")
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    
    table.add_row("Type", task.task_type.value)
    table.add_row("Subject", email.subject[:50])
    table.add_row("Command", task.to_command()[:50])
    table.add_row("Attachments", str(len(task.attachments)))
    table.add_row("Auto-execute", "Yes" if task.auto_execute else "No")
    
    console.print(table)
    
    if dry_run:
        console.print("[blue]ℹ[/blue] Dry run mode - task not executed")
        return True
    
    # TODO: Execute the task using kimi
    # This would involve calling the CLI programmatically or creating a subprocess
    console.print(f"[green]✓[/green] Task processed (execution not yet implemented)")
    
    return True


@cli.command(name="check")
def mail_check(
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Don't actually execute tasks, just show what would be done.",
        ),
    ] = False,
    auto_execute: Annotated[
        bool,
        typer.Option(
            "--auto-execute",
            help="Automatically execute read-only tasks without confirmation.",
        ),
    ] = True,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose", "-v",
            help="Enable verbose output.",
        ),
    ] = False,
) -> None:
    """Check for new emails and process them."""
    
    async def _check():
        # Load configuration
        config = MailGlobalConfig.from_env()
        
        # Validate configuration
        if not config.username or not config.password:
            typer.echo("Error: Email credentials not configured.", err=True)
            typer.echo("Set KIMI_EMAIL_USERNAME and KIMI_EMAIL_PASSWORD environment variables.", err=True)
            raise typer.Exit(1)
        
        if verbose:
            logger.enable("kimi_cli")
        
        # Create configs
        imap_config = _get_imap_config(config)
        security_config = _get_security_config(config)
        validator = SecurityValidator(security_config)
        
        # Connect and fetch emails
        try:
            async with IMAPClient(imap_config) as client:
                emails = await client.fetch_unseen(limit=50)
                
                if not emails:
                    typer.echo("No new emails found.")
                    return
                
                typer.echo(f"Found {len(emails)} unread email(s)")
                
                processed = 0
                for email in emails:
                    try:
                        success = await _process_email(
                            email,
                            validator,
                            config.working_dir or Path.cwd(),
                            dry_run=dry_run,
                        )
                        if success:
                            processed += 1
                    except Exception as e:
                        logger.error(f"Failed to process email: {e}")
                        if verbose:
                            raise
                
                typer.echo(f"Processed {processed}/{len(emails)} email(s)")
                
        except Exception as e:
            logger.error(f"Failed to check emails: {e}")
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(1)
    
    asyncio.run(_check())


@cli.command(name="server")
def mail_server(
    interval: Annotated[
        int,
        typer.Option(
            "--interval", "-i",
            help="Check interval in seconds (for polling mode).",
        ),
    ] = 60,
    once: Annotated[
        bool,
        typer.Option(
            "--once",
            help="Run once and exit (don't loop).",
        ),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Don't actually execute tasks.",
        ),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose", "-v",
            help="Enable verbose output.",
        ),
    ] = False,
) -> None:
    """Run the email server daemon.
    
    This command continuously monitors the email inbox for new messages
    and processes them automatically.
    """
    
    async def _server():
        # Load configuration
        config = MailGlobalConfig.from_env()
        
        # Validate configuration
        if not config.username or not config.password:
            typer.echo("Error: Email credentials not configured.", err=True)
            typer.echo("Set KIMI_EMAIL_USERNAME and KIMI_EMAIL_PASSWORD environment variables.", err=True)
            raise typer.Exit(1)
        
        if verbose:
            logger.enable("kimi_cli")
        
        # Create configs
        imap_config = _get_imap_config(config)
        security_config = _get_security_config(config)
        validator = SecurityValidator(security_config)
        
        typer.echo(f"Starting mail server...")
        typer.echo(f"  IMAP: {config.imap_host}:{config.imap_port}")
        typer.echo(f"  Mailbox: {config.mailbox}")
        typer.echo(f"  Check interval: {interval}s")
        typer.echo(f"  Press Ctrl+C to stop")
        
        try:
            async with IMAPClient(imap_config) as client:
                while True:
                    try:
                        # Check for new emails
                        emails = await client.fetch_unseen(limit=10)
                        
                        if emails:
                            typer.echo(f"[{asyncio.get_event_loop().time():.0f}] Found {len(emails)} new email(s)")
                            
                            for email in emails:
                                try:
                                    await _process_email(
                                        email,
                                        validator,
                                        config.working_dir or Path.cwd(),
                                        dry_run=dry_run,
                                    )
                                except Exception as e:
                                    logger.error(f"Failed to process email: {e}")
                        
                        if once:
                            break
                        
                        # Wait before next check
                        await asyncio.sleep(interval)
                        
                    except Exception as e:
                        logger.error(f"Error in processing loop: {e}")
                        if once:
                            raise
                        await asyncio.sleep(interval)
                        
        except KeyboardInterrupt:
            typer.echo("\nStopping mail server...")
        except Exception as e:
            logger.error(f"Server error: {e}")
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(1)
    
    asyncio.run(_server())


@cli.command(name="test")
def mail_test(
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose", "-v",
            help="Enable verbose output.",
        ),
    ] = False,
) -> None:
    """Test email configuration."""
    
    async def _test():
        config = MailGlobalConfig.from_env()
        
        if verbose:
            logger.enable("kimi_cli")
        
        # Show configuration
        typer.echo("Configuration:")
        typer.echo(f"  IMAP Host: {config.imap_host}")
        typer.echo(f"  IMAP Port: {config.imap_port}")
        typer.echo(f"  Username: {config.username or '(not set)'}")
        typer.echo(f"  Password: {'(set)' if config.password else '(not set)'}")
        typer.echo(f"  Mailbox: {config.mailbox}")
        
        if not config.username or not config.password:
            typer.echo("\nError: Email credentials not configured.", err=True)
            raise typer.Exit(1)
        
        # Test connection
        typer.echo("\nTesting IMAP connection...")
        
        try:
            imap_config = _get_imap_config(config)
            async with IMAPClient(imap_config) as client:
                typer.echo("✓ Connected successfully")
                
                # Check for unread messages
                emails = await client.fetch_unseen(limit=1)
                if emails:
                    typer.echo(f"✓ Found {len(emails)} unread message(s)")
                else:
                    typer.echo("ℹ No unread messages")
                    
        except Exception as e:
            typer.echo(f"✗ Connection failed: {e}", err=True)
            raise typer.Exit(1)
        
        typer.echo("\nAll tests passed!")
    
    asyncio.run(_test())
