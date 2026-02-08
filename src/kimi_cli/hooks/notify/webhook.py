"""Webhook notification hook.

This module provides the WebhookHook class for sending HTTP webhook
notifications when tasks are completed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import httpx
from jinja2 import Template
from loguru import logger

from kimi_cli.hooks.base import HookConfig, HookResult, TaskCompletionHook, TaskContext


# Default payload template (JSON)
DEFAULT_PAYLOAD_TEMPLATE = """\
{
  "event": "task_completion",
  "timestamp": "{{ timestamp }}",
  "data": {
    "success": {{ success | lower }},
    "duration": {{ duration }},
    "work_dir": "{{ work_dir }}",
    "session_id": "{{ session_id }}",
    "model": "{{ model }}",
    "summary": "{{ result_summary | replace('\\"', '\\\\"') }}"
  }
}
"""


@dataclass
class WebhookConfig:
    """Configuration for webhook hook.
    
    Attributes:
        url: The webhook endpoint URL.
        method: HTTP method (GET, POST, PUT, etc.).
        headers: Additional HTTP headers.
        payload_template: Jinja2 template for request body.
        timeout: Request timeout in seconds.
    """
    url: str
    method: str = "POST"
    headers: dict[str, str] | None = None
    payload_template: str | None = None
    timeout: float = 30.0
    
    @classmethod
    def from_hook_config(cls, config: HookConfig) -> WebhookConfig:
        """Create WebhookConfig from generic HookConfig.
        
        Args:
            config: The generic hook configuration.
            
        Returns:
            A WebhookConfig instance.
        """
        cfg = config.config
        return cls(
            url=cfg.get("url", ""),
            method=cfg.get("method", "POST"),
            headers=cfg.get("headers"),
            payload_template=cfg.get("payload_template"),
            timeout=cfg.get("timeout", 30.0),
        )


class WebhookHook(TaskCompletionHook):
    """Hook that sends HTTP webhook notifications.
    
    Example configuration for Slack:
        ```toml
        [[hooks.task_completion.channels]]
        type = "webhook"
        name = "slack-notify"
        enabled = true
        url = "https://hooks.slack.com/services/xxx/yyy/zzz"
        headers = { "Content-Type" = "application/json" }
        payload_template = """
        {
          "text": "Kimi task {{ 'completed' if success else 'failed' }} in {{ '%.0f'|format(duration) }}s"
        }
        """
        ```
    """
    
    def __init__(self, config: HookConfig) -> None:
        """Initialize the webhook hook.
        
        Args:
            config: Configuration for this hook.
        """
        super().__init__(config)
        self.webhook_config = WebhookConfig.from_hook_config(config)
        self.template = Template(
            config.config.get("payload_template") or DEFAULT_PAYLOAD_TEMPLATE
        )
    
    async def on_complete(self, context: TaskContext) -> HookResult:
        """Send a webhook notification when a task completes.
        
        Args:
            context: The task completion context.
            
        Returns:
            A HookResult indicating whether the webhook was sent successfully.
        """
        try:
            # Validate configuration
            if not self.webhook_config.url:
                return HookResult(
                    success=False,
                    error="No webhook URL configured",
                )
            
            # Build payload
            from datetime import datetime, timezone
            
            template_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "success": context.success,
                "duration": context.duration,
                "work_dir": str(context.session.work_dir),
                "session_id": context.session.id,
                "model": context.metadata.get("model", "unknown"),
                "result_summary": context.result_summary,
                "error": context.metadata.get("error", ""),
            }
            
            payload_str = self.template.render(**template_data)
            
            # Parse JSON to validate
            try:
                payload = json.loads(payload_str)
            except json.JSONDecodeError as e:
                logger.warning(f"Payload is not valid JSON: {e}")
                payload = payload_str  # Send as raw string
            
            # Prepare headers
            headers = self.webhook_config.headers or {}
            if isinstance(payload, dict) and "Content-Type" not in headers:
                headers["Content-Type"] = "application/json"
            
            # Send request
            logger.debug(
                f"Sending webhook to {self.webhook_config.url} "
                f"({self.webhook_config.method})"
            )
            
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method=self.webhook_config.method,
                    url=self.webhook_config.url,
                    headers=headers,
                    json=payload if isinstance(payload, dict) else None,
                    content=payload_str if isinstance(payload, str) else None,
                    timeout=self.webhook_config.timeout,
                )
                response.raise_for_status()
            
            logger.info(
                f"Webhook notification sent successfully "
                f"(status={response.status_code})"
            )
            return HookResult(
                success=True,
                data={"status_code": response.status_code},
            )
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error sending webhook: {e}")
            return HookResult(success=False, error=f"HTTP error: {e}")
        except Exception as e:
            logger.exception(f"Failed to send webhook: {e}")
            return HookResult(success=False, error=f"Failed to send webhook: {e}")
