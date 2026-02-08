"""Task completion hooks system for kimi-cli.

This module provides a hook system that allows triggering notifications
when a task is completed.
"""

from __future__ import annotations

from kimi_cli.hooks.base import (
    HookConfig,
    HookManager,
    HookResult,
    TaskCompletionHook,
    TaskContext,
    get_hook_manager,
)
from kimi_cli.hooks.notify.simple_email import SimpleEmailHook

__all__ = [
    "HookConfig",
    "HookManager",
    "HookResult",
    "TaskCompletionHook",
    "TaskContext",
    "get_hook_manager",
    "SimpleEmailHook",
]


def register_default_hooks() -> None:
    """Register default hooks based on configuration.
    
    This function is called at startup to automatically register
    hooks based on environment configuration.
    """
    from kimi_cli.mail.simple_config import get_simple_config
    
    manager = get_hook_manager()
    config = get_simple_config()
    
    # Register simple email hook if configured
    if config.is_configured():
        hook = SimpleEmailHook(config)
        manager.register(hook)
        import logging
        logging.getLogger(__name__).info(
            f"Registered email hook for {config.email}"
        )
