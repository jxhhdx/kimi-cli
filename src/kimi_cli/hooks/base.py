"""Base classes and utilities for the hooks system.

This module provides the foundation for the task completion hook system,
including abstract base classes, configuration models, and the hook manager.
"""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from loguru import logger

if TYPE_CHECKING:
    from kimi_cli.session import Session


@dataclass
class TaskContext:
    """Context information about a completed task.
    
    This dataclass holds all relevant information about a task that has
    just been completed, which can be used by hooks to generate notifications.
    
    Attributes:
        session: The session in which the task was executed.
        success: Whether the task completed successfully.
        duration: The duration of the task execution in seconds.
        result_summary: A brief summary of what was done.
        user_input: The user's input that triggered this task.
        metadata: Additional metadata about the task execution.
    """
    session: "Session"
    success: bool
    duration: float
    result_summary: str
    user_input: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class HookResult:
    """Result of a hook execution.
    
    Attributes:
        success: Whether the hook executed successfully.
        error: Error message if the hook failed.
        data: Optional data returned by the hook.
    """
    success: bool
    error: str | None = None
    data: dict[str, Any] | None = None


@dataclass
class HookConfig:
    """Configuration for a hook channel.
    
    This is a generic configuration class that can be extended by
    specific hook implementations.
    
    Attributes:
        type: The type of hook (e.g., "email", "webhook").
        name: A unique name for this hook channel.
        enabled: Whether this hook is enabled.
        on_success: Whether to trigger on successful tasks.
        on_failure: Whether to trigger on failed tasks.
        config: Type-specific configuration dict.
    """
    type: str
    name: str
    enabled: bool = True
    on_success: bool = True
    on_failure: bool = True
    config: dict[str, Any] = field(default_factory=dict)


class TaskCompletionHook(ABC):
    """Abstract base class for task completion hooks.
    
    All custom hooks should inherit from this class and implement
    the `on_complete` method.
    
    Example:
        ```python
        class MyHook(TaskCompletionHook):
            async def on_complete(self, context: TaskContext) -> HookResult:
                # Do something when task completes
                return HookResult(success=True)
        ```
    """
    
    def __init__(self, config: HookConfig) -> None:
        """Initialize the hook with configuration.
        
        Args:
            config: Configuration for this hook instance.
        """
        self.config = config
    
    @property
    def name(self) -> str:
        """Return the name of this hook."""
        return self.config.name
    
    @property
    def enabled(self) -> bool:
        """Return whether this hook is enabled."""
        return self.config.enabled
    
    def should_trigger(self, context: TaskContext) -> bool:
        """Determine whether this hook should trigger for the given context.
        
        By default, triggers based on success/failure configuration.
        Subclasses can override this for more complex logic.
        
        Args:
            context: The task completion context.
            
        Returns:
            True if the hook should trigger, False otherwise.
        """
        if not self.enabled:
            return False
        
        if context.success and not self.config.on_success:
            return False
        
        if not context.success and not self.config.on_failure:
            return False
        
        return True
    
    @abstractmethod
    async def on_complete(self, context: TaskContext) -> HookResult:
        """Called when a task is completed.
        
        This method must be implemented by subclasses to perform
        the actual notification action.
        
        Args:
            context: Information about the completed task.
            
        Returns:
            A HookResult indicating success or failure.
        """
        raise NotImplementedError


class HookManager:
    """Manager for task completion hooks.
    
    This class manages the registration and execution of hooks.
    It supports parallel execution and error isolation.
    
    Example:
        ```python
        manager = HookManager()
        manager.register(EmailHook(config))
        manager.register(WebhookHook(config))
        
        # Later, when a task completes
        results = await manager.trigger_all(context)
        ```
    """
    
    def __init__(self) -> None:
        """Initialize an empty hook manager."""
        self._hooks: list[TaskCompletionHook] = []
        self._timeout: float = 30.0  # Default timeout for hook execution
    
    def register(self, hook: TaskCompletionHook) -> None:
        """Register a hook.
        
        Args:
            hook: The hook instance to register.
        """
        self._hooks.append(hook)
        logger.debug(f"Registered hook: {hook.name}")
    
    def unregister(self, hook_name: str) -> bool:
        """Unregister a hook by name.
        
        Args:
            hook_name: The name of the hook to unregister.
            
        Returns:
            True if a hook was removed, False otherwise.
        """
        for i, hook in enumerate(self._hooks):
            if hook.name == hook_name:
                self._hooks.pop(i)
                logger.debug(f"Unregistered hook: {hook_name}")
                return True
        return False
    
    def get_hooks(self) -> list[TaskCompletionHook]:
        """Get all registered hooks.
        
        Returns:
            A list of all registered hooks.
        """
        return self._hooks.copy()
    
    def clear(self) -> None:
        """Remove all registered hooks."""
        self._hooks.clear()
        logger.debug("Cleared all hooks")
    
    async def trigger_all(
        self,
        context: TaskContext,
        *,
        parallel: bool = True,
        fail_silent: bool = True,
    ) -> list[HookResult]:
        """Trigger all registered hooks.
        
        Args:
            context: The task completion context.
            parallel: Whether to execute hooks in parallel.
            fail_silent: Whether to suppress individual hook errors.
            
        Returns:
            A list of HookResult, one for each triggered hook.
        """
        # Filter hooks that should trigger
        hooks_to_trigger = [
            hook for hook in self._hooks
            if hook.should_trigger(context)
        ]
        
        if not hooks_to_trigger:
            logger.debug("No hooks to trigger")
            return []
        
        logger.info(
            f"Triggering {len(hooks_to_trigger)} hooks for task completion "
            f"(success={context.success})"
        )
        
        if parallel:
            # Execute hooks in parallel with timeout
            tasks = [
                asyncio.create_task(
                    self._execute_hook_with_timeout(hook, context, fail_silent)
                )
                for hook in hooks_to_trigger
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Convert exceptions to HookResult
            processed_results: list[HookResult] = []
            for hook, result in zip(hooks_to_trigger, results):
                if isinstance(result, Exception):
                    processed_results.append(HookResult(
                        success=False,
                        error=f"Hook {hook.name} raised exception: {result}",
                    ))
                else:
                    processed_results.append(result)
            return processed_results
        else:
            # Execute hooks sequentially
            results = []
            for hook in hooks_to_trigger:
                result = await self._execute_hook_with_timeout(
                    hook, context, fail_silent
                )
                results.append(result)
            return results
    
    async def _execute_hook_with_timeout(
        self,
        hook: TaskCompletionHook,
        context: TaskContext,
        fail_silent: bool,
    ) -> HookResult:
        """Execute a single hook with timeout and error handling.
        
        Args:
            hook: The hook to execute.
            context: The task context.
            fail_silent: Whether to suppress errors.
            
        Returns:
            The HookResult from execution.
        """
        start_time = time.time()
        try:
            result = await asyncio.wait_for(
                hook.on_complete(context),
                timeout=self._timeout,
            )
            elapsed = time.time() - start_time
            logger.debug(
                f"Hook {hook.name} completed in {elapsed:.2f}s "
                f"(success={result.success})"
            )
            return result
        except asyncio.TimeoutError:
            logger.error(f"Hook {hook.name} timed out after {self._timeout}s")
            return HookResult(
                success=False,
                error=f"Hook timed out after {self._timeout}s",
            )
        except Exception as e:
            logger.exception(f"Hook {hook.name} failed: {e}")
            if not fail_silent:
                raise
            return HookResult(
                success=False,
                error=f"Hook failed: {e}",
            )


# Global hook manager instance
_hook_manager: HookManager | None = None


def get_hook_manager() -> HookManager:
    """Get the global hook manager instance.
    
    Returns:
        The global HookManager singleton.
    """
    global _hook_manager
    if _hook_manager is None:
        _hook_manager = HookManager()
    return _hook_manager


def reset_hook_manager() -> None:
    """Reset the global hook manager (useful for testing)."""
    global _hook_manager
    _hook_manager = None
