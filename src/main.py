#!/usr/bin/env python3
"""
news-report: Main entry point.

Usage:
  python3 main.py [--collect-only | --evaluate-only | --full]

Workflow:
  1. Collect  → TG / RSS / Search  → data/items.jsonl
  2. Evaluate → Filter + Challenge + Dispute → verdict set on items
  3. Deduplicate → semantic dedup
  4. Report  → formatted markdown → output/latest.md
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SKILL_DIR / "src"))

# Load .env file before importing submodules (they read os.environ at import time)
from env_loader import load_env  # noqa: E402

load_env()

# Import submodules
from collect_bilibili import collect_bilibili  # noqa: E402
from collect_miniflux import collect_miniflux  # noqa: E402
from collect_rss import collect_rss  # noqa: E402
from collect_search import collect_search  # noqa: E402
from collect_telegram import collect_telegram  # noqa: E402
from collect_twitter import collect_twitter  # noqa: E402
from collect_x_browser import collect_x_browser  # noqa: E402
from collect_xhs import collect_xhs  # noqa: E402
from collect_zhihu import collect_zhihu  # noqa: E402
from deduplicator import deduplicate  # noqa: E402
from evaluator import evaluate_items  # noqa: E402
from report import generate_report, load_curated_items, save_report  # noqa: E402


def log(msg: str):
    print(f"[news-report] {msg}", flush=True)


def run_step(name: str, fn, *args, **kwargs):
    log(f"Starting: {name}")
    try:
        result = fn(*args, **kwargs)
        log(f"Done: {name} → {result}")
        return result
    except Exception as e:
        log(f"ERROR in {name}: {e}")
        raise


def step_collect():
    """Collect from all enabled sources, append to items.jsonl.

    Sources can be individually toggled in config/config.json under
    `enabled_sources` (default: all on for backward compat). Disabled
    sources are skipped entirely and their reason (if any) is logged.
    """
    config_file = SKILL_DIR / "config" / "config.json"
    config = json.loads(config_file.read_text())

    enabled = config.get("enabled_sources", {})
    reasons = config.get("disabled_reasons", {})

    def _enabled(name: str, default: bool = True) -> bool:
        return bool(enabled.get(name, default))

    def _skip(name: str):
        reason = reasons.get(name, "")
        if reason:
            log(f"SKIP {name}: {reason}")
        else:
            log(f"SKIP {name}")

    # Clear previous raw data
    items_file = SKILL_DIR / "data" / "items.jsonl"
    items_file.parent.mkdir(exist_ok=True)
    items_file.write_text("")

    tg_file = SKILL_DIR / "config" / "telegram-channels.json"
    rss_file = SKILL_DIR / "config" / "rss-sources.json"
    kw_file = SKILL_DIR / "config" / "search-keywords.json"

    tg_channels = json.loads(tg_file.read_text())
    rss_sources = json.loads(rss_file.read_text())
    keywords = json.loads(kw_file.read_text())

    total = 0

    # Telegram (disabled by default — needs TG_HISTORY_SCRIPT)
    if _enabled("telegram"):
        tg_items = collect_telegram(
            tg_channels, limit_per_channel=config.get("telegram_limit_per_channel", 20)
        )
        log(f"TG collected: {len(tg_items)}")
        total += len(tg_items)
    else:
        _skip("telegram")
        tg_items = []

    # Miniflux (module 01) — one API call covers every subscribed feed.
    if _enabled("miniflux"):
        miniflux_items = collect_miniflux(
            hours=config.get("miniflux_hours", 24),
            limit=config.get("miniflux_limit", 100),
            categories=config.get("miniflux_categories") or None,
            per_feed_limit=config.get("miniflux_per_feed_limit", 5),
        )
        log(f"Miniflux collected: {len(miniflux_items)}")
        total += len(miniflux_items)
    else:
        _skip("miniflux")
        miniflux_items = []

    # RSS direct (default enabled)
    if _enabled("rss"):
        rss_items = collect_rss(
            rss_sources, limit_per_source=config.get("rss_limit_per_source", 10)
        )
        log(f"RSS collected: {len(rss_items)}")
        total += len(rss_items)
    else:
        _skip("rss")
        rss_items = []

    # Search (disabled by default — SearXNG 8099 not running; use MCP instead)
    if _enabled("search"):
        search_items = collect_search(
            keywords, limit_per_keyword=config.get("search_limit_per_keyword", 5)
        )
        log(f"Search collected: {len(search_items)}")
        total += len(search_items)
    else:
        _skip("search")
        search_items = []

    # Zhihu CLI (module 02) — graceful skip when unauthenticated
    if _enabled("zhihu"):
        zhihu_items = collect_zhihu(include_hot=config.get("zhihu_include_hot", True))
        log(f"Zhihu collected: {len(zhihu_items)}")
        total += len(zhihu_items)
    else:
        _skip("zhihu")
        zhihu_items = []

    # Twitter/X CLI (module 03) — disabled by default (not authenticated)
    if _enabled("twitter"):
        twitter_items = collect_twitter(include_feed=config.get("twitter_include_feed", True))
        log(f"Twitter collected: {len(twitter_items)}")
        total += len(twitter_items)
    else:
        _skip("twitter")
        twitter_items = []

    # Bilibili CLI (module 04) — disabled by default (collector has a bug)
    if _enabled("bilibili"):
        bilibili_items = collect_bilibili(include_hot=config.get("bilibili_include_hot", True))
        log(f"Bilibili collected: {len(bilibili_items)}")
        total += len(bilibili_items)
    else:
        _skip("bilibili")
        bilibili_items = []

    # Xiaohongshu CLI (module 05) — disabled by default (not authenticated)
    if _enabled("xhs"):
        xhs_items = collect_xhs(
            include_hot=config.get("xhs_include_hot", True),
            hot_categories=config.get("xhs_hot_categories", ["food", "fashion"]),
        )
        log(f"XHS collected: {len(xhs_items)}")
        total += len(xhs_items)
    else:
        _skip("xhs")
        xhs_items = []

    # X-Browser CDP (module 06) — disabled by default (needs Edge CDP running)
    if _enabled("x_browser"):
        xb_items = collect_x_browser(
            timeline=config.get("x_browser_timeline", "following"),
            scroll_rounds=config.get("x_browser_scroll_rounds", 12),
        )
        log(f"X-Browser collected: {len(xb_items)}")
        total += len(xb_items)
    else:
        _skip("x_browser")
        xb_items = []

    all_items = (
        tg_items
        + miniflux_items
        + rss_items
        + search_items
        + zhihu_items
        + twitter_items
        + bilibili_items
        + xhs_items
        + xb_items
    )
    with open(items_file, "a", encoding="utf-8") as f:
        for item in all_items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    # Persist the collection scale so step_report can show it later. The report
    # stage only sees the curated set; without this it cannot tell 239 collected
    # from 20 selected, and the header would hide the true source coverage.
    stats = {
        "collected": len(all_items),
        "sources": len({i.get("source") for i in all_items if i.get("source")}),
        "by_source": {
            s: sum(1 for i in all_items if i.get("source") == s)
            for s in {i.get("source") for i in all_items if i.get("source")}
        },
    }
    (SKILL_DIR / "data" / "collect_stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    log(f"Collect step complete: {total} total items written ({stats['sources']} sources)")
    return total


def step_evaluate(skip_llm: bool = False):
    """Run the multi-agent evaluation pipeline."""
    items = evaluate_items(skip_llm=skip_llm, target_selection=20)
    return len(items)


def step_deduplicate():
    """Deduplicate curated items."""
    items = load_curated_items()
    if not items:
        return 0
    unique = deduplicate(items)
    # Rewrite items.jsonl with deduplicated items only
    items_file = SKILL_DIR / "data" / "items.jsonl"
    with open(items_file, "w", encoding="utf-8") as f:
        for item in unique:
            f.write(
                json.dumps(item.__dict__ if hasattr(item, "__dict__") else item, ensure_ascii=False)
                + "\n"
            )
    return len(unique)


def step_report():
    """Generate and save the final report."""
    items = load_curated_items()
    if not items:
        log("No items to report")
        return ""

    collected = 0
    sources = 0
    stats_file = SKILL_DIR / "data" / "collect_stats.json"
    try:
        stats = json.loads(stats_file.read_text(encoding="utf-8"))
        collected = int(stats.get("collected") or 0)
        sources = int(stats.get("sources") or 0)
    except (OSError, ValueError, json.JSONDecodeError):
        pass

    report = generate_report(items, collected=collected, sources=sources)
    save_report(report)
    return report


def run_full():
    """Run the complete pipeline."""
    log(f"=== news-report run at {datetime.now().isoformat()} ===")

    count = run_step("collect", step_collect)
    if count == 0:
        log("Nothing collected, aborting pipeline")
        return

    curated_count = run_step("evaluate", step_evaluate)
    if curated_count == 0:
        log("Nothing survived evaluation")
        return

    run_step("deduplicate", step_deduplicate)

    report = run_step("report", step_report)
    return report


def main():
    parser = argparse.ArgumentParser(description="news-report skill")
    parser.add_argument("--collect-only", action="store_true", help="Run collection only")
    parser.add_argument("--evaluate-only", action="store_true", help="Run evaluation only")
    parser.add_argument("--full", action="store_true", help="Run full pipeline")
    parser.add_argument(
        "--skip-llm",
        action="store_true",
        help="Skip LLM filtering in evaluation (rule-only, fastest)",
    )
    args = parser.parse_args()

    if args.collect_only:
        step_collect()
    elif args.evaluate_only:
        step_evaluate(skip_llm=args.skip_llm)
    else:
        report = run_full()
        if report:
            print("\n" + "=" * 50)
            print(report)


if __name__ == "__main__":
    main()
