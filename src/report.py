#!/usr/bin/env python3
"""
Report generator.
Loads curated items, renders them through the template, and outputs formatted report.

⚠️ DEPRECATED (2026-08-09): 旧脚本链路（src/main.py）专用。
当前 `/news_report` 执行路径由 Agent 直接按 SKILL.md 的【输出模板】生成，不经过本脚本。
格式唯一权威标准 = ../SKILL.md →【输出模板】章节（📰 NEWS REPORT + 🔴🟡🟢🔵 优先级分区）。
"""

import json
import re
import sys
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict

# Reuse the shared Item dataclass from evaluator
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
try:
    from evaluator import Item
except ImportError:
    # Fallback: define minimal Item if evaluator not importable
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
        filter_note: str = ""
        challenge_note: str = ""
        dispute_note: str = ""
        raw_text: str = ""
        def __post_init__(self):
            if self.tags is None:
                self.tags = []

SKILL_DIR = Path(__file__).parent.parent


@dataclass
class Item:
    id: str
    title: str
    url: str
    summary: str
    source: str
    source_type: str
    tags: list
    date: str
    verdict: str = ""
    verdict_reason: str = ""
    filter_note: str = ""
    challenge_note: str = ""
    dispute_note: str = ""


# ─── Template ────────────────────────────────────────────────────────────────
# ⚠️ 已弃用：旧格式（📡 资讯汇报 + 话题分组）。
# 当前权威模板见 SKILL.md【输出模板】章节（📰 NEWS REPORT + 🔴🟡🟢🔵 优先级分区 + 📊 来源统计表）。

REPORT_TEMPLATE = """\
📡 **资讯汇报** · {date}

> 采集源：TG×{tg_count} / RSS×{rss_count} / 搜索×{search_count} → 精选 {total} 条

---

{items}

---

_由 news-report skill 生成 · {timestamp}_
"""


ITEM_TEMPLATE = """\
[{display_title}]({url})
"""


def load_curated_items() -> list[Item]:
    """Load items with keep / keep_for_reader / dispute verdicts.
    Dispute items are kept for reader judgment per user requirement.
    """
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
                # raw_text may be present in TG items but not in Item definition
                item_kwargs = {k: v for k, v in d.items() if k in (
                    "id", "title", "url", "summary", "source", "source_type",
                    "tags", "date", "verdict", "verdict_reason",
                    "filter_note", "challenge_note", "dispute_note"
                )}
                items.append(Item(**item_kwargs))
            except Exception:
                pass
    return items


def build_reason(item: Item) -> str:
    """
    Build a clear recommendation reason. Dispute items are noted as contested.
    """
    dispute_note = "（⚠️ 有争议，仅供参考）" if item.verdict == "dispute" else ""

    if item.verdict_reason and len(item.verdict_reason) > 5:
        reason = item.verdict_reason
        # Strip internal scoring language for cleaner output
        reason = reason.replace("综合得分", "").replace("；高价值指标", " | 高价值").replace("；命中", " | 命中")
        reason = reason.strip(" ，,，")
        return (reason + dispute_note)[:120]

    if item.tags:
        return f"属于【{item.tags[0]}】领域，与创作或工作流相关{dispute_note}"
    return f"值得关注的资讯动态{dispute_note}"


def render_item(item: Item) -> str:
    """Render a single item as [title](url)."""
    # Clean title: first line, strip bold markdown and inline links like [text](url)
    title_raw = item.title.strip()
    first_line = title_raw.splitlines()[0].strip()
    display_title = first_line
    # Remove [text](url) → text
    display_title = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', display_title)
    # Remove leftover bare **bold**
    display_title = re.sub(r'\*\*(.+?)\*\*', r'\1', display_title)
    # Remove extra `markdown` backticks
    display_title = re.sub(r'`(.+?)`', r'\1', display_title)
    # Limit to 100 chars for readability
    if len(display_title) > 100:
        cut = display_title[:100].rfind(" ")
        display_title = display_title[:cut] + "…" if cut > 0 else display_title[:100] + "…"

    url = item.url if item.url and item.url not in ("", "（无链接）") else ""
    if url:
        return f"[{display_title}]({url})"
    return display_title


def group_by_relevance(items: list[Item]) -> dict[str, list[Item]]:
    """
    Group items into three buckets:
    - creative: 设计、创作、AI工具
    - investment: 投资、金融、市场
    - general: 其他
    """
    creative_tags = {"AI工具", "设计", "3D", "工作流", "创作工具", "数字艺术", "复古未来主义",
                     "AI视频", "AI", "技术", "OpenClaw"}
    investment_tags = {"投资", "黄金", "基金", "市场分析"}

    buckets = {
        "💡 创作 & 工具": [],
        "📊 投资 & 行业": [],
        "🔮 新动态 / 大厂": [],
        "📦 其他": [],
    }

    for item in items:
        item_tags = set(item.tags)
        if item_tags & creative_tags:
            buckets["💡 创作 & 工具"].append(item)
        elif item_tags & investment_tags:
            buckets["📊 投资 & 行业"].append(item)
        elif item.source_type in ("search", "telegram") and any(
            kw in item.title + item.summary for kw in
            ["AI", "模型", "工具", "设计", "发布", "发布", "开源", "新功能", "模型"]
        ):
            buckets["🔮 新动态 / 大厂"].append(item)
        else:
            buckets["📦 其他"].append(item)

    return buckets


def generate_report(items: list[Item]) -> str:
    """Generate the final formatted report."""
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%Y-%m-%d %H:%M")

    tg_count = sum(1 for it in items if it.source_type == "telegram")
    rss_count = sum(1 for it in items if it.source_type == "rss")
    search_count = sum(1 for it in items if it.source_type == "search")

    TARGET = 20

    buckets = group_by_relevance(items)

    rendered_items = []
    first_section = True
    section_order = ["💡 创作 & 工具", "📊 投资 & 行业", "🔮 新动态 / 大厂", "📦 其他"]

    for section in section_order:
        section_items = buckets.get(section, [])
        if not section_items:
            continue
        if first_section:
            rendered_items.append(f"{section}\n")
            first_section = False
        else:
            rendered_items.append(f"\n· · ·\n{section}\n")
        for item in section_items:
            rendered_items.append(render_item(item).strip())
            rendered_items.append("")

    # Filter empty strings
    items_text = "\n".join(filter(None, rendered_items)).strip()

    report = REPORT_TEMPLATE.format(
        date=date_str,
        tg_count=tg_count,
        rss_count=rss_count,
        search_count=search_count,
        total=len(items),
        items=items_text,
        timestamp=time_str,
    )

    return report


def save_report(report: str):
    """Save report to output directory."""
    now = datetime.now()
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
