#!/usr/bin/env python3
"""
Xiaohongshu (小红书) CLI collector — search notes, hot content, feed via xiaohongshu-cli.

Requires:
  - xiaohongshu-cli installed (uv tool install xiaohongshu-cli or pipx install xiaohongshu-cli)
  - Browser cookies or QR login for authentication

Without auth, gracefully skips. Check status with:
  xhs status

Environment variables:
  XHS_CLI_PATH        — path to xhs binary (auto-detected if unset)
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
    """Find xiaohongshu-cli binary path.

    Resolution order:
      1. XHS_CLI_PATH env var
      2. config.json -> xhs_cli_path
      3. Auto-detect from known locations
      4. PATH search
    """
    # 1. Env var
    env_path = os.environ.get("XHS_CLI_PATH", "").strip()
    if env_path and Path(env_path).exists():
        return env_path

    # 2. Config file
    config_path = SKILL_DIR / "config" / "config.json"
    if config_path.exists():
        try:
            cfg: dict = json.loads(config_path.read_text(encoding="utf-8"))
            cli_path = cfg.get("xhs_cli_path", "")
            if cli_path and Path(cli_path).exists():
                return str(cli_path)
        except Exception:
            pass

    # 3. Auto-detect (uv tool install location)
    known_locations = [
        Path.home() / ".local" / "bin" / "xhs",
        Path.home() / ".local" / "bin" / "xiaohongshu",
        Path.home() / ".local" / "share" / "uv" / "tools" / "xiaohongshu-cli" / "bin" / "xhs",
    ]
    if os.name == "nt":
        local_appdata = os.environ.get("LOCALAPPDATA", "")
        if local_appdata:
            known_locations.extend(
                [
                    Path(local_appdata)
                    / "Programs"
                    / "uv"
                    / "tools"
                    / "xiaohongshu-cli"
                    / "Scripts"
                    / "xhs.exe",
                    Path(local_appdata)
                    / "Programs"
                    / "uv"
                    / "tools"
                    / "xiaohongshu-cli"
                    / "Scripts"
                    / "xiaohongshu.exe",
                ]
            )

    for p in known_locations:
        if p.exists():
            return str(p)

    # 4. PATH search
    for cmd in ["xhs", "xiaohongshu"]:
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
    """Run xiaohongshu-cli command and parse JSON output.

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
        print(f"[XHS] Command timed out: {' '.join(args[:3])}...", file=sys.stderr)
        return None
    except (json.JSONDecodeError, OSError) as e:
        print(f"[XHS] Error: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[XHS] Unexpected error: {e}", file=sys.stderr)
        return None


# ─── Auth Check ─────────────────────────────────────────────────────────────


def check_auth(cli_path: str) -> bool:
    """Check if xiaohongshu-cli is authenticated."""
    data = run_cli(cli_path, ["status"], timeout=10)
    if data and data.get("ok"):
        auth_data = data.get("data", {})
        return bool(auth_data.get("authenticated", False))
    return False


# ─── Collectors ─────────────────────────────────────────────────────────────


def collect_search(cli_path: str, query: str, count: int = 10) -> list[dict]:
    """Search Xiaohongshu notes by keyword."""
    data = run_cli(cli_path, ["search", query, "--max", str(count)])
    if not data or not data.get("ok"):
        return []

    items = []
    results = data.get("data", {})
    notes = results.get("items", results.get("notes", []))
    for n in notes:
        title = n.get("title") or n.get("display_title") or ""
        if not title:
            continue
        note_id = n.get("note_id") or n.get("id") or ""
        url = f"https://www.xiaohongshu.com/explore/{note_id}" if note_id else ""
        author = n.get("user", {}).get("nickname", n.get("author", ""))
        desc = n.get("desc") or n.get("description", "")
        liked_count = n.get("liked_count", 0)
        note_type = n.get("type", n.get("note_type", ""))

        # Format date (timestamp)
        date_str = ""
        time_val = n.get("time", n.get("create_time", 0))
        if isinstance(time_val, (int, float)) and time_val > 0:
            # Handle both seconds and milliseconds
            if time_val > 1e12:
                time_val = time_val / 1000
            date_str = time.strftime("%Y-%m-%d", time.localtime(time_val))

        items.append(
            {
                "title": title,
                "url": url,
                "summary": (desc or title)[:500],
                "source": f"小红书-{author}" if author else "小红书",
                "source_type": "xiaohongshu",
                "tags": ["小红书"],
                "date": date_str,
                "raw_text": desc or title,
                "engagement": {"likes": liked_count, "type": note_type},
            }
        )
    return items


def collect_hot(cli_path: str, category: str = "food", count: int = 20) -> list[dict]:
    """Get Xiaohongshu hot/trending notes by category."""
    data = run_cli(cli_path, ["hot", "-c", category, "--max", str(count)])
    if not data or not data.get("ok"):
        return []

    items = []
    results = data.get("data", {})
    notes = results.get("items", results.get("notes", []))
    for n in notes:
        title = n.get("title") or n.get("display_title") or ""
        if not title:
            continue
        note_id = n.get("note_id") or n.get("id") or ""
        url = f"https://www.xiaohongshu.com/explore/{note_id}" if note_id else ""
        author = n.get("user", {}).get("nickname", n.get("author", ""))
        desc = n.get("desc") or n.get("description", "")
        liked_count = n.get("liked_count", 0)

        items.append(
            {
                "title": f"[热榜] {title}",
                "url": url,
                "summary": (desc or title)[:500],
                "source": f"小红书热榜-{author}" if author else f"小红书热榜-{category}",
                "source_type": "xiaohongshu",
                "tags": ["小红书", "热榜", category],
                "date": "",
                "raw_text": desc or title,
                "engagement": {"likes": liked_count},
            }
        )
    return items


def collect_feed(cli_path: str, count: int = 20) -> list[dict]:
    """Get Xiaohongshu recommendation feed."""
    data = run_cli(cli_path, ["feed", "--max", str(count)])
    if not data or not data.get("ok"):
        return []

    items = []
    results = data.get("data", {})
    notes = results.get("items", results.get("notes", []))
    for n in notes:
        title = n.get("title") or n.get("display_title") or ""
        if not title:
            continue
        note_id = n.get("note_id") or n.get("id") or ""
        url = f"https://www.xiaohongshu.com/explore/{note_id}" if note_id else ""
        author = n.get("user", {}).get("nickname", n.get("author", ""))
        desc = n.get("desc") or n.get("description", "")
        liked_count = n.get("liked_count", 0)

        items.append(
            {
                "title": title,
                "url": url,
                "summary": (desc or title)[:500],
                "source": f"小红书-{author}" if author else "小红书-Feed",
                "source_type": "xiaohongshu",
                "tags": ["小红书", "Feed"],
                "date": "",
                "raw_text": desc or title,
                "engagement": {"likes": liked_count},
            }
        )
    return items


# ─── Main Collector ─────────────────────────────────────────────────────────


def collect_xhs(
    queries: list[str] | None = None,
    include_hot: bool = True,
    hot_categories: list[str] | None = None,
) -> list[dict]:
    """Main Xiaohongshu collector.

    Args:
        queries: search queries (defaults to config/search-keywords.json)
        include_hot: include trending/hot list
        hot_categories: categories to fetch hot notes for (defaults to ["food", "fashion"])

    Returns:
        List of item dicts ready for evaluation pipeline.
    """
    cli_path = find_cli()
    if not cli_path:
        print(
            "[XHS] CLI not found — install: uv tool install xiaohongshu-cli",
            file=sys.stderr,
        )
        return []

    if not check_auth(cli_path):
        print(
            "[XHS] Not authenticated — run: xhs login (or xhs login --qrcode)",
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
        queries = ["AI", "科技", "生活"]

    # Default hot categories
    if hot_categories is None:
        hot_categories = ["food", "fashion"]

    print(f"[XHS] Authenticated. CLI: {cli_path}", file=sys.stderr)

    # Search notes
    for query in queries:
        items = collect_search(cli_path, query, count=5)
        if items:
            print(f"[XHS] '{query}': {len(items)} results", file=sys.stderr)
            all_items.extend(items)
        time.sleep(1.5)  # Rate limit courtesy (Gaussian jitter in CLI)

    # Hot lists
    if include_hot:
        for cat in hot_categories:
            items = collect_hot(cli_path, category=cat, count=10)
            if items:
                print(f"[XHS] Hot ({cat}): {len(items)} items", file=sys.stderr)
                all_items.extend(items)
            time.sleep(1)

    return all_items
