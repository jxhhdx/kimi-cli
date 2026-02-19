from __future__ import annotations

import os
from pathlib import Path


def get_share_dir() -> Path:
    """Get the share directory path for kimi2 (custom version)."""
    if share_dir := os.getenv("KIMI2_SHARE_DIR"):
        share_dir = Path(share_dir)
    else:
        share_dir = Path.home() / ".kimi2"
    share_dir.mkdir(parents=True, exist_ok=True)
    return share_dir
