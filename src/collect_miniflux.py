#!/usr/bin/env python3
"""
Miniflux collector (module 01 · miniflux).

Pulls entries from a self-hosted Miniflux instance via its REST API instead of
fetching each RSS feed individually. One request covers every subscribed feed,
so a Miniflux account with N feeds costs one round-trip instead of N.

API: https://miniflux.app/docs/api.html  (Basic auth with API key as the password,
or username/password when the key is not available).
"""

import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import collect_rss as _rss

SKILL_DIR = Path(__file__).parent.parent

DEFAULT_BASE_URL = "https://miniflux.cgartlab.com"
DEFAULT_HOURS = 24


def _cfg(key: str, default=None):
    """Read a collector setting from config.json."""
    try:
        cfg = json.loads((SKILL_DIR / "config" / "config.json").read_text(encoding="utf-8"))
        return cfg.get(key, default)
    except Exception:
        return default


def _auth_header() -> str | None:
    """Build the Authorization header.

    Preference order:
      1. MINIFLUX_API_KEY — used as the Basic-auth password with any username
         (that is how Miniflux documents API keys).
      2. MINIFLUX_USERNAME / MINIFLUX_PASSWORD.
    Returns None when nothing is configured, so the caller can report a clear skip.
    """
    api_key = os.environ.get("MINIFLUX_API_KEY", "").strip()
    if api_key:
        user = os.environ.get("MINIFLUX_USERNAME", "").strip() or "miniflux"
        raw = f"{user}:{api_key}"
    else:
        user = os.environ.get("MINIFLUX_USERNAME", "").strip()
        password = os.environ.get("MINIFLUX_PASSWORD", "").strip()
        if not user or not password:
            return None
        raw = f"{user}:{password}"
    return "Basic " + base64.b64encode(raw.encode()).decode()


def _get(path: str, params: dict | None = None, timeout: int = 30):
    base = os.environ.get("MINIFLUX_URL", DEFAULT_BASE_URL).rstrip("/")
    url = f"{base}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": _auth_header() or "",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def _strip_html(text: str) -> str:
    """Strip markup and decode entities (shared behaviour with collect_rss)."""
    return _rss._strip_html(text)


def _strip_noise(summary: str, title: str = "") -> str:
    """Drop leading page chrome (breadcrumbs / bylines) — shared with collect_rss."""
    return _rss._strip_noise(summary, title)


def _entry_date(published_at: str) -> str:
    """Miniflux returns RFC 3339 (2026-10-20T21:08:08+08:00) -> YYYY-MM-DD."""
    if not published_at:
        return ""
    import re

    m = re.search(r"\d{4}-\d{2}-\d{2}", published_at)
    return m.group() if m else ""


def collect_miniflux(
    hours: int | None = None,
    limit: int | None = None,
    categories: list[str] | None = None,
    status: str = "unread",
    per_feed_limit: int | None = None,
) -> list[dict]:
    """Collect the most recent entries across every subscribed feed.

    Args:
        hours: only entries published within this many hours (default from config).
        limit: max entries to return across all feeds (default from config).
        categories: optional category titles to keep (e.g. ["TECH", "AI"]).
        status: "unread" (default), "read", or "all".
        per_feed_limit: max entries taken from any single feed. Without this, a
            high-volume feed (IT之家 publishes 100+/day) drowns out every other
            source — measured 182/300 from one feed before this cap existed.

    Returns:
        List of item dicts in the same shape the other collectors emit.
    """
    if _auth_header() is None:
        print(
            "[Miniflux] Credentials not configured — set MINIFLUX_API_KEY "
            "or MINIFLUX_USERNAME/MINIFLUX_PASSWORD (see .env.example)",
            file=sys.stderr,
        )
        return []

    hours = int(hours if hours is not None else _cfg("miniflux_hours", DEFAULT_HOURS))
    limit = int(limit if limit is not None else _cfg("miniflux_limit", 100))
    per_feed = int(
        per_feed_limit if per_feed_limit is not None else _cfg("miniflux_per_feed_limit", 5)
    )
    cats = categories if categories is not None else (_cfg("miniflux_categories") or [])

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    params = {
        "limit": min(max(limit * 4, 200), 1000),
        "order": "published_at",
        "direction": "desc",
        "published_after": int(cutoff.timestamp()),
    }
    if status and status != "all":
        params["status"] = status

    try:
        data = _get("/v1/entries", params)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:200]
        print(f"[Miniflux] HTTP {e.code}: {body}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"[Miniflux] Error: {type(e).__name__}: {e}", file=sys.stderr)
        return []

    entries = data.get("entries", []) if isinstance(data, dict) else []
    wanted = {c.upper() for c in cats if c}

    items = []
    seen_per_feed: dict[str, int] = {}
    for entry in entries:
        title = (entry.get("title") or "").strip()
        url = (entry.get("url") or "").strip()
        if not title or not url:
            continue

        feed = entry.get("feed") or {}
        feed_title = (feed.get("title") or "").strip()
        cat_title = ((feed.get("category") or {}).get("title") or "").strip()

        if wanted and cat_title.upper() not in wanted:
            continue

        # Per-feed cap keeps a single high-volume source from dominating.
        key = feed_title or "?"
        if per_feed > 0 and seen_per_feed.get(key, 0) >= per_feed:
            continue

        summary = _strip_noise(_strip_html(entry.get("content") or ""), title)[:300]
        if not summary:
            summary = title

        items.append(
            {
                "id": f"mf_{entry.get('id')}",
                "title": title,
                "url": url,
                "summary": summary,
                "source": feed_title or "Miniflux",
                "source_type": "rss",
                "tags": [cat_title] if cat_title else [],
                "date": _entry_date(entry.get("published_at") or ""),
            }
        )
        seen_per_feed[key] = seen_per_feed.get(key, 0) + 1
        if len(items) >= limit:
            break

    print(
        f"[Miniflux] {len(items)} items / {len(seen_per_feed)} feeds from {hours}h window "
        f"(cap {per_feed}/feed)",
        file=sys.stderr,
    )
    return items


if __name__ == "__main__":
    for it in collect_miniflux():
        print(f"{it['date'] or '----------'}  [{it['source'][:18]:18s}] {it['title'][:60]}")
