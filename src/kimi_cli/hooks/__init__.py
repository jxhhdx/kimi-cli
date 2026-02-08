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

__all__ = [
    "HookConfig",
    "HookManager",
    "HookResult",
    "TaskCompletionHook",
    "TaskContext",
    "get_hook_manager",
]
