#!/usr/bin/env python3
"""
Zhihu CLI collector — search Zhihu community + global web via zhihu-cli.

Requires:
  - zhihu-cli installed (scripts/setup.sh or scripts/setup.ps1)
  - Access Secret configured (zhihu-cli auth set)

Without auth, gracefully skips. Check status with:
  zhihu-cli status

Environment variables:
  ZHIHU_CLI_PATH    — path to zhihu-cli binary (auto-detected if unset)
  ZHIHU_ACCESS_SECRET — alternative to CLI auth (headless mode)
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
    """Find zhihu-cli binary path.

    Resolution order:
      1. ZHIHU_CLI_PATH env var
      2. config.json -> zhihu_cli_path
      3. Auto-detect from known locations
    """
    # 1. Env var
    env_path = os.environ.get("ZHIHU_CLI_PATH", "").strip()
    if env_path and Path(env_path).exists():
        return env_path

    # 2. Config file
    config_path = SKILL_DIR / "config" / "config.json"
    if config_path.exists():
        try:
            cfg: dict = json.loads(config_path.read_text(encoding="utf-8"))
            cli_path = cfg.get("zhihu_cli_path", "")
            if cli_path and Path(cli_path).exists():
                return str(cli_path)
        except Exception:
            pass

    # 3. Auto-detect
    known_locations = [
        # Windows
        Path.home() / "AppData" / "Local" / "ZhihuCLI" / "current" / "zhihu-cli.exe",
        # macOS / Linux
        Path.home() / ".local" / "bin" / "zhihu-cli",
        Path.home() / ".zhihu-cli" / "zhihu-cli",
        # XDG
        Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
        / "zhihu-cli"
        / "current"
        / "zhihu-cli",
    ]
    for p in known_locations:
        if p.exists():
            return str(p)

    # 4. PATH search
    for cmd in ["zhihu-cli", "zhihu"]:
        try:
            result = subprocess.run(
                ["which", cmd] if os.name != "nt" else ["where", cmd],
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
    """Run zhihu-cli command and parse JSON output.

    Returns parsed JSON dict, or None on failure.
    """
    cmd = [cli_path] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            # Try parsing stderr as JSON
            for stream in [result.stderr, result.stdout]:
                stream = stream.strip()
                if stream.startswith("{"):
                    try:
                        err_data: dict = json.loads(stream)
                        if not err_data.get("ok", True):
                            return None
                    except json.JSONDecodeError:
                        pass
            return None
        output = result.stdout.strip()
        if not output:
            return None
        data: dict = json.loads(output)
        return data
    except subprocess.TimeoutExpired:
        print(f"[Zhihu] Command timed out: {' '.join(args[:3])}...", file=sys.stderr)
        return None
    except (json.JSONDecodeError, OSError) as e:
        print(f"[Zhihu] Error: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[Zhihu] Unexpected error: {e}", file=sys.stderr)
        return None


# ─── Auth Check ─────────────────────────────────────────────────────────────


def check_auth(cli_path: str) -> bool:
    """Check if zhihu-cli is authenticated."""
    data = run_cli(cli_path, ["status"], timeout=10)
    if data and data.get("ok"):
        auth_config = data.get("auth", {})
        return bool(auth_config.get("configured", False))
    return False


# ─── Collectors ─────────────────────────────────────────────────────────────


def collect_search_zhihu(cli_path: str, query: str, count: int = 10) -> list[dict]:
    """Search Zhihu community content."""
    data = run_cli(cli_path, ["search", "zhihu", "--query", query, "--count", str(count)])
    if not data or not data.get("ok"):
        return []

    items = []
    results = data.get("data", {}).get("results", data.get("results", []))
    for r in results:
        title = r.get("Title") or r.get("title") or r.get("Text", "")
        if not title:
            continue
        url = r.get("Url") or r.get("url") or ""
        author = r.get("AuthorName") or r.get("author") or ""
        content = r.get("ContentText") or r.get("content") or ""
        date = r.get("Date") or r.get("date") or ""

        items.append(
            {
                "title": title,
                "url": url,
                "summary": content[:500],
                "source": f"知乎-{author}" if author else "知乎",
                "source_type": "zhihu",
                "tags": ["知乎"],
                "date": date,
                "raw_text": content,
            }
        )
    return items


def collect_search_global(cli_path: str, query: str, count: int = 10) -> list[dict]:
    """Search global web via Zhihu CLI."""
    data = run_cli(cli_path, ["search", "global", "--query", query, "--count", str(count)])
    if not data or not data.get("ok"):
        return []

    items = []
    results = data.get("data", {}).get("results", data.get("results", []))
    for r in results:
        title = r.get("Title") or r.get("title") or r.get("Text", "")
        if not title:
            continue
        url = r.get("Url") or r.get("url") or ""
        content = r.get("ContentText") or r.get("content") or ""
        date = r.get("Date") or r.get("date") or ""

        items.append(
            {
                "title": title,
                "url": url,
                "summary": content[:500],
                "source": "知乎-全网",
                "source_type": "zhihu",
                "tags": ["全网"],
                "date": date,
                "raw_text": content,
            }
        )
    return items


def collect_hot(cli_path: str, limit: int = 20) -> list[dict]:
    """Get Zhihu trending/hot list."""
    data = run_cli(cli_path, ["hot", "--limit", str(limit)])
    if not data or not data.get("ok"):
        return []

    items = []
    results = data.get("data", {}).get("results", data.get("results", []))
    for r in results:
        title = r.get("Title") or r.get("title") or r.get("Text", "")
        if not title:
            continue
        url = r.get("Url") or r.get("url") or ""
        content = r.get("ContentText") or r.get("content") or ""

        items.append(
            {
                "title": f"[热榜] {title}",
                "url": url,
                "summary": content[:500] or title,
                "source": "知乎热榜",
                "source_type": "zhihu",
                "tags": ["知乎", "热榜"],
                "date": "",
                "raw_text": content or title,
            }
        )
    return items


# ─── Main Collector ─────────────────────────────────────────────────────────


def collect_zhihu(queries: list[str] | None = None, include_hot: bool = True) -> list[dict]:
    """Main Zhihu CLI collector.

    Args:
        queries: search queries (defaults to config/search-keywords.json)
        include_hot: include trending hot list

    Returns:
        List of item dicts ready for evaluation pipeline.
    """
    cli_path = find_cli()
    if not cli_path:
        print(
            "[Zhihu] CLI not found — install: run scripts/setup.sh (or .ps1) in zhihu-cli skill",
            file=sys.stderr,
        )
        return []

    if not check_auth(cli_path):
        print(
            "[Zhihu] Not authenticated — get Access Secret at https://developer.zhihu.com/profile",
            file=sys.stderr,
        )
        return []

    all_items: list[dict] = []

    # Load default queries from config
    if queries is None:
        keywords_path = SKILL_DIR / "config" / "search-keywords.json"
        if keywords_path.exists():
            try:
                cfg = json.loads(keywords_path.read_text(encoding="utf-8"))
                queries = cfg.get("keywords", [])[:6]  # Limit to 6 queries
            except Exception:
                queries = []

    if not queries:
        queries = ["AI news", "科技趋势"]

    print(f"[Zhihu] Authenticated. CLI: {cli_path}", file=sys.stderr)

    # Search Zhihu community
    for query in queries:
        items = collect_search_zhihu(cli_path, query, count=5)
        if items:
            print(f"[Zhihu] '{query}': {len(items)} results", file=sys.stderr)
            all_items.extend(items)
        time.sleep(1)  # Rate limit courtesy

    # Search global web
    for query in queries[:3]:  # Limit global search to 3 queries
        items = collect_search_global(cli_path, query, count=5)
        if items:
            print(f"[Zhihu-global] '{query}': {len(items)} results", file=sys.stderr)
            all_items.extend(items)
        time.sleep(1)

    # Hot list
    if include_hot:
        items = collect_hot(cli_path, limit=10)
        if items:
            print(f"[Zhihu] Hot list: {len(items)} items", file=sys.stderr)
            all_items.extend(items)

    return all_items
