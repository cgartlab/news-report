#!/usr/bin/env python3
"""
Bilibili CLI collector — search videos, trending/hot content via bilibili-cli.

Requires:
  - bilibili-cli installed (uv tool install bilibili-cli or pipx install bilibili-cli)
  - Browser cookies or QR login for authentication (most commands work without)

Without auth, gracefully skips. Check status with:
  bili status

Environment variables:
  BILIBILI_CLI_PATH   — path to bili binary (auto-detected if unset)
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
    """Find bilibili-cli binary path.

    Resolution order:
      1. BILIBILI_CLI_PATH env var
      2. config.json -> bilibili_cli_path
      3. Auto-detect from known locations
      4. PATH search
    """
    # 1. Env var
    env_path = os.environ.get("BILIBILI_CLI_PATH", "").strip()
    if env_path and Path(env_path).exists():
        return env_path

    # 2. Config file
    config_path = SKILL_DIR / "config" / "config.json"
    if config_path.exists():
        try:
            cfg: dict = json.loads(config_path.read_text(encoding="utf-8"))
            cli_path = cfg.get("bilibili_cli_path", "")
            if cli_path and Path(cli_path).exists():
                return str(cli_path)
        except Exception:
            pass

    # 3. Auto-detect (uv tool install location)
    known_locations = [
        Path.home() / ".local" / "bin" / "bili",
        Path.home() / ".local" / "bin" / "bilibili",
        Path.home() / ".local" / "share" / "uv" / "tools" / "bilibili-cli" / "bin" / "bili",
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
                    / "bilibili-cli"
                    / "Scripts"
                    / "bili.exe",
                    Path(local_appdata)
                    / "Programs"
                    / "uv"
                    / "tools"
                    / "bilibili-cli"
                    / "Scripts"
                    / "bilibili.exe",
                ]
            )

    for p in known_locations:
        if p.exists():
            return str(p)

    # 4. PATH search
    for cmd in ["bili", "bilibili"]:
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
    """Run bilibili-cli command and parse JSON output.

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
        print(f"[Bilibili] Command timed out: {' '.join(args[:3])}...", file=sys.stderr)
        return None
    except (json.JSONDecodeError, OSError) as e:
        print(f"[Bilibili] Error: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[Bilibili] Unexpected error: {e}", file=sys.stderr)
        return None


# ─── Auth Check ─────────────────────────────────────────────────────────────


def check_auth(cli_path: str) -> bool:
    """Check if bilibili-cli is authenticated (optional for most commands)."""
    data = run_cli(cli_path, ["status"], timeout=10)
    if data and data.get("ok"):
        auth_data = data.get("data", {})
        return bool(auth_data.get("authenticated", False))
    return False


# ─── Collectors ─────────────────────────────────────────────────────────────


def collect_search(cli_path: str, query: str, count: int = 10) -> list[dict]:
    """Search Bilibili videos by keyword."""
    data = run_cli(cli_path, ["search", query, "--type", "video", "--max", str(count)])
    if not data or not data.get("ok"):
        return []

    items = []
    results = data.get("data", {})
    videos = results.get("items", results.get("videos", []))
    for v in videos:
        title = v.get("title") or v.get("name") or ""
        if not title:
            continue
        bvid = v.get("bvid") or v.get("id") or ""
        url = f"https://www.bilibili.com/video/{bvid}" if bvid else ""
        author = v.get("owner", {}).get("name", v.get("author", ""))
        stat = v.get("stat", {})
        views = stat.get("view", v.get("view", 0))
        like = stat.get("like", v.get("like", 0))
        desc = v.get("desc") or v.get("description", "")
        pubdate = v.get("pubdate", v.get("publish_date", ""))

        # Format date
        date_str = ""
        if isinstance(pubdate, (int, float)) and pubdate > 0:
            date_str = time.strftime("%Y-%m-%d", time.localtime(pubdate))

        items.append(
            {
                "title": title,
                "url": url,
                "summary": (desc or title)[:500],
                "source": f"B站-{author}" if author else "B站",
                "source_type": "bilibili",
                "tags": ["B站"],
                "date": date_str,
                "raw_text": desc or title,
                "engagement": {"views": views, "likes": like},
            }
        )
    return items


def collect_hot(cli_path: str, limit: int = 20) -> list[dict]:
    """Get Bilibili trending/hot videos."""
    data = run_cli(cli_path, ["hot", "--max", str(limit)])
    if not data or not data.get("ok"):
        return []

    items = []
    results = data.get("data", {})
    videos = results.get("items", results.get("videos", []))
    for v in videos:
        title = v.get("title") or v.get("name") or ""
        if not title:
            continue
        bvid = v.get("bvid") or v.get("id") or ""
        url = f"https://www.bilibili.com/video/{bvid}" if bvid else ""
        author = v.get("owner", {}).get("name", v.get("author", ""))
        stat = v.get("stat", {})
        views = stat.get("view", v.get("view", 0))
        like = stat.get("like", v.get("like", 0))
        desc = v.get("desc") or v.get("description", "")

        items.append(
            {
                "title": f"[热榜] {title}",
                "url": url,
                "summary": (desc or title)[:500],
                "source": f"B站热榜-{author}" if author else "B站热榜",
                "source_type": "bilibili",
                "tags": ["B站", "热榜"],
                "date": "",
                "raw_text": desc or title,
                "engagement": {"views": views, "likes": like},
            }
        )
    return items


def collect_rank(cli_path: str, day: int = 3, limit: int = 20) -> list[dict]:
    """Get Bilibili site-wide ranking."""
    data = run_cli(cli_path, ["rank", "--day", str(day), "--max", str(limit)])
    if not data or not data.get("ok"):
        return []

    items = []
    results = data.get("data", {})
    videos = results.get("items", results.get("videos", []))
    for v in videos:
        title = v.get("title") or v.get("name") or ""
        if not title:
            continue
        bvid = v.get("bvid") or v.get("id") or ""
        url = f"https://www.bilibili.com/video/{bvid}" if bvid else ""
        author = v.get("owner", {}).get("name", v.get("author", ""))
        stat = v.get("stat", {})
        views = stat.get("view", v.get("view", 0))
        like = stat.get("like", v.get("like", 0))
        desc = v.get("desc") or v.get("description", "")

        items.append(
            {
                "title": f"[排行榜] {title}",
                "url": url,
                "summary": (desc or title)[:500],
                "source": f"B站排行-{author}" if author else "B站排行",
                "source_type": "bilibili",
                "tags": ["B站", "排行榜"],
                "date": "",
                "raw_text": desc or title,
                "engagement": {"views": views, "likes": like},
            }
        )
    return items


# ─── Main Collector ─────────────────────────────────────────────────────────


def collect_bilibili(queries: list[str] | None = None, include_hot: bool = True) -> list[dict]:
    """Main Bilibili collector.

    Args:
        queries: search queries (defaults to config/search-keywords.json)
        include_hot: include trending/hot list and ranking

    Returns:
        List of item dicts ready for evaluation pipeline.
    """
    cli_path = find_cli()
    if not cli_path:
        print(
            "[Bilibili] CLI not found — install: uv tool install bilibili-cli",
            file=sys.stderr,
        )
        return []

    # Check auth (optional for most commands)
    authenticated = check_auth(cli_path)
    if not authenticated:
        print(
            "[Bilibili] Not authenticated (some commands may not work) — run: bili login",
            file=sys.stderr,
        )

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
        queries = ["AI", "科技"]

    print(f"[Bilibili] CLI: {cli_path} (authenticated: {authenticated})", file=sys.stderr)

    # Search videos
    for query in queries:
        items = collect_search(cli_path, query, count=5)
        if items:
            print(f"[Bilibili] '{query}': {len(items)} results", file=sys.stderr)
            all_items.extend(items)
        time.sleep(1)  # Rate limit courtesy

    # Hot list
    if include_hot:
        items = collect_hot(cli_path, limit=10)
        if items:
            print(f"[Bilibili] Hot list: {len(items)} items", file=sys.stderr)
            all_items.extend(items)

        # Ranking
        items = collect_rank(cli_path, day=3, limit=10)
        if items:
            print(f"[Bilibili] Ranking (3-day): {len(items)} items", file=sys.stderr)
            all_items.extend(items)

    return all_items
