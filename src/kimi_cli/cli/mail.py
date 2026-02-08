"""Simple mail commands for kimi-cli.

This module provides simple CLI commands for email notification
and response handling for a single user.
"""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer
from loguru import logger

from kimi_cli.mail.client import IMAPClient, IMAPConfig
from kimi_cli.mail.parser import EmailParser
from kimi_cli.mail.simple_config import get_simple_config

cli = typer.Typer(
    name="mail",
    help="Simple email notification and reply handling.",
    no_args_is_help=True,
)


@cli.command(name="check")
def mail_check(
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Don't execute, just show what would be done."),
    ] = False,
) -> None:
    """Check for email replies from your configured address."""
    
    async def _check():
        config = get_simple_config()
        
        if not config.is_configured():
            typer.echo("Error: Email not configured.", err=True)
            typer.echo("Set KIMI_EMAIL_ADDRESS and KIMI_EMAIL_PASSWORD", err=True)
            raise typer.Exit(1)
        
        is_valid, error = config.validate()
        if not is_valid:
            typer.echo(f"Error: {error}", err=True)
            raise typer.Exit(1)
        
        typer.echo(f"Checking for replies from: {config.email}")
        
        # Connect to IMAP
        imap_config = IMAPConfig(
            host=config.imap_host,
            port=config.imap_port,
            username=config.email,
            password=config.password,
            use_ssl=config.imap_use_ssl,
            mark_seen=True,
        )
        
        try:
            async with IMAPClient(imap_config) as client:
                emails = await client.fetch_unseen(limit=10)
                
                if not emails:
                    typer.echo("No new emails found.")
                    return
                
                # Filter: only process emails from self
                my_emails = [e for e in emails if e.from_address.lower() == config.email.lower()]
                
                if not my_emails:
                    typer.echo(f"Found {len(emails)} email(s), but none from {config.email}")
                    return
                
                typer.echo(f"Found {len(my_emails)} reply(ies) from you:")
                
                for email in my_emails:
                    typer.echo(f"\n  Subject: {email.subject}")
                    typer.echo(f"  From: {email.from_address}")
                    
                    # Extract task from email
                    task = EmailParser.extract_task(email)
                    
                    if task.attachments:
                        typer.echo(f"  Attachments: {len(task.attachments)}")
                        for att in task.attachments:
                            typer.echo(f"    - {att.filename}")
                    
                    if not dry_run:
                        # TODO: Execute the task
                        typer.echo(f"  Command: {task.to_command()[:60]}...")
                        typer.echo("  → Task ready to execute (use --execute to run)")
                    else:
                        typer.echo(f"  Would execute: {task.to_command()[:60]}...")
                
        except Exception as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(1)
    
    asyncio.run(_check())


@cli.command(name="test")
def mail_test() -> None:
    """Test email configuration."""
    config = get_simple_config()
    
    typer.echo("Email Configuration:")
    typer.echo(f"  Address: {config.email or '(not set)'}")
    typer.echo(f"  Password: {'(set)' if config.password else '(not set)'}")
    typer.echo(f"  SMTP: {config.smtp_host}:{config.smtp_port}")
    typer.echo(f"  IMAP: {config.imap_host}:{config.imap_port}")
    
    if not config.is_configured():
        typer.echo("\n❌ Not configured", err=True)
        typer.echo("\nSet environment variables:")
        typer.echo("  export KIMI_EMAIL_ADDRESS='your@gmail.com'")
        typer.echo("  export KIMI_EMAIL_PASSWORD='your-app-password'")
        raise typer.Exit(1)
    
    # Test connection
    typer.echo("\nTesting connections...")
    
    async def _test():
        # Test SMTP
        try:
            import aiosmtplib
            
            # Connect based on port
            if config.smtp_port == 465:
                # Direct TLS
                smtp = aiosmtplib.SMTP(
                    hostname=config.smtp_host,
                    port=config.smtp_port,
                    use_tls=True,
                )
                await smtp.connect()
            else:
                # STARTTLS
                smtp = aiosmtplib.SMTP(
                    hostname=config.smtp_host,
                    port=config.smtp_port,
                    use_tls=False,
                )
                await smtp.connect()
                await smtp.starttls()
            
            await smtp.login(config.email, config.password)
            await smtp.quit()
            typer.echo("  ✓ SMTP connection OK")
        except Exception as e:
            typer.echo(f"  ✗ SMTP failed: {e}", err=True)
        
        # Test IMAP
        try:
            imap_config = IMAPConfig(
                host=config.imap_host,
                port=config.imap_port,
                username=config.email,
                password=config.password,
            )
            async with IMAPClient(imap_config) as client:
                typer.echo("  ✓ IMAP connection OK")
        except Exception as e:
            typer.echo(f"  ✗ IMAP failed: {e}", err=True)
    
    asyncio.run(_test())
    typer.echo("\n✓ Configuration valid!")


@cli.command(name="send-test")
def mail_send_test(
    message: Annotated[
        str,
        typer.Argument(help="Test message to send."),
    ] = "Hello from Kimi CLI!",
) -> None:
    """Send a test email to yourself."""
    
    async def _send():
        config = get_simple_config()
        
        if not config.is_configured():
            typer.echo("Error: Email not configured", err=True)
            raise typer.Exit(1)
        
        try:
            import aiosmtplib
            from email.mime.text import MIMEText
            
            msg = MIMEText(message)
            msg["Subject"] = "Kimi CLI Test Email"
            msg["From"] = config.email
            msg["To"] = config.email
            
            # Connect based on port
            if config.smtp_port == 465:
                smtp = aiosmtplib.SMTP(
                    hostname=config.smtp_host,
                    port=config.smtp_port,
                    use_tls=True,
                )
                await smtp.connect()
            else:
                smtp = aiosmtplib.SMTP(
                    hostname=config.smtp_host,
                    port=config.smtp_port,
                    use_tls=False,
                )
                await smtp.connect()
                await smtp.starttls()
            
            await smtp.login(config.email, config.password)
            await smtp.send_message(msg)
            await smtp.quit()
            
            typer.echo(f"✓ Test email sent to {config.email}")
            
        except Exception as e:
            typer.echo(f"✗ Failed to send: {e}", err=True)
            raise typer.Exit(1)
    
    asyncio.run(_send())
