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
import subprocess
from pathlib import Path
from datetime import datetime

SKILL_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SKILL_DIR / "src"))

# Import submodules
from collect_telegram import collect_telegram
from collect_rss import collect_rss
from collect_search import collect_search
from evaluator import evaluate_items, Item
from deduplicator import deduplicate
from report import generate_report, save_report, load_curated_items


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
    """Collect from all sources, append to items.jsonl."""
    config_file = SKILL_DIR / "config" / "config.json"
    config = json.loads(config_file.read_text())

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

    tg_items = collect_telegram(tg_channels, limit_per_channel=config.get("telegram_limit_per_channel", 20))
    log(f"TG collected: {len(tg_items)}")
    total += len(tg_items)

    rss_items = collect_rss(rss_sources, limit_per_source=config.get("rss_limit_per_source", 10))
    log(f"RSS collected: {len(rss_items)}")
    total += len(rss_items)

    search_items = collect_search(keywords, limit_per_keyword=config.get("search_limit_per_keyword", 5))
    log(f"Search collected: {len(search_items)}")
    total += len(search_items)

    all_items = tg_items + rss_items + search_items
    with open(items_file, "a", encoding="utf-8") as f:
        for item in all_items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    log(f"Collect step complete: {total} total items written")
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
            f.write(json.dumps(item.__dict__ if hasattr(item, '__dict__') else item, ensure_ascii=False) + "\n")
    return len(unique)


def step_report():
    """Generate and save the final report."""
    items = load_curated_items()
    if not items:
        log("No items to report")
        return ""
    report = generate_report(items)
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

    unique_count = run_step("deduplicate", step_deduplicate)

    report = run_step("report", step_report)
    return report


def main():
    parser = argparse.ArgumentParser(description="news-report skill")
    parser.add_argument("--collect-only", action="store_true", help="Run collection only")
    parser.add_argument("--evaluate-only", action="store_true", help="Run evaluation only")
    parser.add_argument("--full", action="store_true", help="Run full pipeline")
    parser.add_argument("--skip-llm", action="store_true",
                        help="Skip LLM filtering in evaluation (rule-only, fastest)")
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
