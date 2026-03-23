"""User config loaded from ~/.git-recap (TOML format)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

DEFAULT_CONFIG_PATH = Path.home() / ".git-recap"

_DEFAULTS: dict[str, Any] = {
    "model": "qwen2.5:3b",
    "since": "1 week ago",
    "author": None,
    "format": "text",
    "ollama_url": "http://localhost:11434/api/chat",
}


def load() -> dict[str, Any]:
    """Load config from ~/.git-recap, falling back to defaults for missing keys.

    The config file uses a simple KEY=VALUE format (one per line).
    Lines starting with # are comments. Example::

        model=llama3.2:3b
        since=3 days ago
        author=kamil

    Returns:
        Dict with resolved config values.
    """
    config = dict(_DEFAULTS)
    path = DEFAULT_CONFIG_PATH

    if not path.exists():
        return config

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip().lower()
        value = value.strip()
        if key in config:
            config[key] = value if value.lower() != "none" else None

    return config
