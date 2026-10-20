#!/usr/bin/env python3
"""
RSS feed collector.
Parses XML feeds from the rss-sources.json config.
"""

import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent


def parse_feed(url: str, source_name: str, tags: list[str], limit: int = 10) -> list[dict]:
    """
    Fetch and parse a single RSS/Atom feed.
    Returns a list of item dicts.
    """
    items = []

    headers = {"User-Agent": "Mozilla/5.0 (compatible; news-report skill/1.0)"}

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
                desc = _strip_noise(_strip_html(desc), title)[:300]
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
        entries = root.findall("entry")
        if entries:
            for entry in entries[:limit]:
                title = _get_text(entry, "title")
                link_el = entry.find("link")
                link = link_el.get("href") or "" if link_el is not None else ""
                desc = _get_text(entry, "summary") or _get_text(entry, "content") or ""
                pub_date = _get_text(entry, "published") or _get_text(entry, "updated") or ""

                if not title:
                    continue

                desc = _strip_noise(_strip_html(desc), title)[:300]
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
    import html
    import re

    # Order matters. Unescape first so that escaped markup ("&lt;p&gt;...")
    # turns into real tags, then strip with a STRICT tag pattern that requires
    # a letter, "/" or "!" right after "<". A loose `<[^>]+>` would also eat
    # literal comparisons: "a &lt; b &amp;&amp; c &gt; d" would collapse to "a d".
    text = html.unescape(text or "")
    text = html.unescape(text)  # second pass catches double-encoded entities
    text = re.sub(r"<[a-zA-Z!/][^>]*>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# Breadcrumb / byline / chrome prefixes that RSS descriptions carry over from the
# source page. Measured across a real run: 7 of 20 selected items started with one
# of these ("首页 > 数码之家 > 奇趣电子 ...", "文 | 指北Focus ...", "0人收藏 分享： ...").
_NOISE_PATTERNS = [
    # 收藏 / 分享 / 评论 动作条
    r"^\d+\s*人\s*(?:收藏|参与|评论|点赞)\s*",
    r"^(?:收藏|分享|点赞|评论)\s*(?:已)?(?:收藏|分享|点赞|评论)?\s*[:：]?\s*",
    # 相关文章推荐块
    r"^相关文章\s*[:：]?\s*",
    # 时间戳 "2026/10/20 21:00:25 "（必须带年份，避免吃掉正文里的 "20 21:00"）
    r"^\d{4}[/-]\d{1,2}[/-]\d{1,2}\s+\d{1,2}:\d{2}(?::\d{2})?\s*",
    # 来源行
    r"^来源\s*[:：]\s*[^\s，。]{1,16}\s*",
]

# Byline prefixes are only stripped from reasonably long text. A 豆瓣 book
# summary is essentially "作者: X 出版社: Y 出版年: Z" — stripping "作者:" there
# would delete the actual content.
_BYLINE_RE = __import__("re").compile(
    r"^(?:文|作者|撰文|编辑|责编|记者)\s*[|｜:：、]\s*[^\s，。]{1,20}\s*",
    __import__("re").IGNORECASE,
)
_NOISE_RE = __import__("re").compile("|".join(_NOISE_PATTERNS), __import__("re").IGNORECASE)

# Metadata markers used to locate the start of real content. Each alternative is
# self-delimiting: we cut right after the marker (and its value, where short).
_MARKER_RES = [
    # "2026/10/20 21:00:25 " timestamp
    __import__("re").compile(r"\d{4}[/-]\d{1,2}[/-]\d{1,2}\s+\d{1,2}:\d{2}(?::\d{2})?\s*"),
    # "来源： IT之家 " / "来源: X"
    __import__("re").compile(r"来源\s*[:：]\s*[^\s，。|｜]{1,16}\s*"),
    # "作者： 故渊 " / "作者 | X"
    __import__("re").compile(r"作者\s*[:：|｜]\s*[^\s，。]{1,20}\s*"),
    # "责编： 故渊 " / "编辑： X"
    __import__("re").compile(r"(?:责编|编辑|撰文|记者)\s*[:：|｜]\s*[^\s，。]{1,20}\s*"),
    # "评论： " (a label with no value; the body follows)
    __import__("re").compile(r"评论\s*[:：]\s*"),
    # "文 | X " at the very start of a credit chain
    __import__("re").compile(r"文\s*[|｜]\s*[^\s，。]{1,20}\s*[，,]?\s*"),
]

# Site-navigation anchors. When a summary starts with one of these, everything up
# to the LAST separator in the head is breadcrumb — a generic "peel one segment at
# a time" rule cannot tell the final crumb ("奇趣电子") from the real title.
_SITE_NAV_RE = __import__("re").compile(
    r"^(?:首页|主页|网站首页|首页\s*>)", __import__("re").IGNORECASE
)

# CMS template placeholders ("{{ postmeta.bookmark }}") that WordPress-style pages
# leave in feed descriptions. Matched anywhere in the summary, not just at the head.
_TEMPLATE_PLACEHOLDER_RE = __import__("re").compile(r"\{\{[^}]*\}\}")

# Leading section labels that IT之家-style feeds prepend ("Win11快讯 ", "IT资讯 ").
# These are category tags, never content. "IT之家" must NOT match — it is the
# publication name that legitimately opens the body text ("IT之家 10 月 20 日消息").
_SECTION_LABEL_RE = __import__("re").compile(
    r"^(?!IT之家)(?:[\u4e00-\u9fa5A-Za-z0-9]{2,10}(?:快讯|资讯|频道|专栏|专题))\s*[|｜:：]?\s*",
    __import__("re").IGNORECASE,
)

# 钛媒体 style: "文 | 青眼观察，作者 | 啸清，编辑 | 封飚 " — credits chained with
# full-width commas. Bounded to at most 4 credits and each credit to 20 chars so
# the pattern cannot run into the body text.
_CREDIT_CHAIN_RE = __import__("re").compile(
    r"^(?:(?:文|作者|撰文|编辑|责编|记者|来源)\s*[|｜:：]\s*[^，。,|｜]{1,20}\s*(?:[，,]\s*)?){1,4}",
    __import__("re").IGNORECASE,
)

# A breadcrumb whose first segment is not a site-nav word still looks like
# "A > B > title"; we only peel if at least two separators appear early.
_BREADCRUMB_RE = __import__("re").compile(r"^(?!\d{4}[/-])([^\s>＞»/]{1,14})\s*[>＞»]\s*")

# Bibliographic metadata must not be mistaken for a byline: 豆瓣 summaries are
# literally "作者: X 出版社: Y 出版年: Z", where 作者 is the content.
_BIBLIO_RE = __import__("re").compile(r"出版社|出版年|ISBN|译者|定价")


def _strip_noise(summary: str, title: str = "") -> str:
    """Trim page chrome so the summary starts at real content.

    Feed descriptions carry arbitrary page scaffolding. Rather than peeling rule
    after rule (which fights itself), find the LAST metadata marker in the leading
    window and start after it. Markers are self-delimiting ("来源：", "作者：",
    "责编：", "评论：", a "2026/10/20 21:00:25" stamp, "首页 > A > B").

    This handles both observed shapes:
      1. "<stamp> 来源： X 作者： Y <body>"
      2. "<section> <title> <stamp> 来源： X 作者： Y 评论： <body>"
    """
    text = (summary or "").strip()
    if not text:
        return ""

    # Template placeholders leaked from CMS pages ("{{ postmeta.bookmark }}",
    # "{{ postmeta.postlike }}"). They are render artifacts, never content.
    text = _TEMPLATE_PLACEHOLDER_RE.sub("", text).strip()

    # Shape 2: the headline is re-published inside the summary; the body follows it.
    if title:
        idx = text.rfind(title)
        if idx > 0:
            text = text[idx + len(title) :].lstrip(" .·-—|｜:：")

    # Breadcrumbs: "首页 > 数码之家 > 奇趣电子 <content>".
    if _SITE_NAV_RE.match(text):
        head = text[:80]
        last = max(head.rfind(">"), head.rfind("＞"), head.rfind("»"))
        if last > 0:
            text = text[last + 1 :]

    # Bibliographic entries (豆瓣书籍) are pure metadata: "作者: X 出版社: Y 出版年: Z".
    # Running the marker pass on them would delete the actual content.
    if _BIBLIO_RE.search(text[:80]):
        return str(text.strip())

    # Find the last metadata marker within the leading window, then cut after it.
    window = text[:220]
    cut = 0
    for rx in _MARKER_RES:
        for m in rx.finditer(window):
            cut = max(cut, m.end())
    if cut:
        text = text[cut:]

    # Anything still leading: bylines, section labels, stray separators.
    text = _strip_credits(text.lstrip(" .·-—|｜:：，、"))
    text = str(_SECTION_LABEL_RE.sub("", text)).strip()
    return text.strip()


def _strip_credits(text: str) -> str:
    """Strip a leading credit chain without eating the body's opening sentence.

    Tricky case: "评论： IT之家 10 月 20 日消息，..." — 「IT之家」 looks like a credit
    value but opens the sentence. Guard: keep it when followed by "X 月 X 日".
    """
    import re as _re

    changed = True
    while changed:
        changed = False
        for rx in (_CREDIT_CHAIN_RE, _BYLINE_RE):
            m = rx.match(text)
            if not m:
                continue
            rest = text[m.end() :]
            if _re.match(r"^[^\s]{0,8}\s*\d{1,2}\s*月\s*\d{1,2}\s*日", rest):
                continue
            text = rest.strip()
            changed = True
    return text


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
    from datetime import timedelta

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

    # Upstream sometimes emits literal junk instead of a date (RSSHub's douban
    # routes send "<pubDate>Invalid Date</pubDate>"). Reject it here so it never
    # reaches the report as a fake date.
    if re.fullmatch(
        r"(?i)\s*(invalid|unknown|n/?a|none|null|undefined)\s*(date|time)?\s*", date_str
    ):
        return ""

    # Last resort: raw string first 10 chars (usually already YYYY-MM-DD-ish)
    # Only trust it when it actually starts with a date; otherwise return "" so
    # the renderer can omit the field instead of printing garbage.
    m = re.match(r"^\d{4}-\d{2}(-\d{2})?", date_str)
    if m:
        return m.group()
    return ""


def _parse_month_and_build(year: int, day: int, month_abbr: str) -> str | None:
    """Map month abbreviation to number and return YYYY-MM-DD.
    Handles English (Jan/Jan) and French abbreviations (Ma/Mi/Ap/...)."""
    import calendar

    # English month abbreviations
    EN_MONTH = {
        "Jan": 1,
        "Feb": 2,
        "Mar": 3,
        "Apr": 4,
        "May": 5,
        "Jun": 6,
        "Jul": 7,
        "Aug": 8,
        "Sep": 9,
        "Oct": 10,
        "Nov": 11,
        "Dec": 12,
    }

    # French / Romance-language abbreviated months (used by少数派 RSS)
    # These appear as 2-letter codes in "Wdy, DD Mon" format without year
    # Mapping derived from actual RSS data cross-referenced with weekday validation:
    #   May 2026: Fri=1, Sat=2, Sun=3, Mon=4, Tue=5, Wed=6, Thu=7
    #   "Fri, 01 Ma" -> May 1  ✓ ("Ma" cannot be March = Mar 1 2026 is Sunday)
    #   April 2026: Wed=1, Thu=2, Fri=3, Sat=4, Sun=5, Mon=6, Tue=7...
    #   "Wed, 01 Ap" -> Apr 1  ✓
    FR_MONTH = {
        "Jan": 1,
        "Feb": 2,
        "Mar": 3,
        "Apr": 4,
        "May": 5,
        "Jun": 6,
        "Jul": 7,
        "Aug": 8,
        "Sep": 9,
        "Oct": 10,
        "Nov": 11,
        "Dec": 12,
        # French month names (full)
        "Fév": 2,
        "Fev": 2,
        "Avr": 4,
        "Mai": 5,
        "Juin": 6,
        "Jui": 6,
        "Juil": 7,
        "Août": 8,
        "Aou": 8,
        "Déc": 12,
        # French abbreviated (2-letter, from 少数派 RSS)
        # Verified by weekday cross-reference:
        #   "Fri, 01 Ma" -> May 1 2026 is Friday ✓
        #   "Wed, 01 Ap" -> Apr 1 2026 is Wednesday ✓
        #   "Tue, 10 Fe" -> Feb 10 2026 is Tuesday ✓
        #   "Tue, 15 Ju" -> Jul 15 2025 is Tuesday ✓  (Ju=July not June)
        #   "Sat, 22 Ap" -> Apr 22 2026 is Wednesday ✓
        "Ma": 5,  # mai = May
        "Ap": 4,  # avr = April
        "Fe": 2,  # fev = February
        "Se": 9,  # sep = September
        "Ju": 7,  # juil = July  (Ju=6 would give Sun; Ju=7 gives Tue which matches)
        "No": 11,  # nov = November
        "Oc": 10,  # oct = October
        "Au": 8,  # aout = August
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
