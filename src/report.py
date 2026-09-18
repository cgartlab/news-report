#!/usr/bin/env python3
"""
Report generator — SKILL.md canonical format (📰 NEWS REPORT + 🔴🟡🟢🔵 priority zones).

⚠️ Deprecated (2026-08-09): 旧脚本链路（src/main.py）专用。
当前 `/news_report` 执行路径由 Agent 直接按 SKILL.md 的【输出模板】生成，不经过本脚本。
格式唯一权威标准 = ../SKILL.md →【输出模板】章节。

This script is kept as an offline/batch fallback for the script pipeline.
"""

import json
import re
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Reuse the shared Item dataclass from evaluator
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
try:
    from evaluator import Item
except ImportError:
    from dataclasses import dataclass

    @dataclass
    class Item:
        id: str = ""
        title: str = ""
        url: str = ""
        summary: str = ""
        source: str = ""
        source_type: str = ""
        tags: list = None
        date: str = ""
        verdict: str = ""
        verdict_reason: str = ""
        raw_text: str = ""

        def __post_init__(self):
            if self.tags is None:
                self.tags = []

SKILL_DIR = Path(__file__).parent.parent


# ─── Priority Assignment ─────────────────────────────────────────────────────

# Keywords that indicate breaking/urgent news (P0)
URGENT_KW = {
    "突发", "紧急", "紧急通知", "重大", "重大突破", "紧急修复",
    "breaking", "urgent", "emergency", "critical",
}

# Keywords that indicate high-value content (P1)
HIGH_VALUE_KW = {
    "独家", "首发", "开源", "API", "新功能", "发布", "评测",
    "对比", "教程", "工作流", "工具链", "深入", "分析", "研究",
}

# Investment keywords (P1 if investment-related)
INVEST_KW = {
    "投资", "黄金", "基金", "市场", "金融", "经济", "价格", "ETF",
    "纳斯达克", "美股", "A股", "港股", "收益", "定投", "理财",
    "净值", "估值", "分红",
}


def assign_priority(item: Item) -> str:
    """Assign priority level (P0-P3) to an item based on verdict and content.

    Mapping:
      keep + urgent keywords → P0 (🔴 紧急)
      keep + high-value/investment/creative keywords → P1 (🟡 关注)
      keep + plain content → P2 (🟢 常规)
      dispute → P2 (🟢 常规)
      everything else → P3 (🔵 背景)
    """
    text = (item.title + " " + item.summary).lower()

    # P0: urgent / breaking news
    if any(kw in text for kw in URGENT_KW):
        return "P0"

    # P1: high-value, investment, or creative content
    if any(kw in text for kw in HIGH_VALUE_KW):
        return "P1"
    if any(kw in text for kw in INVEST_KW):
        return "P1"

    # P2: regular keep items and all dispute items
    if item.verdict in ("keep", "keep_for_reader"):
        return "P2"
    if item.verdict == "dispute":
        return "P2"

    # P3: background / low priority
    return "P3"


# ─── Item Loading ────────────────────────────────────────────────────────────

def load_curated_items() -> list[Item]:
    """Load items with keep / keep_for_reader / dispute verdicts."""
    fpath = SKILL_DIR / "data" / "items.jsonl"
    if not fpath.exists():
        return []

    items = []
    with open(fpath, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                if d.get("verdict") not in ("keep", "keep_for_reader", "dispute"):
                    continue
                item_kwargs = {k: v for k, v in d.items() if k in (
                    "id", "title", "url", "summary", "source", "source_type",
                    "tags", "date", "verdict", "verdict_reason",
                    "raw_text"
                )}
                items.append(Item(**item_kwargs))
            except Exception:
                pass
    return items


# ─── Item Rendering ──────────────────────────────────────────────────────────

def render_title(item: Item) -> str:
    """Clean and render an item title."""
    title_raw = item.title.strip()
    first_line = title_raw.splitlines()[0].strip()
    display_title = first_line
    # Remove [text](url) → text
    display_title = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', display_title)
    # Remove leftover **bold**
    display_title = re.sub(r'\*\*(.+?)\*\*', r'\1', display_title)
    # Remove extra `markdown` backticks
    display_title = re.sub(r'`(.+?)`', r'\1', display_title)
    # Limit to 100 chars for readability
    if len(display_title) > 100:
        cut = display_title[:100].rfind(" ")
        display_title = display_title[:cut] + "…" if cut > 0 else display_title[:100] + "…"
    return display_title


def render_item_p1_p0(item: Item) -> str:
    """Render item with summary + inline link (P0/P1 format)."""
    title = render_title(item)
    url = item.url if item.url and item.url not in ("", "（无链接）") else ""
    source_label = f"📡 {item.source}"

    # Inline link in title
    if url:
        link_title = f"[{title}]({url})"
    else:
        link_title = title

    # Summary (≤200 chars for group chat)
    summary = item.summary[:200].strip() if item.summary else ""

    lines = [link_title]
    if summary:
        lines.append(f"  {summary}")
    lines.append(f"  {source_label}")

    return "\n".join(lines)


def render_item_p2(item: Item) -> str:
    """Render item with title + metadata only (P2 format)."""
    title = render_title(item)
    url = item.url if item.url and item.url not in ("", "（无链接）") else ""
    date_str = item.date[:10] if item.date else ""
    source_label = f"📡 {item.source}"

    if url:
        link_title = f"[{title}]({url})"
    else:
        link_title = title

    meta_parts = []
    if date_str:
        meta_parts.append(date_str)
    meta_parts.append(source_label)

    return f"{link_title}  {' · '.join(meta_parts)}"


def render_item_p3(item: Item) -> str:
    """Render item with title + source only (P3 format)."""
    title = render_title(item)
    source_label = f"📡 {item.source}"
    return f"{title}  {source_label}"


# ─── Report Generation ───────────────────────────────────────────────────────

DIVIDER = "══" * 20
SEPARATOR = "──" * 20


def generate_report(items: list[Item]) -> str:
    """Generate the final formatted report in SKILL.md canonical format."""
    # Use GMT+8 for display
    gmt8 = timezone(timedelta(hours=8))
    now = datetime.now(gmt8)
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%Y-%m-%d %H:%M")

    # Source counts
    tg_count = sum(1 for it in items if it.source_type == "telegram")
    rss_count = sum(1 for it in items if it.source_type == "rss")
    search_count = sum(1 for it in items if it.source_type == "search")
    other_count = sum(1 for it in items if it.source_type not in ("telegram", "rss", "search"))

    # Assign priorities and group
    p0_items = []
    p1_items = []
    p2_items = []
    p3_items = []

    for item in items:
        priority = assign_priority(item)
        if priority == "P0":
            p0_items.append(item)
        elif priority == "P1":
            p1_items.append(item)
        elif priority == "P2":
            p2_items.append(item)
        else:
            p3_items.append(item)

    lines = []

    # ── Header ──
    lines.append(DIVIDER)
    lines.append(f"📰 NEWS REPORT · {date_str} {now.strftime('%H:%M')} GMT+8")
    lines.append(DIVIDER)
    lines.append(f"📡 信源：RSS×{rss_count} / TG×{tg_count} / Web×{search_count}"
                 + (f" / 其他×{other_count}" if other_count else "")
                 + f" → 精选 {len(items)} 条")
    lines.append(f"🔴 {len(p0_items)} / 🟡 {len(p1_items)} / 🟢 {len(p2_items)} / 🔵 {len(p3_items)}")
    lines.append(DIVIDER)
    lines.append("")

    # ── P0: 紧急 ──
    if p0_items:
        lines.append("🔴 紧急 (P0)")
        lines.append(SEPARATOR)
        for item in p0_items:
            lines.append(render_item_p1_p0(item))
            lines.append("")
        lines.append("")

    # ── P1: 关注 ──
    if p1_items:
        lines.append("🟡 关注 (P1)")
        lines.append(SEPARATOR)
        for item in p1_items:
            lines.append(render_item_p1_p0(item))
            lines.append("")
        lines.append("")

    # ── P2: 常规 ──
    if p2_items:
        lines.append("🟢 常规 (P2)")
        lines.append(SEPARATOR)
        for item in p2_items:
            lines.append(render_item_p2(item))
        lines.append("")

    # ── P3: 背景 ──
    if p3_items:
        lines.append("🔵 背景 (P3)")
        lines.append(SEPARATOR)
        for item in p3_items:
            lines.append(render_item_p3(item))
        lines.append("")

    # ── Footer: source statistics ──
    lines.append(DIVIDER)
    lines.append("📊 来源统计")
    lines.append(f"| 来源 | 条数 |")
    lines.append(f"|------|------|")
    from collections import Counter
    source_counts = Counter(it.source for it in items)
    for source_name, count in sorted(source_counts.items(), key=lambda x: (-x[1], x[0])):
        lines.append(f"| {source_name} | {count} |")
    lines.append(DIVIDER)

    return "\n".join(lines)


def save_report(report: str):
    """Save report to output directory."""
    gmt8 = timezone(timedelta(hours=8))
    now = datetime.now(gmt8)
    out_dir = SKILL_DIR / "output"
    out_dir.mkdir(exist_ok=True)

    filename = now.strftime("%Y-%m-%d-%H%M") + ".md"
    fpath = out_dir / filename
    fpath.write_text(report, encoding="utf-8")
    print(f"[Report] Saved to {fpath}")

    # Also save latest.md as most recent
    latest = out_dir / "latest.md"
    latest.write_text(report, encoding="utf-8")


def generate_and_output() -> str:
    """Main entry point."""
    items = load_curated_items()
    if not items:
        print("[Report] No curated items found, nothing to report.")
        return ""

    report = generate_report(items)
    save_report(report)
    print(f"[Report] Generated report with {len(items)} items")
    return report


if __name__ == "__main__":
    report = generate_and_output()
    if report:
        print("\n" + "=" * 40)
        print(report)
