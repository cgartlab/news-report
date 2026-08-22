#!/usr/bin/env python3
"""
Semantic deduplicator.
Uses LLM to assess whether two items are duplicates, then merges.
Threshold: items with >75% semantic overlap are merged (the more complete one wins).
"""

import json
import subprocess
import sys
from pathlib import Path
from dataclasses import dataclass

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
    raw_text: str = ""


def load_items() -> list[Item]:
    items = []
    fpath = SKILL_DIR / "data" / "items.jsonl"
    if not fpath.exists():
        return []
    with open(fpath, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                if d.get("verdict") not in ("keep", "keep_for_reader"):
                    continue
                if "raw_text" not in d:
                    d["raw_text"] = ""
                items.append(Item(**d))
            except Exception:
                pass
    return items


def _call_llm(prompt: str) -> str:
    api_key = _get_api_key()
    if not api_key:
        return "no"

    # Try SiliconFlow endpoint
    url = "https://api.siliconflow.com/v1/chat/completions"
    payload = {
        "model": "deepseek-ai/DeepSeek-V4-Flash",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 50,
    }

    try:
        proc = subprocess.run(
            ["curl", "-s", url, "-X", "POST",
             "-H", f"Authorization: Bearer {api_key}",
             "-H", "Content-Type: application/json",
             "-d", json.dumps(payload)],
            capture_output=True, text=True, timeout=20,
        )
        resp = json.loads(proc.stdout)
        if "choices" in resp:
            return resp["choices"][0]["message"]["content"]
        return "no"
    except Exception:
        return "no"


def _get_api_key() -> str:
    """Return SiliconFlow API key if found in TOOLS.md, else empty."""
    tools_md = Path("/root/.openclaw/workspace/TOOLS.md")
    if not tools_md.exists():
        return ""
    for line in tools_md.read_text().splitlines():
        if 'SiliconFlow' in line or 'DeepSeek' in line:
            for part in line.split('|'):
                part = part.strip()
                if part.startswith('sk-'):
                    return part
    return ""


DEDUP_PROMPT = """\
判断以下两条信息是否在讨论同一件事（语义重复）。只回答 yes 或 no。

标题A：{title_a}
摘要A：{summary_a}

标题B：{title_b}
摘要B：{summary_b}

判断（yes=重复，no=不重复）：
"""


def is_duplicate(a: Item, b: Item, threshold: float = 0.75) -> bool:
    """
    Keyword-based duplicate detection using Jaccard similarity.
    LLM calls removed — they caused timeouts in the pipeline.
    """
    # Normalize: title words + first 200 chars of summary
    words_a = set((a.title + " " + a.summary[:200]).lower().split())
    words_b = set((b.title + " " + b.summary[:200]).lower().split())

    # Remove very common stopwords to reduce noise
    stopwords = {"the", "a", "an", "of", "in", "to", "for", "and", "or", "on", "is", "it", "with", "as", "by", "at", "be", "this", "that", "are", "was", "were", "has", "have", "had", "not", "but", "from", "or", "and", "新", "的", "是", "在", "了", "和", "与", "为", "对", "将", "把", "被", "要", "有", "可", "以", "也"}
    words_a -= stopwords
    words_b -= stopwords

    if not words_a or not words_b:
        return False

    intersection = words_a & words_b
    union = words_a | words_b
    jaccard = len(intersection) / len(union)

    # Also check URL overlap
    url_match = (a.url and b.url and a.url == b.url)

    return jaccard > threshold or url_match


def deduplicate(items: list[Item]) -> list[Item]:
    """
    Remove duplicate items, keeping the one with the longer/more complete summary.
    """
    if len(items) <= 1:
        return items

    unique = []
    duplicates_found = 0

    for candidate in items:
        is_dup = False
        for existing in unique:
            if is_duplicate(existing, candidate):
                # Keep the one with more content
                if len(candidate.summary) > len(existing.summary):
                    unique.remove(existing)
                    unique.append(candidate)
                    print(f"[Dedup] Merged: {candidate.title[:60]}...")
                duplicates_found += 1
                is_dup = True
                break

        if not is_dup:
            unique.append(candidate)

    print(f"[Dedup] {len(items)} → {len(unique)} items ({duplicates_found} duplicates removed)")
    return unique


if __name__ == "__main__":
    items = load_items()
    unique = deduplicate(items)
    print(f"Unique items: {len(unique)}")
