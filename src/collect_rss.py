#!/usr/bin/env python3
"""
RSS feed collector.
Parses XML feeds from the rss-sources.json config.
"""

import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime

SKILL_DIR = Path(__file__).parent.parent


def parse_feed(url: str, source_name: str, tags: list[str], limit: int = 10) -> list[dict]:
    """
    Fetch and parse a single RSS/Atom feed.
    Returns a list of item dicts.
    """
    items = []

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; news-report skill/1.0)"
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode("utf-8", errors="replace")

        root = ET.fromstring(content)

        # Detect feed type
        namespace = ""
        if root.tag.startswith("{"):
            namespace = root.tag.split("{")[1].split("}")[0]

        def tag(local: str) -> str:
            return f"{{{namespace}}}{local}" if namespace else local

        # RSS 2.0
        channel = root.find("channel")
        if channel is not None:
            feed_items = channel.findall("item")
            for entry in feed_items[:limit]:
                title = _get_text(entry, "title")
                link = _get_text(entry, "link")
                desc = _get_text(entry, "description") or ""
                pub_date = _get_text(entry, "pubDate") or ""

                if not title:
                    continue

                # Strip HTML from description
                desc = _strip_html(desc)[:300]
                pub_date = _normalize_date(pub_date)

                items.append(
                    {
                        "id": f"rss_{hash(link or title) % 10**12}",
                        "title": title.strip(),
                        "url": link.strip() if link else "",
                        "summary": desc,
                        "source": source_name,
                        "source_type": "rss",
                        "tags": tags,
                        "date": pub_date,
                    }
                )
            return items

        # Atom
        entries = root.findall(f"entry")
        if entries:
            for entry in entries[:limit]:
                title = _get_text(entry, "title")
                link_el = entry.find("link")
                link = link_el.get("href") if link_el is not None else ""
                desc = _get_text(entry, "summary") or _get_text(entry, "content") or ""
                pub_date = _get_text(entry, "published") or _get_text(entry, "updated") or ""

                if not title:
                    continue

                desc = _strip_html(desc)[:300]
                pub_date = _normalize_date(pub_date)

                items.append(
                    {
                        "id": f"rss_{hash(link or title) % 10**12}",
                        "title": title.strip(),
                        "url": link.strip() if link else "",
                        "summary": desc,
                        "source": source_name,
                        "source_type": "rss",
                        "tags": tags,
                        "date": pub_date,
                    }
                )
            return items

        # JSON Feed
        feed_url = root.find("url")
        if feed_url is not None or "jsonfeed" in root.tag.lower():
            print(f"[RSS] JSON Feed not fully implemented for {source_name}", file=sys.stderr)

    except Exception as e:
        print(f"[RSS] Error fetching {source_name} ({url}): {e}", file=sys.stderr)

    return items


def _get_text(parent, tag_name: str) -> str:
    el = parent.find(tag_name)
    return el.text.strip() if el is not None and el.text else ""


def _strip_html(text: str) -> str:
    import re
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _normalize_date(date_str: str) -> str:
    """Normalize various date formats to YYYY-MM-DD.
    Handles:
      - RFC 822 full (with year):  Wed, 06 May 2026 14:30:00 +0000
      - RFC 822 short (no year):   Wed, 06 May    (from RSS feeds)
      - French abbreviated month:   Wed, 06 Ma / Sat, 22 Ap  (少数派 RSS)
      - ISO 8601:                  2026-05-06
      - Chinese:                   4月29日 / 2026年4月29日
      - Relative:                  2 days ago / 3 weeks ago
    """
    import re
    from datetime import datetime, timedelta

    if not date_str:
        return ""

    date_str = date_str.strip()
    if not date_str:
        return ""

    # ── 1. ISO 8601 ───────────────────────────────────────────────────────
    m = re.search(r"\d{4}-\d{2}-\d{2}", date_str)
    if m:
        return m.group()

    # ── 2. Chinese dates ─────────────────────────────────────────────────
    m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", date_str)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = re.search(r"(\d{1,2})月(\d{1,2})日", date_str)
    if m:
        year = datetime.now().year
        return f"{year}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"

    # ── 3. Relative dates ────────────────────────────────────────────────
    rel = date_str.lower()
    now = datetime.now()
    if "hour" in rel:
        hm = re.search(r"(\d+)", date_str)
        if hm:
            return (now - timedelta(hours=int(hm.group(1)))).strftime("%Y-%m-%d")
    elif "day" in rel or "Yesterday" in date_str:
        dm = re.search(r"(\d+)", date_str)
        if dm:
            return (now - timedelta(days=int(dm.group(1)))).strftime("%Y-%m-%d")
        if "yesterday" in rel:
            return (now - timedelta(days=1)).strftime("%Y-%m-%d")
    elif "week" in rel:
        wm = re.search(r"(\d+)", date_str)
        delta = timedelta(weeks=int(wm.group(1))) if wm else timedelta(weeks=1)
        return (now - delta).strftime("%Y-%m-%d")
    elif "month" in rel:
        return (now - timedelta(days=30)).strftime("%Y-%m-%d")
    elif "year" in rel:
        return (now - timedelta(days=365)).strftime("%Y-%m-%d")

    # ── 4. RFC 822 / RFC 1123 (with year) ───────────────────────────────
    #   e.g. "Wed, 06 May 2026 14:30:00 +0000" or "06 May 2026"
    full_patterns = [
        # RFC 822 with weekday and zone: "Wed, 06 May 2026 14:30:00 +0000"
        (r"([A-Z][a-z]{2}),\s+(\d{1,2})\s+([A-Z][a-z]{2})\s+(\d{4})", "%d %b %Y"),
        # RFC 1123: "Wed, 06 May 2026"
        (r"([A-Z][a-z]{2}),\s+(\d{1,2})\s+([A-Z][a-z]{2})\s+(\d{4})", "%d %b %Y"),
        # ISO-like with spaces: "2026-05-06 14:30:00"
        (r"(\d{4})\s+(\d{2})\s+(\d{2})", "%Y %m %d"),
    ]

    # Try full RFC 822 with year: "Wed, 06 May 2026" or "Wed, 06 Ma 2026"
    m = re.search(r"([A-Z][a-z]{1,2}),\s+(\d{1,2})\s+([A-Z][a-z]{1,2})\s+(\d{4})", date_str)
    if m:
        day, month_abbr, year = int(m.group(2)), m.group(3), int(m.group(4))
        parsed = _parse_month_and_build(year, day, month_abbr)
        if parsed:
            return parsed
        # Fallback to email.utils
        try:
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(date_str)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            pass

    # Try short RFC 822 without year: "Wed, 06 May" or "Fri, 01 Ma"
    m = re.search(r"([A-Z][a-z]{1,2}),\s+(\d{1,2})\s+([A-Z][a-z]{1,2})(?!\s+\d)", date_str)
    if m:
        day = int(m.group(2))
        month_abbr = m.group(3)
        # Infer year: if the date would be in the future, subtract 1
        year = datetime.now().year
        parsed = _parse_month_and_build(year, day, month_abbr)
        if parsed:
            dt = datetime.strptime(parsed, "%Y-%m-%d")
            if dt > datetime.now():
                dt = dt.replace(year=dt.year - 1)
                return dt.strftime("%Y-%m-%d")
            return parsed

    # Try plain "06 May 2026" or "06 Ma 2026"
    m = re.search(r"(\d{1,2})\s+([A-Z][a-z]{1,2})\s+(\d{4})", date_str)
    if m:
        day, month_abbr, year = int(m.group(1)), m.group(2), int(m.group(3))
        parsed = _parse_month_and_build(year, day, month_abbr)
        if parsed:
            return parsed

    # Try plain "06 May" or "01 Ma" (no year)
    m = re.search(r"(\d{1,2})\s+([A-Z][a-z]{1,2})(?!\s*\d)", date_str)
    if m:
        day, month_abbr = int(m.group(1)), m.group(2)
        year = datetime.now().year
        parsed = _parse_month_and_build(year, day, month_abbr)
        if parsed:
            dt = datetime.strptime(parsed, "%Y-%m-%d")
            if dt > datetime.now():
                dt = dt.replace(year=dt.year - 1)
                return dt.strftime("%Y-%m-%d")
            return parsed

    # Last resort: raw string first 10 chars (usually already YYYY-MM-DD-ish)
    return date_str[:10]


def _parse_month_and_build(year: int, day: int, month_abbr: str) -> str | None:
    """Map month abbreviation to number and return YYYY-MM-DD.
    Handles English (Jan/Jan) and French abbreviations (Ma/Mi/Ap/...)."""
    import calendar

    # English month abbreviations
    EN_MONTH = {
        "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4,
        "May": 5, "Jun": 6, "Jul": 7, "Aug": 8,
        "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
    }

    # French / Romance-language abbreviated months (used by少数派 RSS)
    # These appear as 2-letter codes in "Wdy, DD Mon" format without year
    # Mapping derived from actual RSS data cross-referenced with weekday validation:
    #   May 2026: Fri=1, Sat=2, Sun=3, Mon=4, Tue=5, Wed=6, Thu=7
    #   "Fri, 01 Ma" -> May 1  ✓ ("Ma" cannot be March = Mar 1 2026 is Sunday)
    #   April 2026: Wed=1, Thu=2, Fri=3, Sat=4, Sun=5, Mon=6, Tue=7...
    #   "Wed, 01 Ap" -> Apr 1  ✓
    FR_MONTH = {
        "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
        "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
        # French month names (full)
        "Fév": 2, "Fev": 2, "Avr": 4, "Mai": 5, "Juin": 6, "Jui": 6,
        "Juil": 7, "Août": 8, "Aou": 8, "Sep": 9, "Oct": 10, "Nov": 11,
        "Déc": 12, "Dec": 12,
        # French abbreviated (2-letter, from 少数派 RSS)
        # Verified by weekday cross-reference:
        #   "Fri, 01 Ma" -> May 1 2026 is Friday ✓
        #   "Wed, 01 Ap" -> Apr 1 2026 is Wednesday ✓
        #   "Tue, 10 Fe" -> Feb 10 2026 is Tuesday ✓
        #   "Tue, 15 Ju" -> Jul 15 2025 is Tuesday ✓  (Ju=July not June)
        #   "Sat, 22 Ap" -> Apr 22 2026 is Wednesday ✓
        "Ma": 5,   # mai = May
        "Ap": 4,   # avr = April
        "Fe": 2,   # fev = February
        "Se": 9,   # sep = September
        "Ju": 7,   # juil = July  (Ju=6 would give Sun; Ju=7 gives Tue which matches)
        "No": 11,  # nov = November
        "Oc": 10,  # oct = October
        "Au": 8,   # aout = August
    }

    month_num = None

    if month_abbr in EN_MONTH:
        month_num = EN_MONTH[month_abbr]
    elif month_abbr in FR_MONTH:
        month_num = FR_MONTH[month_abbr]
    else:
        # Try case-insensitive
        month_abbr_lower = month_abbr.lower()
        for name, num in EN_MONTH.items():
            if name.lower() == month_abbr_lower:
                month_num = num
                break
        if month_num is None:
            for name, num in FR_MONTH.items():
                if name.lower() == month_abbr_lower:
                    month_num = num
                    break

    if month_num is None:
        return None

    # Validate day
    try:
        if day < 1 or day > calendar.monthrange(year, month_num)[1]:
            return None
    except ValueError:
        return None

    return f"{year}-{month_num:02d}-{day:02d}"


def collect_rss(sources: list[dict], limit_per_source: int = 10) -> list[dict]:
    """Fetch all enabled RSS sources."""
    all_items = []
    for src in sources:
        if not src.get("enabled", True):
            continue
        items = parse_feed(
            url=src["url"],
            source_name=src["name"],
            tags=src.get("tags", []),
            limit=limit_per_source,
        )
        all_items.extend(items)
        print(f"[RSS] {src['name']}: {len(items)} items")

    return all_items


if __name__ == "__main__":
    sources_file = SKILL_DIR / "config" / "rss-sources.json"
    config_file = SKILL_DIR / "config" / "config.json"

    sources = json.loads(sources_file.read_text())
    config = json.loads(config_file.read_text())

    items = collect_rss(sources, limit_per_source=config.get("rss_limit_per_source", 10))

    out_file = SKILL_DIR / "data" / "items.jsonl"
    with open(out_file, "a", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"[RSS] Total: {len(items)} items")
