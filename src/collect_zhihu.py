#!/usr/bin/env python3
"""
Zhihu collector — search Zhihu community + global web via zhihu-search CLI.

Requires:
  - zhihu-search installed (uv tool install zhihu-search)
  - Access Secret configured (zhihu-search --save-token <SECRET> or env ZHIHU_ACCESS_SECRET)

Without auth, gracefully skips. Check status with:
  zhihu-search --check-token

Environment variables:
  ZHIHU_SEARCH_CLI_PATH — path to zhihu-search binary (auto-detected if unset)
  ZHIHU_ACCESS_SECRET   — Access Secret (env or via --save-token to credentials file)

Note on legacy compatibility:
  The old zhihu-cli (PyPI 1.2.0, 2020) is EOL — Python 3.10+ cannot build its locked
  lxml==4.3.4 dependency. This collector has been re-implemented against zhihu-search
  (klarkxy, v2.x) which is the maintained replacement on the Zhihu open platform.
  Legacy ZHIHU_CLI_PATH env var is still honored for path lookup.
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
    """Find zhihu-search binary path.

    Resolution order:
      1. ZHIHU_SEARCH_CLI_PATH env var (canonical name)
      2. ZHIHU_CLI_PATH env var (legacy, backward compat)
      3. config.json -> zhihu_search_cli_path / zhihu_cli_path
      4. Auto-detect from known locations
      5. PATH search (zhihu-search first, then legacy zhihu-cli / zhihu)
    """
    # 1. Env var (canonical)
    env_path = os.environ.get("ZHIHU_SEARCH_CLI_PATH", "").strip()
    if env_path and Path(env_path).exists():
        return env_path

    # 2. Legacy env var
    env_path = os.environ.get("ZHIHU_CLI_PATH", "").strip()
    if env_path and Path(env_path).exists():
        return env_path

    # 3. Config file
    config_path = SKILL_DIR / "config" / "config.json"
    if config_path.exists():
        try:
            cfg: dict = json.loads(config_path.read_text(encoding="utf-8"))
            cli_path = cfg.get("zhihu_search_cli_path") or cfg.get("zhihu_cli_path", "")
            if cli_path and Path(cli_path).exists():
                return str(cli_path)
        except Exception:
            pass

    # 4. Auto-detect (uv tool default install location)
    known_locations = [
        Path.home() / ".local" / "bin" / "zhihu-search",
        Path.home() / ".local" / "share" / "uv" / "tools" / "zhihu-search" / "bin" / "zhihu-search",
    ]
    for p in known_locations:
        if p.exists():
            return str(p)

    # 5. PATH search
    for cmd in ["zhihu-search", "zhihu-cli", "zhihu"]:
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
    """Run zhihu-search command and parse JSON output.

    Args must include --format json for structured response.
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
            return None
        output = result.stdout.strip()
        if not output:
            return None
        # Some subcommands print a trailing "===" separator; the JSON payload is
        # the leading block. json.loads will fail if there's trailing text, so
        # find the closing brace of the outermost object.
        try:
            data: dict = json.loads(output)
            return data
        except json.JSONDecodeError:
            # Fallback: strip trailing non-JSON text
            brace_end = output.rfind("}")
            if brace_end == -1:
                return None
            try:
                return json.loads(output[: brace_end + 1])
            except json.JSONDecodeError:
                return None
    except subprocess.TimeoutExpired:
        print(f"[Zhihu] Command timed out: {' '.join(args[:3])}...", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[Zhihu] Error: {e}", file=sys.stderr)
        return None


# ─── Auth Check ─────────────────────────────────────────────────────────────


def check_auth(cli_path: str) -> bool:
    """Check if zhihu-search is authenticated.

    Uses --check-token, which exits 0 when a valid credential source is present.
    """
    try:
        result = subprocess.run(
            [cli_path, "--check-token"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False


# ─── Response Normalization ─────────────────────────────────────────────────


def _items_from_response(data: dict, scope: str) -> list[dict]:
    """Normalize zhihu-search JSON response to a uniform item list.

    zhihu-search search output shape:
      {
        "success": true,
        "kind": "search",
        "data": {
          "HasMore": bool,
          "SearchHashId": str,
          "Items": [
            { "Title", "ContentType", "ContentID", "ContentText", "Url",
              "CommentCount", "VoteUpCount", "AuthorName", "EditTime", ... }
          ]
        }
      }

    zhihu-search trending output shape:
      {
        "success": true,
        "kind": "trending",
        "data": { "Total": int, "Items": [ { "Title", "Url", "ThumbnailUrl", "Summary" } ] }
      }
    """
    if not data or not data.get("success"):
        return []

    payload = data.get("data") or {}
    raw_items = payload.get("Items") or []

    items: list[dict] = []
    for r in raw_items:
        title = r.get("Title") or r.get("title") or ""
        if not title:
            continue
        url = r.get("Url") or r.get("url") or ""
        author = r.get("AuthorName") or r.get("author") or ""
        # Trending uses Summary; search uses ContentText.
        content = r.get("ContentText") or r.get("Summary") or r.get("content") or ""
        # EditTime is a unix timestamp; convert to YYYY-MM-DD when present.
        date = ""
        edit_time = r.get("EditTime")
        if isinstance(edit_time, (int, float)) and edit_time > 0:
            try:
                date = time.strftime("%Y-%m-%d", time.gmtime(edit_time))
            except Exception:
                date = ""

        if scope == "zhihu":
            source_prefix = "知乎"
            source = f"知乎-{author}" if author else source_prefix
            tags = ["知乎"]
        elif scope == "web":
            source_prefix = "知乎-全网"
            source = source_prefix
            tags = ["知乎", "全网"]
        else:  # trending
            source_prefix = "知乎热榜"
            source = source_prefix
            tags = ["知乎", "热榜"]

        items.append(
            {
                "title": title,
                "url": url,
                "summary": content[:500],
                "source": source,
                "source_type": "zhihu",
                "tags": tags,
                "date": date,
                "raw_text": content,
            }
        )
    return items


# ─── Collectors ─────────────────────────────────────────────────────────────


def collect_search_zhihu(cli_path: str, query: str, count: int = 10) -> list[dict]:
    """Search Zhihu community content (scope=zhihu, max 10)."""
    count = max(1, min(count, 10))
    data = run_cli(
        cli_path,
        ["search", query, "--scope", "zhihu", "--count", str(count), "--format", "json"],
    )
    return _items_from_response(data, scope="zhihu")


def collect_search_web(cli_path: str, query: str, count: int = 10) -> list[dict]:
    """Search global web via Zhihu (scope=web, max 20)."""
    count = max(1, min(count, 20))
    data = run_cli(
        cli_path,
        ["search", query, "--scope", "web", "--count", str(count), "--format", "json"],
    )
    return _items_from_response(data, scope="web")


def collect_search_global(cli_path: str, query: str, count: int = 10) -> list[dict]:
    """Backward-compat alias: previously searched via zhihu-cli's `search global`.

    Now delegates to `zhihu-search search --scope web`.
    """
    return collect_search_web(cli_path, query, count=count)


def collect_hot(cli_path: str, limit: int = 20) -> list[dict]:
    """Get Zhihu trending list (max 30)."""
    limit = max(1, min(limit, 30))
    data = run_cli(cli_path, ["trending", "--limit", str(limit), "--format", "json"])
    items = _items_from_response(data, scope="trending")
    # Prefix titles for clarity in downstream evaluation.
    for it in items:
        it["title"] = f"[热榜] {it['title']}"
    return items


# ─── Main Collector ─────────────────────────────────────────────────────────


def collect_zhihu(queries: list[str] | None = None, include_hot: bool = True) -> list[dict]:
    """Main Zhihu collector via zhihu-search CLI.

    Args:
        queries: search queries (defaults to config/search-keywords.json)
        include_hot: include trending hot list

    Returns:
        List of item dicts ready for evaluation pipeline.
    """
    cli_path = find_cli()
    if not cli_path:
        print(
            "[Zhihu] CLI not found — install: uv tool install zhihu-search",
            file=sys.stderr,
        )
        return []

    if not check_auth(cli_path):
        print(
            "[Zhihu] Not authenticated — get Access Secret at https://developer.zhihu.com/profile "
            "then run: zhihu-search --save-token <SECRET> (or set ZHIHU_ACCESS_SECRET env)",
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

    # Search global web (scope=web)
    for query in queries[:3]:  # Limit global search to 3 queries
        items = collect_search_web(cli_path, query, count=5)
        if items:
            print(f"[Zhihu-web] '{query}': {len(items)} results", file=sys.stderr)
            all_items.extend(items)
        time.sleep(1)

    # Hot list
    if include_hot:
        items = collect_hot(cli_path, limit=10)
        if items:
            print(f"[Zhihu] Hot list: {len(items)} items", file=sys.stderr)
            all_items.extend(items)

    return all_items
