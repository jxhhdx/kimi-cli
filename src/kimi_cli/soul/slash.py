from __future__ import annotations

import os
import tempfile
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import TYPE_CHECKING

from kosong.message import Message
from loguru import logger
from prompt_toolkit import PromptSession

import kimi_cli.prompts as prompts
from kimi_cli.soul import wire_send
from kimi_cli.soul.agent import load_agents_md
from kimi_cli.soul.context import Context
from kimi_cli.soul.message import system
from kimi_cli.utils.slashcmd import SlashCommandRegistry
from kimi_cli.wire.types import StatusUpdate, TextPart

if TYPE_CHECKING:
    from kimi_cli.soul.kimisoul import KimiSoul

type SoulSlashCmdFunc = Callable[[KimiSoul, str], None | Awaitable[None]]
"""
A function that runs as a KimiSoul-level slash command.

Raises:
    Any exception that can be raised by `Soul.run`.
"""

registry = SlashCommandRegistry[SoulSlashCmdFunc]()


@registry.command
async def init(soul: KimiSoul, args: str):
    """Analyze the codebase and generate an `AGENTS.md` file"""
    from kimi_cli.soul.kimisoul import KimiSoul

    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_context = Context(file_backend=Path(temp_dir) / "context.jsonl")
        tmp_soul = KimiSoul(soul.agent, context=tmp_context)
        await tmp_soul.run(prompts.INIT)

    agents_md = await load_agents_md(soul.runtime.builtin_args.KIMI_WORK_DIR)
    system_message = system(
        "The user just ran `/init` slash command. "
        "The system has analyzed the codebase and generated an `AGENTS.md` file. "
        f"Latest AGENTS.md file content:\n{agents_md}"
    )
    await soul.context.append_message(Message(role="user", content=[system_message]))


@registry.command
async def compact(soul: KimiSoul, args: str):
    """Compact the context"""
    if soul.context.n_checkpoints == 0:
        wire_send(TextPart(text="The context is empty."))
        return

    logger.info("Running `/compact`")
    await soul.compact_context()
    wire_send(TextPart(text="The context has been compacted."))
    wire_send(StatusUpdate(context_usage=soul.status.context_usage))


@registry.command(aliases=["reset"])
async def clear(soul: KimiSoul, args: str):
    """Clear the context"""
    logger.info("Running `/clear`")
    await soul.context.clear()
    wire_send(TextPart(text="The context has been cleared."))
    wire_send(StatusUpdate(context_usage=soul.status.context_usage))


@registry.command
async def yolo(soul: KimiSoul, args: str):
    """Toggle YOLO mode (auto-approve all actions)"""
    if soul.runtime.approval.is_yolo():
        soul.runtime.approval.set_yolo(False)
        wire_send(TextPart(text="You only die once! Actions will require approval."))
    else:
        soul.runtime.approval.set_yolo(True)
        wire_send(TextPart(text="You only live once! All actions will be auto-approved."))


@registry.command
async def mail(soul: KimiSoul, args: str):
    """Configure email notifications for task completion"""
    from kimi_cli.mail.simple_config import SimpleMailConfig, get_simple_config
    
    wire_send(TextPart(text="📧 Email Notification Setup\n"))
    wire_send(TextPart(text="This will configure email notifications when tasks complete.\n"))
    
    # Check current config
    current_config = get_simple_config()
    if current_config.is_configured():
        wire_send(TextPart(f"✉️  Current email: {current_config.email}\n"))
        wire_send(TextPart(text="Type 'change' to update, or press Enter to keep current:\n"))
        
        session = PromptSession[str]()
        try:
            choice = await session.prompt_async(" Choice: ")
            if choice.strip().lower() != "change":
                wire_send(TextPart(text="✓ Keeping current email configuration."))
                return
        except (EOFError, KeyboardInterrupt):
            return
    
    # Select email provider
    wire_send(TextPart(text="\nSelect your email provider:"))
    wire_send(TextPart(text="  1. QQ Mail (qq.com)"))
    wire_send(TextPart(text="  2. Gmail (gmail.com)"))
    wire_send(TextPart(text="  3. 163 Mail (163.com)"))
    wire_send(TextPart(text="  4. Other"))
    
    session = PromptSession[str]()
    try:
        choice = await session.prompt_async(" Choice (1-4): ")
        choice = choice.strip()
        
        provider_domains = {
            "1": "qq.com",
            "2": "gmail.com", 
            "3": "163.com",
            "4": "other"
        }
        
        if choice not in provider_domains:
            wire_send(TextPart(text="❌ Invalid choice. Configuration cancelled."))
            return
        
        provider = provider_domains[choice]
        
        # Get email address
        if provider == "other":
            wire_send(TextPart(text="\nEnter your email address:"))
            email = await session.prompt_async(" Email: ")
            email = email.strip()
        else:
            if provider == "qq.com":
                wire_send(TextPart(text="\nEnter your QQ number (without @qq.com):"))
                qq_number = await session.prompt_async(" QQ: ")
                email = f"{qq_number.strip()}@qq.com"
            else:
                wire_send(TextPart(text=f"\nEnter your {provider} email address:"))
                email = await session.prompt_async(" Email: ")
                email = email.strip()
        
        if not email or "@" not in email:
            wire_send(TextPart(text="❌ Invalid email address. Configuration cancelled."))
            return
        
        # Get password/authorization code
        wire_send(TextPart(text="\n" + "=" * 50))
        if provider == "qq.com":
            wire_send(TextPart(text="📱 For QQ Mail, you need an authorization code:"))
            wire_send(TextPart(text="   1. Go to https://mail.qq.com"))
            wire_send(TextPart(text="   2. Settings → Account → IMAP/SMTP Service"))
            wire_send(TextPart(text="   3. Generate authorization code (16 characters)"))
        elif provider == "gmail.com":
            wire_send(TextPart(text="📱 For Gmail, you need an App Password:"))
            wire_send(TextPart(text="   1. Go to https://myaccount.google.com/apppasswords"))
            wire_send(TextPart(text="   2. Generate an App Password"))
        else:
            wire_send(TextPart(text=f"📱 Enter your {provider} email password or authorization code:"))
        wire_send(TextPart(text="=" * 50 + "\n"))
        
        password = await session.prompt_async(
            " Authorization code: ",
            is_password=True
        )
        password = password.strip()
        
        if not password:
            wire_send(TextPart(text="❌ Password cannot be empty. Configuration cancelled."))
            return
        
        # Get notification recipient (optional)
        wire_send(TextPart(text=f"\nSend notifications to [{email}]? (Press Enter to confirm)"))
        wire_send(TextPart(text="Or enter a different email address:"))
        notify_email = await session.prompt_async(" Notify email [default: same]: ")
        notify_email = notify_email.strip() or email
        
        # Test configuration
        wire_send(TextPart(text="\n🧪 Testing email configuration..."))
        
        test_config = SimpleMailConfig(
            email=email,
            password=password,
            notify_email=notify_email
        )
        
        is_valid, error = test_config.validate()
        if not is_valid:
            wire_send(TextPart(f"❌ Configuration invalid: {error}"))
            return
        
        # Save configuration to environment
        wire_send(TextPart(text="\n💾 Saving configuration..."))
        
        # Determine shell config file
        shell = os.path.basename(os.environ.get("SHELL", "/bin/bash"))
        if shell == "zsh":
            rc_file = Path.home() / ".zshrc"
        else:
            rc_file = Path.home() / ".bashrc"
        
        # Remove old config if exists
        if rc_file.exists():
            content = rc_file.read_text()
            lines = content.split("\n")
            new_lines = [
                line for line in lines 
                if not line.startswith("export KIMI_EMAIL")
            ]
            rc_file.write_text("\n".join(new_lines))
        
        # Add new config
        with open(rc_file, "a") as f:
            f.write(f"\n# Kimi2 email notification configuration\n")
            f.write(f'export KIMI_EMAIL_ADDRESS="{email}"\n')
            f.write(f'export KIMI_EMAIL_PASSWORD="{password}"\n')
            f.write(f'export KIMI_NOTIFY_EMAIL="{notify_email}"\n')
        
        wire_send(TextPart(text=f"✅ Email configuration saved to {rc_file}"))
        wire_send(TextPart(text="\n📝 To apply the changes, run:"))
        wire_send(TextPart(text=f"   source {rc_file}"))
        wire_send(TextPart(text="\n📧 You will receive email notifications when tasks complete!"))
        
    except (EOFError, KeyboardInterrupt):
        wire_send(TextPart(text="\n❌ Configuration cancelled."))
        return
