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
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Reuse the shared Item dataclass from evaluator
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
# noqa: E402 — import after sys.path bootstrap
from evaluator import (  # noqa: E402,F401
    _NEWS_SOURCE_RE,
    _P0_STRONG_KW,
    _P0_WEAK_KW,
    Item,
)

SKILL_DIR = Path(__file__).parent.parent


def _is_aggregate_title(title: str) -> bool:
    """True when a title packs several distinct news items into one link.

    Daily-digest pages ("早报", "晚报") publish one entry whose title chains
    stories with "；" or "|". Such a link opens a list, so the headline keywords
    it contains do not describe what the reader will actually land on.

    Threshold: >=2 strong separators AND a reasonably long title. A normal
    headline rarely uses two semicolons; quoted speech uses commas instead.
    """
    t = (title or "").strip()
    if len(t) < 30:
        return False
    separators = t.count("；") + t.count(";") + t.count("｜")
    return separators >= 2


def assign_priority(item: Item) -> str:
    """Priority for the report.

    The LLM pass (evaluator.assign_semantic_priorities) decides P0–P3 semantically
    and stores it on item.priority. This function only translates that stored value
    and applies keyword fallback when it is missing (e.g. --skip-llm or an item that
    bypassed the LLM). It does NOT re-guess P0 from bare keywords — the Microsoft
    "digital sovereignty" blog incident showed a blog hitting "critical" does not
    make it breaking news.

    Mapping (docstring kept from the older keyword version):
      P0 (🔴 紧急)   — semantic: safety / historic / market-moving / revolutionary
      P1 (🟡 关注)   — high value, below P0
      P2 (🟢 常规)   — regular
      P3 (🔵 背景)   — background
    """
    if getattr(item, "priority", "") in ("P0", "P1", "P2", "P3"):
        return item.priority

    # Fallback when priority was not assigned (no LLM, or bypassed item).
    # Keyword fallback is conservative: only a news outlet + strong breaking word
    # may claim P0; everything else degrades to P1/P2.
    t = (item.title + " " + item.summary).lower()
    kept = item.verdict in ("keep", "keep_for_reader")

    # Aggregate titles ("A；B；C" — a digest page packing several stories) never
    # take P0/P1, whatever their keywords say.
    if kept and _is_aggregate_title(item.title):
        return "P2"

    is_news = bool(_NEWS_SOURCE_RE.search(item.source or ""))
    has_strong = any(kw.lower() in t for kw in _P0_STRONG_KW)
    has_weak = any(kw.lower() in t for kw in _P0_WEAK_KW)

    if kept and has_strong and is_news:
        return "P0"
    if kept and has_weak and is_news:
        return "P1"

    # P2: regular keep items and all dispute items
    if kept:
        return "P2"
    if item.verdict == "dispute":
        return "P2"
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
                item_kwargs = {
                    k: v
                    for k, v in d.items()
                    if k
                    in (
                        "id",
                        "title",
                        "url",
                        "summary",
                        "source",
                        "source_type",
                        "tags",
                        "date",
                        "verdict",
                        "verdict_reason",
                        "priority",
                        "raw_text",
                    )
                }
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
    display_title = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", display_title)
    # Remove leftover **bold**
    display_title = re.sub(r"\*\*(.+?)\*\*", r"\1", display_title)
    # Remove extra `markdown` backticks
    display_title = re.sub(r"`(.+?)`", r"\1", display_title)
    # Limit to 100 chars for readability
    if len(display_title) > 100:
        cut = display_title[:100].rfind(" ")
        display_title = display_title[:cut] + "…" if cut > 0 else display_title[:100] + "…"
    return display_title


def _summary_140(item: Item) -> str:
    """Trim the summary to ~140 display characters, cutting at a sentence or word
    boundary and appending an ellipsis. Chosen so each item tells the reader
    enough to decide whether to open it — dense but scannable."""
    raw = (item.summary or "").strip()
    if not raw:
        return ""

    # Cut at a clean boundary: prefer a Chinese/English sentence end, else a space.
    if len(raw) <= 140:
        return raw

    cut = 140
    # Try last sentence terminator before the limit.
    for sep in ("。", "！", "？", "．", ". ", "! ", "? "):
        pos = raw.rfind(sep, 0, cut + 1)
        if 0 < pos < cut:
            cut = pos + len(sep)
            break
    # Else fall back to a word boundary (avoid splitting a word).
    else:
        pos = raw.rfind(" ", 0, cut + 1)
        if pos > 0:
            cut = pos
    return raw[:cut].rstrip() + "…"


def render_item_p1_p0(item: Item) -> str:
    """Render item with summary + inline link (P0/P1 format)."""
    title = render_title(item)
    url = item.url if item.url and item.url not in ("", "（无链接）") else ""
    source_label = f"📡 {item.source}"

    # Inline link in title
    link_title = f"[{title}]({url})" if url else title

    # Summary (~140 chars for group chat)
    summary = _summary_140(item)

    lines = [link_title]
    if summary:
        lines.append(f"  {summary}")
    lines.append(f"  {source_label}")

    return "\n".join(lines)


def render_item_p2(item: Item) -> str:
    """Render item with title + summary + source (P2 also gets the same shape)."""
    title = render_title(item)
    url = item.url if item.url and item.url not in ("", "（无链接）") else ""
    date_str = item.date[:10] if item.date else ""
    source_label = f"📡 {item.source}"

    link_title = f"[{title}]({url})" if url else title

    lines = [link_title]
    summary = _summary_140(item)
    if summary:
        lines.append(f"  {summary}")

    meta_parts = []
    if date_str:
        meta_parts.append(date_str)
    meta_parts.append(source_label)
    lines.append("  " + " · ".join(meta_parts))
    return "\n".join(lines)


def render_item_p3(item: Item) -> str:
    """Render item with title + source only (P3 format)."""
    title = render_title(item)
    source_label = f"📡 {item.source}"
    return f"{title}  {source_label}"


# ─── Report Generation ───────────────────────────────────────────────────────

DIVIDER = "══" * 20
SEPARATOR = "──" * 20


def generate_report(items: list[Item], collected: int = 0, sources: int = 0) -> str:
    """Generate the final formatted report in SKILL.md canonical format.

    Args:
        items: the selected (curated) items to render.
        collected: how many raw items were collected before evaluation.
        sources: how many distinct sources those raw items came from.
    """
    # Use GMT+8 for display
    gmt8 = timezone(timedelta(hours=8))
    now = datetime.now(gmt8)
    date_str = now.strftime("%Y-%m-%d")

    # Source counts (of the SELECTED items, by type) — kept for the type line.
    tg_count = sum(1 for it in items if it.source_type == "telegram")
    rss_count = sum(1 for it in items if it.source_type == "rss")
    search_count = sum(1 for it in items if it.source_type == "search")
    other_count = sum(1 for it in items if it.source_type not in ("telegram", "rss", "search"))
    selected_sources = len({it.source for it in items if getattr(it, "source", "")})

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
    # Report the collection scale first: the old "RSS×20" line only counted the
    # SELECTED items by type, which reads like "20 RSS feeds were used" and hid
    # both the true collection volume and the Miniflux contribution.
    lines.append(DIVIDER)
    lines.append(f"📰 NEWS REPORT · {date_str} {now.strftime('%H:%M')} GMT+8")
    lines.append(DIVIDER)
    if collected:
        lines.append(
            f"📡 采集 {collected} 条 / {sources or selected_sources} 个源"
            f" → 精选 {len(items)} 条（{selected_sources} 个源）"
        )
    else:
        lines.append(f"📡 精选 {len(items)} 条 / {selected_sources} 个源")
    # Type breakdown of the selected items (RSS / TG / Web), kept separate from
    # the collection-scale line so neither number is misread as the other.
    type_bits = [f"RSS×{rss_count}"] if rss_count else []
    if tg_count:
        type_bits.append(f"TG×{tg_count}")
    if search_count:
        type_bits.append(f"Web×{search_count}")
    if other_count:
        type_bits.append(f"其他×{other_count}")
    if type_bits:
        lines.append("　　" + " / ".join(type_bits))
    lines.append(
        f"🔴 {len(p0_items)} / 🟡 {len(p1_items)} / 🟢 {len(p2_items)} / 🔵 {len(p3_items)}"
    )
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
    lines.append("| 来源 | 条数 |")
    lines.append("|------|------|")
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
