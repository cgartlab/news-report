#!/usr/bin/env python3
"""
Twitter/X CLI collector — search tweets, timelines, and trending content via twitter-cli.

Requires:
  - twitter-cli installed (uv tool install twitter-cli or pipx install twitter-cli)
  - Browser cookies or env vars for authentication

Without auth, gracefully skips. Check status with:
  twitter status

Environment variables:
  TWITTER_CLI_PATH    — path to twitter binary (auto-detected if unset)
  TWITTER_AUTH_TOKEN  — auth token (alternative to browser cookies)
  TWITTER_CT0         — ct0 token (alternative to browser cookies)
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Add src to path for shared imports
sys.path.insert(0, str(Path(__file__).parent))

SKILL_DIR = Path(__file__).parent.parent


# ─── CLI Path Resolution ────────────────────────────────────────────────────


def find_cli() -> str | None:
    """Find twitter-cli binary path.

    Resolution order:
      1. TWITTER_CLI_PATH env var
      2. config.json -> twitter_cli_path
      3. Auto-detect from known locations
      4. PATH search
    """
    # 1. Env var
    env_path = os.environ.get("TWITTER_CLI_PATH", "").strip()
    if env_path and Path(env_path).exists():
        return env_path

    # 2. Config file
    config_path = SKILL_DIR / "config" / "config.json"
    if config_path.exists():
        try:
            cfg: dict = json.loads(config_path.read_text(encoding="utf-8"))
            cli_path = cfg.get("twitter_cli_path", "")
            if cli_path and Path(cli_path).exists():
                return str(cli_path)
        except Exception:
            pass

    # 3. Auto-detect (uv tool install location)
    known_locations = [
        Path.home() / ".local" / "bin" / "twitter",
        Path.home() / ".local" / "bin" / "twitter-cli",
        Path.home() / ".local" / "share" / "uv" / "tools" / "twitter-cli" / "bin" / "twitter",
    ]
    if os.name == "nt":
        # Windows AppData locations
        local_appdata = os.environ.get("LOCALAPPDATA", "")
        if local_appdata:
            known_locations.extend(
                [
                    Path(local_appdata)
                    / "Programs"
                    / "uv"
                    / "tools"
                    / "twitter-cli"
                    / "Scripts"
                    / "twitter.exe",
                    Path(local_appdata) / "Microsoft" / "WindowsApps" / "twitter.exe",
                ]
            )

    for p in known_locations:
        if p.exists():
            return str(p)

    # 4. PATH search
    for cmd in ["twitter", "twitter-cli"]:
        try:
            result = subprocess.run(
                ["where", cmd] if os.name == "nt" else ["which", cmd],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip().splitlines()[0]
        except Exception:
            pass

    return None


# ─── CLI Execution ──────────────────────────────────────────────────────────


def run_cli(cli_path: str, args: list[str], timeout: int = 30) -> dict | None:
    """Run twitter-cli command and parse JSON output.

    Returns parsed JSON dict, or None on failure.
    """
    cmd = [cli_path] + args + ["--json"]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            return None
        output = result.stdout.strip()
        if not output:
            return None
        data: dict = json.loads(output)
        return data
    except subprocess.TimeoutExpired:
        print(f"[Twitter] Command timed out: {' '.join(args[:3])}...", file=sys.stderr)
        return None
    except (json.JSONDecodeError, OSError) as e:
        print(f"[Twitter] Error: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[Twitter] Unexpected error: {e}", file=sys.stderr)
        return None


# ─── Auth Check ─────────────────────────────────────────────────────────────


def check_auth(cli_path: str) -> bool:
    """Check if twitter-cli is authenticated."""
    data = run_cli(cli_path, ["status"], timeout=10)
    if data and data.get("ok"):
        auth_data = data.get("data", {})
        return bool(auth_data.get("authenticated", False))
    return False


# ─── Collectors ─────────────────────────────────────────────────────────────


def collect_search(cli_path: str, query: str, count: int = 10) -> list[dict]:
    """Search tweets by keyword."""
    data = run_cli(cli_path, ["search", query, "--max", str(count)])
    if not data or not data.get("ok"):
        return []

    items = []
    tweets = data.get("data", [])
    for t in tweets:
        text = t.get("text", "")
        if not text:
            continue
        author = t.get("author", {}).get("screenName", t.get("author", {}).get("name", ""))
        tweet_id = t.get("id", "")
        url = f"https://x.com/i/status/{tweet_id}" if tweet_id else ""
        created_at = t.get("createdAt", t.get("date", ""))
        metrics = t.get("metrics", {})
        likes = metrics.get("likes", 0)
        rts = metrics.get("retweets", 0)

        # Extract hashtags and mentions
        tags = ["Twitter"]
        hashtags = t.get("hashtag", [])
        if isinstance(hashtags, list):
            tags.extend([h for h in hashtags[:3]])
        mentions = t.get("mentions", [])
        if isinstance(mentions, list):
            tags.extend([f"@{m}" for m in mentions[:2]])

        items.append(
            {
                "title": text[:100] + ("..." if len(text) > 100 else ""),
                "url": url,
                "summary": text[:500],
                "source": f"Twitter-{author}" if author else "Twitter",
                "source_type": "twitter",
                "tags": tags,
                "date": created_at,
                "raw_text": text,
                "engagement": {"likes": likes, "retweets": rts},
            }
        )
    return items


def collect_feed(cli_path: str, count: int = 20, timeline: str = "following") -> list[dict]:
    """Fetch timeline tweets (For You or Following)."""
    args = ["feed", "--max", str(count)]
    if timeline == "following":
        args += ["-t", "following"]
    data = run_cli(cli_path, args)
    if not data or not data.get("ok"):
        return []

    items = []
    tweets = data.get("data", [])
    for t in tweets:
        text = t.get("text", "")
        if not text:
            continue
        author = t.get("author", {}).get("screenName", t.get("author", {}).get("name", ""))
        tweet_id = t.get("id", "")
        url = f"https://x.com/i/status/{tweet_id}" if tweet_id else ""
        created_at = t.get("createdAt", t.get("date", ""))
        metrics = t.get("metrics", {})
        likes = metrics.get("likes", 0)
        rts = metrics.get("retweets", 0)

        tags = ["Twitter", "Feed"]

        items.append(
            {
                "title": text[:100] + ("..." if len(text) > 100 else ""),
                "url": url,
                "summary": text[:500],
                "source": f"Twitter-{author}" if author else "Twitter-Feed",
                "source_type": "twitter",
                "tags": tags,
                "date": created_at,
                "raw_text": text,
                "engagement": {"likes": likes, "retweets": rts},
            }
        )
    return items


# ─── Main Collector ─────────────────────────────────────────────────────────


def collect_twitter(queries: list[str] | None = None, include_feed: bool = True) -> list[dict]:
    """Main Twitter/X collector.

    Args:
        queries: search queries (defaults to config/search-keywords.json)
        include_feed: include timeline feed

    Returns:
        List of item dicts ready for evaluation pipeline.
    """
    cli_path = find_cli()
    if not cli_path:
        print(
            "[Twitter] CLI not found — install: uv tool install twitter-cli",
            file=sys.stderr,
        )
        return []

    if not check_auth(cli_path):
        print(
            "[Twitter] Not authenticated — login to x.com in browser or set TWITTER_AUTH_TOKEN",
            file=sys.stderr,
        )
        return []

    all_items: list[dict] = []

    # Load default queries from config
    if queries is None:
        keywords_path = SKILL_DIR / "config" / "search-keywords.json"
        if keywords_path.exists():
            try:
                cfg: dict = json.loads(keywords_path.read_text(encoding="utf-8"))
                queries = cfg.get("keywords", [])[:5]  # Limit to 5 queries
            except Exception:
                queries = []

    if not queries:
        queries = ["AI news", "科技趋势"]

    print(f"[Twitter] Authenticated. CLI: {cli_path}", file=sys.stderr)

    # Search tweets
    for query in queries:
        items = collect_search(cli_path, query, count=5)
        if items:
            print(f"[Twitter] '{query}': {len(items)} results", file=sys.stderr)
            all_items.extend(items)
        time.sleep(2)  # Rate limit courtesy

    # Feed
    if include_feed:
        items = collect_feed(cli_path, count=10, timeline="following")
        if items:
            print(f"[Twitter] Feed: {len(items)} items", file=sys.stderr)
            all_items.extend(items)

    return all_items
