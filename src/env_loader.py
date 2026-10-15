#!/usr/bin/env python3
"""
Lightweight .env loader — no external dependencies.

Usage:
    from env_loader import load_env
    load_env()  # call once at script startup, before reading os.environ

Rules:
  - Reads .env from the project root (parent of src/)
  - KEY=VALUE format, one per line
  - # comments and empty lines are ignored
  - Values may be optionally quoted (single or double)
  - Existing environment variables are NOT overridden
  - Inline comments after values are NOT supported (keep it simple)
"""

import os
from pathlib import Path

_loaded = False


def load_env(env_file: str | Path | None = None) -> None:
    """Load environment variables from a .env file.

    Args:
        env_file: Path to .env file. Defaults to .env in the project root.

    Side effects:
        Sets os.environ entries for keys that are not already set.
    """
    global _loaded
    if _loaded:
        return

    # Load chain: local .env first (skill-specific overrides),
    # then /root/.hermes/.env (central secrets source — MATON/PVE/MINIFLUX/SENSENOVA/…).
    # Only sets keys that are NOT already present, so local .env wins over the global one.
    if env_file is None:
        local_env = Path(__file__).resolve().parent.parent / ".env"
        global_env = Path("/root/.hermes/.env")
        env_files = [p for p in (local_env, global_env) if p.exists()]
    else:
        env_files = [Path(env_file)]

    if not env_files:
        return  # No .env file — that's fine, just use system env

    for env_file in env_files:
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            # Split on first = sign
            if "=" not in line:
                continue

            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()

            if not key:
                continue

            # Strip optional surrounding quotes
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]

            # Priority chain:
            #  - Do not override a real (non-empty) environment value.
            #  - If os.environ currently holds "" (empty local placeholder),
            #    a later file with a real value is allowed to fill it.
            #  - Do NOT overwrite a real value with an empty one.
            existing = os.environ.get(key, "")
            if existing == "":
                os.environ[key] = value

    _loaded = True
