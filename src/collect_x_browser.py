#!/usr/bin/env python3
"""X / Twitter browser collector — read the logged-in timeline via Edge CDP.

Different from module 03 (twitter-cli): this collector drives the real logged-in
browser through Chrome DevTools Protocol, so it can
  - deep-scroll the For You / Following timelines (or any custom tab),
  - read retweet attribution ("@user 已转帖") that the CLI JSON omits,
  - merge multiple timeline passes and deduplicate by tweet id.

Requires a running Edge/Chrome with remote debugging (see ``bin/edge-cdp.ps1``
/ ``bin/edge-cdp.sh``) and an x.com session in that browser. When the CDP
endpoint is unreachable, the collector logs a hint and returns ``[]`` so the
pipeline keeps going (graceful skip, same as the other modules).

Environment variables:
  X_BROWSER_CDP_ENDPOINT — CDP base URL (default http://127.0.0.1:9222)
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))

from x_cdp import CDPSession, DEFAULT_BASE, discover, open_page, pick_page  # noqa: E402, I001

_NUM_RE = re.compile(r"(\d[\d,]*\.?\d*)\s*([KMW万]?)")

# JS run inside the page on every scroll pass: extract tweet cards.
_TWEET_EXTRACT_JS = r"""
(() => {
  const out = [];
  for (const a of document.querySelectorAll('article[data-testid="tweet"]')) {
    const link = a.querySelector('a[href*="/status/"]');
    if (!link) continue;
    const href = link.getAttribute('href') || '';
    const m = href.match(/status\/(\d+)/);
    const id = m ? m[1] : null;
    if (!id) continue;
    const userEl = a.querySelector('[data-testid="User-Name"]');
    const social = a.querySelector('[data-testid="socialContext"]');
    const txt = a.querySelector('[data-testid="tweetText"]');
    const time = a.querySelector('time');
    const eng = {};
    for (const k of ['reply', 'retweet', 'like']) {
      const e = a.querySelector('[data-testid="' + k + '"]');
      if (e) eng[k] = (e.innerText || '').trim() || (e.getAttribute('aria-label') || '').trim();
    }
    out.push({
      id,
      url: href.startsWith('/') ? 'https://x.com' + href.split('?')[0] : href,
      who: userEl ? userEl.innerText.replace(/\s+/g, ' ').trim() : null,
      socialContext: social ? social.innerText.replace(/\s+/g, ' ').trim() : null,
      text: txt ? txt.innerText.replace(/\s+/g, ' ').trim() : null,
      dt: time ? time.getAttribute('datetime') : null,
      eng,
    });
  }
  return out;
})()
"""

_CLICK_TAB_JS = r"""
((names) => {
  const tabs = Array.from(document.querySelectorAll('[role="tab"]'));
  for (const name of names) {
    const t = tabs.find(x => (x.innerText || '').trim() === name);
    if (t) { t.click(); return name; }
  }
  return null;
})(ARG_NAMES)
"""


# ─── CDP reachability ──────────────────────────────────────────────────────


def find_cdp_base() -> str:
    return os.environ.get("X_BROWSER_CDP_ENDPOINT", "").strip() or DEFAULT_BASE


def cdp_available(base: str) -> bool:
    try:
        return bool(discover(base, timeout=3))
    except Exception:
        return False


def pick_or_open_x_page(base: str) -> dict[str, Any] | None:
    """Return an x.com page target, opening one if none is open."""
    targets = discover(base, timeout=5)
    page = pick_page(targets, "x.com")
    if page is None:
        try:
            page = open_page("https://x.com/home", base, timeout=5)
        except Exception:
            page = None
    return page


# ─── Timeline pass ─────────────────────────────────────────────────────────


def collect_pass(cdp: CDPSession) -> list[dict[str, Any]]:
    """Extract currently-rendered tweets as raw dicts."""
    try:
        data = cdp.evaluate(_TWEET_EXTRACT_JS)
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    return [d for d in data if isinstance(d, dict) and d.get("id")]


def switch_tab(cdp: CDPSession, timeline: str) -> bool:
    """Click the timeline tab by Chinese/English name. Returns True if clicked."""
    names: list[str] = []
    if timeline == "following":
        names = ["正在关注", "Following"]
    elif timeline == "for_you":
        names = ["为你推荐", "For you"]
    else:
        return False
    try:
        clicked = cdp.evaluate(_CLICK_TAB_JS.replace("ARG_NAMES", json.dumps(names)))
    except Exception:
        return False
    return clicked is not None


def _author_and_time(who: str | None) -> tuple[str, str]:
    if not who:
        return "", ""
    parts = who.split("·")
    author = (parts[0] or "").strip()
    when = (parts[-1] or "").strip() if len(parts) > 1 else ""
    return author, when


def _eng_num(value: Any) -> int:
    """Normalize engagement strings like ``'12 次转帖。转帖'`` or ``'1.2万'`` to ints."""
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        m = _NUM_RE.search(value)
        if m:
            try:
                num = float(m.group(1).replace(",", ""))
            except ValueError:
                return 0
            suffix = m.group(2).upper()
            if suffix == "K":
                num *= 1_000
            elif suffix == "M":
                num *= 1_000_000
            elif suffix in ("W", "万"):
                num *= 10_000
            return int(num)
    return 0


def _to_items(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert raw tweet dicts to the pipeline's standardized item dicts."""
    items: list[dict[str, Any]] = []
    for t in raw:
        text = t.get("text") or ""
        if not text:
            continue
        author, _ = _author_and_time(t.get("who"))
        tweet_id = str(t.get("id", ""))
        url = t.get("url") or f"https://x.com/i/status/{tweet_id}"
        eng = t.get("eng") or {}
        likes = _eng_num(eng.get("like") or eng.get("likes"))
        rts = _eng_num(eng.get("retweet") or eng.get("retweets"))
        replies = _eng_num(eng.get("reply") or eng.get("replies"))

        tags = ["Twitter", "X"]
        social = t.get("socialContext")
        retweeted_by: str | None = None
        if social:
            retweeted_by = social
            tags.append("转帖")

        item: dict[str, Any] = {
            "id": f"xweb_{tweet_id}",
            "title": text[:100] + ("..." if len(text) > 100 else ""),
            "url": url,
            "summary": text[:500],
            "source": f"X-{author}" if author else "X-Timeline",
            "source_type": "twitter",
            "tags": tags,
            "date": t.get("dt") or "",
            "raw_text": text,
            "engagement": {"likes": likes, "retweets": rts, "replies": replies},
        }
        if retweeted_by:
            item["retweeted_by"] = retweeted_by
        items.append(item)
    return items


# ─── Main collector ────────────────────────────────────────────────────────


def collect_x_browser(
    timeline: str = "following",
    scroll_rounds: int = 12,
    scroll_delta: int = 4000,
    settle_seconds: float = 1.0,
) -> list[dict[str, Any]]:
    """Collect tweets from the logged-in X timeline via a CDP browser.

    Args:
        timeline: ``following``, ``for_you``, or ``both`` (merge both passes).
        scroll_rounds: number of wheel scrolls per pass.
        scroll_delta: wheel deltaY per scroll (CSS pixels).
        settle_seconds: wait between scrolls for lazy rendering.

    Returns:
        List of item dicts ready for the evaluation pipeline, or ``[]`` when
        the CDP browser is unreachable or no x.com page is available.
    """
    base = find_cdp_base()

    if not cdp_available(base):
        print(
            "[X-Browser] CDP unreachable — start the browser first: "
            "bin/edge-cdp.ps1 (Windows) or bin/edge-cdp.sh (Linux/macOS)",
            file=sys.stderr,
        )
        return []

    page = pick_or_open_x_page(base)
    if page is None:
        print("[X-Browser] no x.com page and could not open one", file=sys.stderr)
        return []

    ws = page.get("webSocketDebuggerUrl")
    if not ws:
        print("[X-Browser] x.com page has no debugger URL", file=sys.stderr)
        return []

    all_raw: dict[str, dict[str, Any]] = {}
    with CDPSession(ws, timeout=20) as cdp:
        if timeline == "both":
            # Following first, then For You
            for tname in ("following", "for_you"):
                if switch_tab(cdp, tname):
                    time.sleep(3.0)
                for _ in range(scroll_rounds):
                    for t in collect_pass(cdp):
                        all_raw[t["id"]] = t
                    cdp.scroll(scroll_delta)
                    time.sleep(settle_seconds)
                for t in collect_pass(cdp):
                    all_raw[t["id"]] = t
        else:
            if switch_tab(cdp, timeline):
                time.sleep(3.0)
            for _ in range(scroll_rounds):
                for t in collect_pass(cdp):
                    all_raw[t["id"]] = t
                cdp.scroll(scroll_delta)
                time.sleep(settle_seconds)
            for t in collect_pass(cdp):
                all_raw[t["id"]] = t

    items = _to_items(list(all_raw.values()))
    print(
        f"[X-Browser] collected {len(items)} unique tweets "
        f"(timeline={timeline}, rounds={scroll_rounds})",
        file=sys.stderr,
    )
    return items


if __name__ == "__main__":
    timeline = os.environ.get("X_BROWSER_TIMELINE", "following")
    items = collect_x_browser(timeline=timeline)
    json.dump(items, sys.stdout, ensure_ascii=False, indent=2)
    sys.stderr.write(f"total: {len(items)}\n")
