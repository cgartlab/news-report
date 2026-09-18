#!/usr/bin/env python3
"""
SearXNG search collector.
Uses the local SearXNG instance (192.168.31.111:8099) for unlimited search,
with no API key required and no rate limits.
"""

import json
import sys
import os
import re
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path
from datetime import datetime, timedelta

from env_loader import load_env
load_env()

SKILL_DIR = Path(__file__).parent.parent
SEARXNG_BASE = os.environ.get("SEARXNG_URL", "http://localhost:8099")


def _parse_searxng_date(date_str: str) -> str:
    """Parse SearXNG result date field (ISO or vague)."""
    if not date_str:
        return ""
    # ISO format
    m = re.search(r"(\d{4}-\d{2}-\d{2})", date_str)
    if m:
        return m.group(1)
    # "X days ago" style
    lower = date_str.lower()
    today = datetime.now()
    if "hour" in lower:
        h = re.search(r"(\d+)", lower)
        if h:
            return (today - timedelta(hours=int(h.group(1)))).strftime("%Y-%m-%d")
    elif "day" in lower:
        d = re.search(r"(\d+)", lower)
        if d:
            return (today - timedelta(days=int(d.group(1)))).strftime("%Y-%m-%d")
    elif "week" in lower:
        return (today - timedelta(weeks=1)).strftime("%Y-%m-%d")
    elif "month" in lower:
        return (today - timedelta(days=30)).strftime("%Y-%m-%d")
    elif "year" in lower:
        return (today - timedelta(days=365)).strftime("%Y-%m-%d")
    return ""


def collect_search(keywords: list[dict], limit_per_keyword: int = 5) -> list[dict]:
    """
    Run SearXNG search for each keyword.
    Falls back gracefully if SearXNG is unreachable.
    """
    items = []

    for kw_entry in keywords:
        if not kw_entry.get("enabled", True):
            continue

        keyword = kw_entry.get("keyword", "").strip()
        tags = kw_entry.get("tags", [])

        if not keyword:
            continue

        query = urllib.parse.quote(keyword)
        # Use default engines (no specific engine restriction)
        search_url = (
            f"{SEARXNG_BASE}/search"
            f"?q={query}"
            f"&format=json"
            f"&category=general"
            f"&safesearch=0"
        )

        try:
            req = urllib.request.Request(search_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=35) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
            if not raw:
                print(f"[Search] No response for '{keyword}'", file=sys.stderr)
                continue

            data = json.loads(raw)

            results = data.get("results", [])
            if not results:
                # Try alternative format
                results = data.get("web", {}).get("results", [])

            count = 0
            for r in results:
                if count >= limit_per_keyword:
                    break

                # SearXNG returns: {url, title, content, engine, publishedDate, ...}
                title = r.get("title", "").strip()
                result_url = r.get("url", "").strip()
                snippet = r.get("content", "")[:300]
                date_str = r.get("publishedDate") or r.get("pubdate", "") or ""

                if not title or not result_url:
                    continue

                date_parsed = _parse_searxng_date(date_str) if date_str else ""

                items.append({
                    "id": f"search_{abs(hash(result_url)) % 10**12}",
                    "title": title,
                    "url": result_url,
                    "summary": snippet,
                    "source": keyword,
                    "source_type": "search",
                    "tags": tags,
                    "date": date_parsed,
                })
                count += 1

            print(f"[Search] '{keyword}': {count} results")

        except urllib.error.URLError as e:
            print(f"[Search] Network error for '{keyword}': {e.reason}", file=sys.stderr)
        except json.JSONDecodeError as e:
            print(f"[Search] JSON parse error for '{keyword}': {e}", file=sys.stderr)
        except Exception as e:
            print(f"[Search] Error for '{keyword}': {e}", file=sys.stderr)

    return items


if __name__ == "__main__":
    keywords_file = SKILL_DIR / "config" / "search-keywords.json"
    config_file = SKILL_DIR / "config" / "config.json"

    keywords = json.loads(keywords_file.read_text())
    config = json.loads(config_file.read_text())

    items = collect_search(keywords, limit_per_keyword=config.get("search_limit_per_keyword", 5))

    out_file = SKILL_DIR / "data" / "items.jsonl"
    with open(out_file, "a", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"[Search] Total: {len(items)} items")