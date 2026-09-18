#!/usr/bin/env python3
"""
Telegram channel collector.
Reuses the existing telegram-history session and credentials.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from env_loader import load_env

load_env()

SKILL_DIR = Path(__file__).parent.parent
SESSION_DIR = SKILL_DIR / "session"

# Telegram history script path — configurable via env var or config.json
# Fallback: look for telegram-history sibling directory
TG_HISTORY_SCRIPT = os.environ.get("TG_HISTORY_SCRIPT", "").strip()
if not TG_HISTORY_SCRIPT:
    # Try to read from config.json
    _cfg_path = SKILL_DIR / "config" / "config.json"
    if _cfg_path.exists():
        try:
            _cfg = json.loads(_cfg_path.read_text())
            TG_HISTORY_SCRIPT = _cfg.get("telegram_script_path", "").strip()
        except Exception:
            pass
if not TG_HISTORY_SCRIPT:
    TG_HISTORY_SCRIPT = str(SKILL_DIR.parent / "telegram-history" / "scripts" / "tg_history.py")


def collect_telegram(channels: list[dict], limit_per_channel: int = 20) -> list[dict]:
    """
    Fetch recent messages from multiple Telegram channels.
    Returns a list of dicts with keys: title, url, summary, source, tags, date.
    """
    items = []

    script_path = Path(TG_HISTORY_SCRIPT)
    if not script_path.exists():
        print(
            f"[TG] telegram-history script not found at {TG_HISTORY_SCRIPT} — "
            f"skip Telegram collection. Set TG_HISTORY_SCRIPT env var or "
            f"config.telegram_script_path to enable.",
            file=sys.stderr,
        )
        return items

    for ch in channels:
        chat_id = ch.get("chat_id")
        name = ch.get("name", ch.get("username", str(chat_id)))
        tags = ch.get("tags", [])
        username = ch.get("username", "")

        if not chat_id:
            print(f"[TG] Skipping {name}: no chat_id", file=sys.stderr)
            continue

        # Skip placeholder values like {CHANNEL_ID}
        if chat_id.startswith("{") and chat_id.endswith("}"):
            print(
                f"[TG] Skipping {name}: placeholder chat_id '{chat_id}' — "
                f"replace with real chat_id in config",
                file=sys.stderr,
            )
            continue

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    str(TG_HISTORY_SCRIPT),
                    "history",
                    str(chat_id),
                    "--limit",
                    str(limit_per_channel),
                    "--json",
                ],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(SKILL_DIR.parent / "telegram-history"),
            )

            if result.returncode != 0:
                print(f"[TG] Error fetching {name}: {result.stderr[:200]}", file=sys.stderr)
                continue

            raw = result.stdout.strip()
            if not raw or raw.startswith("usage:") or raw.startswith("Error"):
                print(f"[TG] Empty or error response for {name}", file=sys.stderr)
                continue

            messages = json.loads(raw)

            for msg in messages:
                text = msg.get("text", "").strip()
                if not text or len(text) < 50:
                    continue  # Skip short messages

                # Skip bot commands, join messages, empty content
                if text.startswith("/") or text.startswith("!") or "joined" in text.lower():
                    continue

                # Extract title: first non-empty line, stripped of markdown bold
                import re

                raw_lines = text.splitlines()
                first_line = next((line.strip() for line in raw_lines if line.strip()), "")
                display_title = re.sub(r"\*\*(.+?)\*\*", r"\1", first_line)
                # Truncate at word boundary near 80 chars
                if len(display_title) > 80:
                    cut = display_title[:80].rfind(" ")
                    title = display_title[:cut] + "…" if cut > 0 else display_title[:80] + "…"
                else:
                    title = display_title

                msg_id = msg.get("id", "")
                items.append(
                    {
                        "id": f"tg_{msg_id}" if msg_id else f"tg_{hash(text[:50])}",
                        "title": title,
                        "url": f"https://t.me/{username}/{msg_id}" if msg_id else "",
                        "summary": text[:300],
                        "source": name,
                        "source_type": "telegram",
                        "tags": tags,
                        "date": msg.get("date", "")[:10],
                        "raw_text": text,
                    }
                )

        except subprocess.TimeoutExpired:
            print(f"[TG] Timeout for {name}", file=sys.stderr)
        except json.JSONDecodeError as e:
            print(f"[TG] JSON parse error for {name}: {e}", file=sys.stderr)
        except Exception as e:
            print(f"[TG] Unexpected error for {name}: {e}", file=sys.stderr)

    return items


if __name__ == "__main__":
    channels_file = SKILL_DIR / "config" / "telegram-channels.json"
    config_file = SKILL_DIR / "config" / "config.json"

    channels = json.loads(channels_file.read_text())
    config = json.loads(config_file.read_text())

    items = collect_telegram(
        channels, limit_per_channel=config.get("telegram_limit_per_channel", 20)
    )

    out_file = SKILL_DIR / "data" / "items.jsonl"
    with open(out_file, "a", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"[TG] Collected {len(items)} items from {len(channels)} channels")
