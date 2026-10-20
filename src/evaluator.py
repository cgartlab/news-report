#!/usr/bin/env python3
"""
Multi-agent semantic evaluator — optimized for speed and resilience.

Speed optimizations:
- SiliconFlow DeepSeek V4 Flash (first choice, faster than MiniMax)
- Larger batch size → fewer LLM calls
- Concise prompt (no redundant Chinese framing)
- Rule-pass primary: only borderline items go to LLM
- Incremental saves after each phase
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from threading import Lock

SKILL_DIR = Path(__file__).parent.parent

# ─── Config ──────────────────────────────────────────────────────────────────

BATCH_SIZE = 5  # items per LLM batch (was 2, increase = fewer calls)
MAX_RETRIES = 1  # was 2; 1 retry is enough with fast model
RETRY_DELAYS = (5,)  # seconds before retry
LLM_TIMEOUT = 50  # seconds per LLM call (bump from 40)
MAX_WORKERS = 3  # parallel LLM calls (was 4)


# ─── HTTP Helper ─────────────────────────────────────────────────────────────


def _http_post(url: str, payload: dict, key: str, timeout: int = 30) -> str:
    """POST JSON to an API endpoint using urllib (cross-platform, no curl)."""
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return str(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as e:
        return json.dumps(
            {"error": f"HTTP {e.code}: {e.read().decode('utf-8', errors='replace')[:200]}"}
        )
    except urllib.error.URLError as e:
        return json.dumps({"error": str(e.reason)})
    except Exception as e:
        return json.dumps({"error": str(e)})


# ─── LLM API Discovery ───────────────────────────────────────────────────────

_llm_lock = Lock()
_llm_config = None  # (url, key, model)


def _find_llm():
    """
    Find first working LLM API from environment variables.
    Priority: SenseNova → MiniMax → SiliconFlow → DeepSeek (first with a non-empty env var wins).
    Keys are read from: SENSENOVA_API_KEY, MINIMAX_API_KEY, SILICONFLOW_API_KEY, DEEPSEEK_API_KEY
    """
    global _llm_config
    if _llm_config is not None:
        return _llm_config

    sensenova_key = os.environ.get("SENSENOVA_API_KEY", "").strip()
    minimax_key = os.environ.get("MINIMAX_API_KEY", "").strip()
    sf_key = os.environ.get("SILICONFLOW_API_KEY", "").strip()
    deepseek_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()

    candidates = []
    if sensenova_key:
        candidates.append(
            (
                "https://token.sensenova.cn/v1/chat/completions",
                sensenova_key,
                "sensenova-6.8-flash-lite",
            )
        )
    if minimax_key:
        candidates.append(
            ("https://api.minimax.chat/v1/chat/completions", minimax_key, "MiniMax-M2.7")
        )
    if sf_key:
        candidates.append(
            (
                "https://api.siliconflow.com/v1/chat/completions",
                sf_key,
                "deepseek-ai/DeepSeek-V4-Flash",
            )
        )
    if deepseek_key:
        candidates.append(
            ("https://api.deepseek.com/chat/completions", deepseek_key, "deepseek-chat")
        )

    if not candidates:
        with _llm_lock:
            _llm_config = (None, None, None)
        print(
            "[Evaluator] No LLM API keys set — using rule-based only "
            "(set MINIMAX_API_KEY / SILICONFLOW_API_KEY / DEEPSEEK_API_KEY)"
        )
        return None, None, None

    for url, key, model in candidates:
        test_payload = {
            "model": model,
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 50,
        }
        raw = _http_post(url, test_payload, key, timeout=10)
        try:
            resp = json.loads(raw)
            if "error" not in resp and "choices" in resp:
                with _llm_lock:
                    _llm_config = (url, key, model)
                print(f"[Evaluator] LLM ready: {url.split('/')[2]} / {model}")
                return _llm_config
        except Exception:
            pass

    with _llm_lock:
        _llm_config = (None, None, None)
    print("[Evaluator] No LLM API responded — using rule-based only")
    return None, None, None


def call_llm(prompt: str, *, max_tokens: int = 600, temperature: float = 0.3) -> str:
    """Single LLM call with retries and timeout."""
    url, key, model = _find_llm()
    if not url:
        return ""

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    for attempt in range(MAX_RETRIES + 1):
        try:
            raw = _http_post(url, payload, key, timeout=LLM_TIMEOUT)
            resp = json.loads(raw)
            if "error" in resp:
                raise ValueError(resp["error"])
            msg = resp["choices"][0]["message"]
            return str(msg.get("content", msg.get("reasoning", "")))
        except Exception as e:
            if attempt < MAX_RETRIES:
                delay = RETRY_DELAYS[attempt] if attempt < len(RETRY_DELAYS) else 3
                print(f"[Evaluator] LLM failed (attempt {attempt + 1}), retry in {delay}s: {e}")
                time.sleep(delay)
            else:
                print(f"[Evaluator] LLM failed after {MAX_RETRIES + 1} attempts: {e}")
    return ""


# ─── Dataclass ────────────────────────────────────────────────────────────────


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
    verdict: str = "pending"
    verdict_reason: str = ""
    # Semantic priority assigned by the LLM pass (P0/P1/P2/P3). Decided at eval
    # time, NOT by keyword guessing in report.py — see assign_priority there.
    priority: str = ""
    filter_note: str = ""
    challenge_note: str = ""
    dispute_note: str = ""
    raw_text: str = ""


# ─── Rule-Based Primary Scorer ───────────────────────────────────────────────

CREATIVE_KW = {
    "AI",
    "设计",
    "工具",
    "3D",
    "C4D",
    "Unity",
    "创作",
    "工作流",
    "视觉",
    "动态",
    "视频",
    "生成",
    "模型",
    "开源",
    "发布",
    "GPT",
    "Claude",
    "工具链",
    "插件",
    "设计系统",
    "UI",
    "UX",
    "字体",
    "配色",
    "动效",
    "艺术",
    "数字艺术",
}
INVEST_KW = {
    "投资",
    "黄金",
    "基金",
    "市场",
    "金融",
    "经济",
    "价格",
    "ETF",
    "纳斯达克",
    "美股",
    "A股",
    "港股",
    "收益",
    "定投",
    "理财",
    "净值",
    "估值",
    "分红",
}
HIGH_VALUE_KW = {
    "独家",
    "首发",
    "开源",
    "API",
    "新功能",
    "发布",
    "评测",
    "对比",
    "教程",
    "工作流",
    "工具链",
    "深入",
    "分析",
    "研究",
}
SKIP_PATTERNS = [
    "joined",
    "已加入",
    "登录",
    "验证码",
    "注册",
    "welcome",
    "click here",
    "subscribe",
    "unsubscribe",
    "查看详情",
    "立即购买",
    "点击获取",
    "限时",
    "扫码",
]
ENGAGEMENT_BAIT = [
    "震惊",
    "必看",
    "绝了",
    "太牛了",
    "太可怕",
    "你不知道",
    "突发",
    "刚刚",
    "刚刚宣布",
    "重磅",
]
TECH_SOURCES = {
    "github.com",
    "arxiv.org",
    "huggingface.co",
    "gitlab.com",
    "figma.com",
    "toolify.ai",
}


# Title-level markers for calls-to-action that are not news: 征文/征稿/招募/征集.
# These are matched against the TITLE ONLY — as a full-text substring they would
# wrongly discard every article that merely mentions "征文" in passing.
_CTA_TITLE_RE = __import__("re").compile(
    r"(征文|征稿|投稿|有奖征集|作品征集|招募|征集令|报名开启|报名中)",
    __import__("re").IGNORECASE,
)
_CTA_STRONG_RE = __import__("re").compile(r"(征文|征稿|征集令|有奖征集|作品征集)")


# Low-value / no-cognitive-gain content. The user's rule: high-value is defined by
# interest (AI/design/invest/productivity/digital sovereignty/big tech/retro-futurism),
# and low-value is everything that fails that test while also being celebrity gossip,
# unverified rumors, or clickbait with no information gain. These are TITLE-level
# strong negatives: they must never reach the final report even if the LLM is down.
#
# Strong negatives — one hit discards immediately:
_LOW_VALUE_STRONG_RE = __import__("re").compile(
    r"(明星|八卦|绯闻|恋情|出轨|塌房|私生活|狗仔|"
    r"网传|传闻|爆料|知情人士|据传|小道消息|"
    r"星座|运势|占卜|塔罗|风水|"
    r"心灵鸡汤|成功学|养生秘方|排毒|冥想速成)",
    __import__("re").IGNORECASE,
)

# Weak negatives — demote strongly but do not auto-discard (they can be real news):
_LOW_VALUE_WEAK_RE = __import__("re").compile(
    r"(离婚|结婚|分手|官宣|整容|"
    r"疑似|猜测|听说|据说|或将|可能推出|"
    r"减肥|穿搭|妆容|追星|饭圈)",
    __import__("re").IGNORECASE,
)


def rule_score(item: Item) -> tuple[str, str]:
    """
    Primary rule-based scorer — no API needed, runs instantly.
    Returns (verdict, reason).
    """
    title_lower = (item.title + item.summary).lower()
    text_blob = " ".join([item.title, item.summary, item.raw_text or ""]).lower()
    reasons = []
    score = 0.0

    # Penalties
    if any(p in text_blob for p in SKIP_PATTERNS):
        return "discard", "系统消息/低价值通知类内容"

    # Calls-to-action (征文/征稿/招募) are announcements, not news. Strong markers
    # discard; weak ones ("招募") only demote, since they can appear in real news.
    if _CTA_STRONG_RE.search(item.title or ""):
        return "discard", "征稿/征文类公告，非新闻"
    if _CTA_TITLE_RE.search(item.title or ""):
        score -= 2.5
        reasons.append("征集/招募类")

    # Low-value content: celebrity gossip, unverified rumors, astrology, life-hack
    # clickbait. Strong markers discard outright; weak ones demote below the keep
    # threshold so the LLM/selection pass would need strong reasons to bring them back.
    if _LOW_VALUE_STRONG_RE.search(item.title or ""):
        return "discard", "低价值内容（明星八卦/小道消息/无认知增量）"
    if _LOW_VALUE_WEAK_RE.search(item.title or ""):
        score -= 3.0
        reasons.append("低价值弱信号")

    bait_count = sum(1 for p in ENGAGEMENT_BAIT if p in title_lower)
    if bait_count >= 2:
        score -= 3
        reasons.append("标题党")
    elif bait_count == 1:
        score -= 1

    if len(item.summary) < 50 and len(item.raw_text or "") < 50:
        if item.source_type == "rss":
            pass  # RSS summaries are naturally short, don't penalize
        else:
            score -= 1.5

    # Bonuses
    creative_hit = sum(1 for kw in CREATIVE_KW if kw in title_lower)
    if creative_hit:
        score += creative_hit * 0.8

    invest_hit = sum(1 for kw in INVEST_KW if kw in title_lower)
    if invest_hit:
        score += invest_hit * 1.2
        reasons.append(f"投资关键词×{invest_hit}")

    for kw in HIGH_VALUE_KW:
        if kw in title_lower:
            score += 2.5
            reasons.append(f"高价值: {kw}")
            break

    if item.source_type == "rss":
        score += 0.5
    if item.source_type == "telegram" and any(src in (item.url or "") for src in TECH_SOURCES):
        score += 1.5

    if len(item.summary) >= 300:
        score += 1

    # Verdict (lower threshold to let more good RSS/TG items through)
    if score >= 2.0:
        verdict = "keep"
    elif score >= 0.3:
        verdict = "dispute"
    else:
        verdict = "discard"

    if reasons:
        reason_str = "；".join(reasons)
    else:
        reason_str = f"得分{score:.1f}无明显特征" if score != 0 else "无相关特征"
    return verdict, reason_str[:120]


# ─── LLM Filter (Secondary) ──────────────────────────────────────────────────

FILTER_ITEM_TEMPLATE = """\
标题：{title}
摘要：{summary}
来源：{source}（{source_type}）
标签：{tags}
判断：keep / discard"""

FILTER_BATCH_TEMPLATE = """\
以下{count}条信息，判断是否值得进入资讯汇报（keep=值得，discard=不值得），
并为 keep 的条目给出优先级（priority）。

优先级判定标准（P0 最高，只给真正重大的信号，宁缺毋滥）：
  P0 = 可能危及人身安全 / 重大技术变革 / 可能影响人类历史的信号 /
       市场剧烈变动信号 / 伟大革命性产品发布
  P1 = 高度相关、对读者有实质价值但未达 P0 的重大程度
  P2 = 常规内容，值得知道但谈不上重大
  P3 = 背景性内容

低价值内容一律 discard：明星八卦、小道消息/未经证实传闻、星座运势、
心灵鸡汤、无认知增量的内容农场。不要因为标题出现个别词就误杀正文
其实是正经报道的条目；以整体内容判断。

输出格式（每条）：
{{id}}
verdict: keep/discard
priority: P0/P1/P2/P3（仅 keep 需要）
reason: 原因

---
{items}
---
输出："""


def run_llm_filter_single(batch: list[Item]) -> list[Item]:
    """Run LLM filter on a batch. Returns updated items."""
    items_text = "\n---\n".join(
        FILTER_ITEM_TEMPLATE.format(
            title=item.title[:150],
            summary=item.summary[:200],
            source=item.source,
            source_type=item.source_type,
            tags=", ".join(item.tags) if item.tags else "无",
        )
        + f"\nID: {item.id}"
        for item in batch
    )
    prompt = FILTER_BATCH_TEMPLATE.format(count=len(batch), items=items_text)
    response = call_llm(prompt)

    if not response:
        for item in batch:
            verdict, reason = rule_score(item)
            item.verdict = verdict
            item.verdict_reason = reason + "（LLM不可用）"
        return batch

    # Parse response
    current_id = None
    for line in response.splitlines():
        line = line.strip()
        if not line:
            continue
        # ID lines: alphanumeric + dashes, no colon
        if (
            line
            and line[0].isalnum()
            and ":" not in line[:12]
            and not line.lower().startswith("verdict")
            and not line.lower().startswith("reason")
        ):
            current_id = line.strip()
            continue
        if current_id:
            matched = [it for it in batch if it.id == current_id]
            if not matched:
                matched = [it for it in batch if it.id.startswith(current_id[:12])]
            if not matched:
                current_id = None
                continue
            item = matched[0]
            if line.startswith("verdict:"):
                v = line.split(":", 1)[1].strip().lower()
                item.verdict = "keep" if "keep" in v and "discard" not in v else "discard"
            elif line.startswith("priority:"):
                p = line.split(":", 1)[1].strip().upper()
                # Accept "P0"…"P3"; strip any trailing words a model may add.
                pm = __import__("re").search(r"\bP[0-3]\b", p)
                if pm and item.verdict in ("keep", "keep_for_reader", "dispute"):
                    item.priority = pm.group(0)
            elif line.startswith("reason:") and not item.verdict_reason:
                item.verdict_reason = line.split(":", 1)[1].strip()[:100]
                current_id = None
    return batch


# ─── Persistence ─────────────────────────────────────────────────────────────

_save_lock = Lock()


def save_items_atomic(items: list[Item], label: str = ""):
    """Atomically save items to disk (thread-safe)."""
    items_file = SKILL_DIR / "data" / "items.jsonl"
    with _save_lock, open(items_file, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(asdict(item), ensure_ascii=False) + "\n")
    if label:
        keep = sum(1 for it in items if it.verdict in ("keep", "keep_for_reader", "dispute"))
        print(f"[Evaluator] [{label}] {len(items)} saved ({keep} curated)")


# ─── Main Pipeline ────────────────────────────────────────────────────────────


def load_items() -> list[Item]:
    items_file = SKILL_DIR / "data" / "items.jsonl"
    if not items_file.exists():
        return []
    items = []
    with open(items_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                if "raw_text" not in d:
                    d["raw_text"] = ""
                items.append(Item(**d))
            except Exception as e:
                print(f"[Evaluator] Skip bad line: {e}", file=sys.stderr)
    return items


def assign_semantic_priorities(items: list[Item]) -> list[Item]:
    """Batch-assign P0–P3 semantic priority to the final selection.

    Runs AFTER final_llm_selection so it covers exactly the items that will be
    rendered — one LLM call for the whole batch, not one per item. The five P0
    criteria are semantic (safety / historic / market-moving / revolutionary), so
    keyword matching in report.py cannot do this reliably.
    """
    if not items:
        return items

    url, key, model = _find_llm()
    if not url:
        print("[Priority] No LLM — falling back to rule defaults")
        for it in items:
            if not it.priority:
                it.priority = _rule_priority_fallback(it)
        return items

    # Rule-level fast path first: clear breaking news from a news outlet is P0
    # regardless of what the LLM says; saves prompt tokens for obvious cases.
    for it in items:
        if not it.priority:
            it.priority = _rule_priority_fallback(it, fast_only=True)

    items_text = "\n".join(
        f"{i + 1}|{it.title[:80].replace(chr(10), ' ')}|{it.summary[:60].replace(chr(10), ' ')}"
        for i, it in enumerate(items)
    )
    prompt = (
        "为下列 20 条新闻各指定优先级。这是机械标注任务：\n"
        "P0 = 危及人身安全 / 重大技术变革 / 影响人类历史 / 市场剧烈变动 / 革命性产品（通常 0-2 条）\n"
        "P1 = 高价值但未达 P0\n"
        "P2 = 常规\n"
        "P3 = 背景或低价值\n"
        "严格输出 20 行，每行格式：<数字> <P0|P1|P2|P3>\n"
        "不要输出任何解释、标题、标点、空行之外的文字。\n\n"
        f"{items_text}"
    )
    try:
        # 判断 20 条需要更多 token（600 会截断），且更低温度让它更机械。
        response = call_llm(prompt, max_tokens=1200, temperature=0.1)
    except Exception as e:
        print(f"[Priority] LLM call failed: {e}")
        response = ""

    assigned = 0
    if response:
        # SenseNova 面对真实长输入常无视格式、以叙述作答（"Item 14: ... P1."）。
        # 两段式解析：先找行首锚定的严格行，再退回全文中的 "数字 P级" 对。
        # 后者容忍叙述式输出（"1. Access OpenAI... P1" / "Item 14 ... P1"）。
        tail = response[-min(len(response), 2500):]
        strict = __import__("re").compile(
            r"(?m)^\s*(\d{1,2})\s*[.::：|｜、)）]?\s*(P[0-3])\b"
        )
        loose = __import__("re").compile(
            r"(?:item\s*)?(\d{1,2})\s*[.::：|｜、)）]?\s*(?:is\s+)?(P[0-3])\b"
        )

        for m in strict.finditer(tail):
            idx = int(m.group(1)) - 1
            if 0 <= idx < len(items):
                items[idx].priority = m.group(2).upper()
                assigned += 1

        if assigned < len(items):
            for m in loose.finditer(tail):
                idx = int(m.group(1)) - 1
                if 0 <= idx < len(items) and not items[idx].priority:
                    items[idx].priority = m.group(2).upper()
                    assigned += 1
    print(f"[Priority] assigned {assigned}/{len(items)} via LLM"
          + (f" (raw reply tail: {response[-200:]!r})" if not assigned else ""))

    # Fill anything the LLM skipped with the rule default.
    for it in items:
        if not it.priority:
            it.priority = _rule_priority_fallback(it)
    return items


# News outlets that are allowed to claim P0 on a strong keyword alone. A blog
# ("The Official Microsoft Blog") or a stock forum must never hit P0 on a bare
# word like "critical".
_NEWS_SOURCE_RE = __import__("re").compile(
    r"(雷峰|IT之家|爱范儿|少数派|虎嗅|36氪|36kr|cnBeta|新浪|搜狐|网易|腾讯|"
    r"央视|新华|人民日报|澎湃|财新|界面|钛媒体|品玩|极客公园|果壳|"
    r"Reuters|AP\b|Bloomberg|CNBC|TechCrunch|The\s*Verge|WIRED|Ars|Engadget|"
    r"纽约时报|华尔街日报|FT\b|BBC)",
    __import__("re").IGNORECASE,
)

# Strong breaking signals: these alone justify P0 from a news outlet.
_P0_STRONG_KW = ("突发", "紧急通知", "breaking", "BREAKING", "urgent alert")

# Weak signals: need to co-occur with a news outlet to reach P0.
_P0_WEAK_KW = (
    "重大",
    "历史性",
    "里程碑",
    "革命性",
    "颠覆",
    "首次",
    "史无前例",
    "critical",
    "emergency",
    "historic",
    "milestone",
    "revolutionary",
)


def _rule_priority_fallback(item: Item, fast_only: bool = False) -> str:
    """Rule-based priority fallback used when no LLM is available.

    fast_only=True applies only the unambiguous fast path (breaking + news outlet)
    and leaves everything else empty so the LLM pass can fill it in.
    """
    t = (item.title or "") + " " + (item.summary or "")
    is_news = bool(_NEWS_SOURCE_RE.search(item.source or ""))
    has_strong = any(kw.lower() in t.lower() for kw in _P0_STRONG_KW)
    has_weak = any(kw.lower() in t.lower() for kw in _P0_WEAK_KW)

    if has_strong and is_news:
        return "P0"
    if fast_only:
        return ""
    if has_weak and is_news:
        return "P1"
    return "P2"


def final_llm_selection(items: list[Item], target: int = 20) -> list[Item]:
    """
    Final LLM semantic selection: pick exactly `target` items most relevant
    to user interests. Uses verbose-tolerant parser for models that
    produce thinking text (MiniMax, etc.).
    """
    if len(items) <= target:
        print(f"[Selection] {len(items)} <= {target}, keeping all")
        return items

    url, key, model = _find_llm()
    if not url:
        print(f"[Selection] No LLM — keeping all {len(items)} items (fallback)")
        return items

    # Compact: index | source | tags | title (85 char limit, no URLs)
    items_text = ""
    for i, item in enumerate(items):
        tags = ",".join(item.tags) if item.tags else "-"
        title = item.title[:85].replace("\n", " ")
        source = item.source or "-"
        items_text += f"{i + 1}|{source}|[{tags}]|{title}\n"

    user_prompt = f"""From the {len(items)} items below, select exactly {target} for a news briefing for a user interested in: AI tools/models, design software (C4D/Unity/Blender), investment/finance (gold/stocks/funds), productivity tools, digital sovereignty, big tech companies, retro-futurism/scifi art.

EXCLUDE all of the following even if they match an interest:
- Stock-forum chatter / 个股吹票 (雪球 stock tips, "会不会是价值投资的又一经典之作", personal portfolio opinions)
- Celebrity gossip / 明星八卦 / 小道消息
- Tutorial marketing / 教程营销 or content-农场 filler with no information gain
- Personal essays without analytical value ("我每天陪老板搓AI玩具" style storytelling)
If fewer than {target} items genuinely qualify, select fewer — do NOT pad with excluded types.

For each selected item, write its NUMBER. List ALL selected numbers, one per line.

Items:
{items_text}"""

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": user_prompt}],
        "temperature": 0.1,
        "max_tokens": 800,
    }

    def _call_llm(p: dict) -> str:
        raw = _http_post(url, p, key, timeout=90)
        msg = json.loads(raw)["choices"][0]["message"]
        return str(msg.get("content", msg.get("reasoning", "")))

    def _parse_minimax(content: str, item_count: int) -> set:
        """Parse verbose MiniMax output that includes thinking + natural language selections."""
        found = set()
        cleaned = re.sub(r"<[^>]+>\s*", " ", content)

        # Strategy A: Look for the final selection list near the end (most reliable)
        # Split into sections at \n\n or natural breaks
        lines = cleaned.splitlines()

        # Find section that contains "here" / "are" / "selected" / "my picks" / numbers
        for _i, line in enumerate(lines):
            line = line.strip()
            # Lines that start with numbers (possibly with trailing colon/paren)
            clean_line = re.sub(r"[*`#_~\[\]()>]", "", line).strip()
            if clean_line.isdigit():
                v = int(clean_line)
                if 1 <= v <= item_count:
                    found.add(v - 1)
                    continue

        # Strategy B: Find lines that look like "number. Title" or "number: Title"
        for line in lines:
            line = line.strip()
            if not line:
                continue
            clean_line = re.sub(r"[*`#_~\[\]()>]", "", line).strip()
            # Match "Item 3:", "条目 4:", "#5", "3. ", "- 3 -"
            m = re.search(r"(?:^|[\s,;:()\[\]])([1-9]\d{0,2})(?:[\.:]|\s*[-]|\s)", clean_line)
            if m:
                v = int(m.group(1))
                if 1 <= v <= item_count:
                    found.add(v - 1)

        # Strategy C: Extract all numbers from the LAST 15 lines (model tends to summarize at the end)
        if len(found) < target // 2:
            last_lines = lines[-15:]
            for line in last_lines:
                clean_l = re.sub(r"[*`#_~\[\]()>,.]", "", line).strip()
                nums = re.findall(r"(?<![\d])([1-9]\d{0,2})(?![\d])", clean_l)
                for n in nums:
                    v = int(n)
                    if 1 <= v <= item_count:
                        found.add(v - 1)

        return found

    def _parse_compact(content: str, item_count: int) -> set:
        """Parse compact number-only output."""
        found = set()
        cleaned = re.sub(r"<[^>]+>\s*", " ", content)
        for line in cleaned.splitlines():
            line = line.strip()
            if not line:
                continue
            clean = re.sub(r"[*`#_~\[\]()>,.]", "", line).strip()
            if clean.isdigit() and 1 <= int(clean) <= item_count:
                found.add(int(clean) - 1)
                continue
            nums = re.findall(r"(?<![\d])([1-9]\d{0,2})(?![\d])", clean)
            for n in nums:
                v = int(n)
                if 1 <= v <= item_count:
                    found.add(v - 1)
        return found

    try:
        content = _call_llm(payload)
    except Exception as e:
        print(f"[Selection] LLM call failed: {e}")
        return items[:target]

    # Try compact parser first, then verbose parser
    selected_ids = _parse_compact(content, len(items))
    if len(selected_ids) < target // 2:
        print(
            f"[Selection] Compact parser got {len(selected_ids)}/{target}, trying verbose parser..."
        )
        selected_ids = _parse_minimax(content, len(items))

    if len(selected_ids) < target // 2:
        print(f"[Selection] Got {len(selected_ids)}/{target}, retrying with strict prompt...")
        retry_payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": f"Output {target} numbers. One per line. ONLY numbers. Like: 3\n7\n12\n...\n\nItems:\n{items_text}",
                }
            ],
            "temperature": 0.01,
            "max_tokens": 200,
        }
        try:
            content2 = _call_llm(retry_payload)
            selected_ids |= _parse_compact(content2, len(items))
            if len(selected_ids) < target // 2:
                selected_ids |= _parse_minimax(content2, len(items))
        except Exception as e2:
            print(f"[Selection] Retry failed: {e2}")

    count = len(selected_ids)
    if count == 0:
        print(f"[Selection] LLM returned no valid indices, fallback to first {target}")
        return items[:target]

    selected = [items[i] for i in sorted(selected_ids) if i < len(items)][:target]
    print(
        f"[Selection] LLM selected {len(selected)}/{target} items from {len(items)} (parsed {count} total indices)"
    )
    return selected


def evaluate_items(skip_llm: bool = False, target_selection: int = 20) -> list[Item]:
    """
    Pipeline:
    1. Load items
    2. Time filter
    3. Rule pass (instant, primary)
    4. LLM filter for disputed items (parallel, optional)
    5. Save
    """
    _find_llm()  # prime
    items = load_items()
    if not items:
        print("[Evaluator] No items to evaluate")
        return []

    print(f"[Evaluator] {len(items)} items loaded")

    # Time filter
    now = datetime.now()
    current_ym = now.strftime("%Y-%m")
    before = len(items)
    items = [it for it in items if _is_recent_enough(it, current_ym)]
    print(f"[Evaluator] Time filter: removed {before - len(items)} old ({len(items)} remain)")

    if not items:
        return []

    # Rule pass (PRIMARY — instant, no API)
    print("[Evaluator] Rule pass running (primary)...")
    rule_counts = {"keep": 0, "dispute": 0, "discard": 0}
    for item in items:
        item.verdict = "pending"
        item.verdict_reason = ""
        verdict, reason = rule_score(item)
        item.verdict = verdict
        item.verdict_reason = reason
        rule_counts[verdict] = rule_counts.get(verdict, 0) + 1
    print(
        f"[Evaluator] Rule: {rule_counts['keep']} keep / {rule_counts['dispute']} dispute / {rule_counts['discard']} discard"
    )
    save_items_atomic(items, "after-rule")

    # LLM filter (SECONDARY)
    if skip_llm:
        print("[Evaluator] --skip-llm: LLM phase skipped, using rule verdicts")
    else:
        url, _, _ = _find_llm()
        if not url:
            print("[Evaluator] No LLM — using rule verdicts")
        else:
            disputed = [it for it in items if it.verdict == "dispute"]
            if not disputed:
                print("[Evaluator] No disputed items — LLM not needed")
            else:
                num_batches = (len(disputed) + BATCH_SIZE - 1) // BATCH_SIZE
                print(
                    f"[Evaluator] LLM filtering {len(disputed)} disputed items "
                    f"({num_batches} batches × {MAX_WORKERS} workers)..."
                )
                batches = []
                remaining = disputed[:]
                while remaining:
                    batches.append(remaining[:BATCH_SIZE])
                    remaining = remaining[BATCH_SIZE:]

                completed = 0
                with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                    futures = {
                        executor.submit(run_llm_filter_single, batch): batch for batch in batches
                    }
                    for future in as_completed(futures):
                        batch = futures[future]
                        try:
                            updated = future.result(timeout=LLM_TIMEOUT * (MAX_RETRIES + 3))
                            for item in updated:
                                for t in items:
                                    if t.id == item.id:
                                        t.verdict = item.verdict
                                        t.verdict_reason = item.verdict_reason
                                        break
                        except Exception as e:
                            print(f"[Evaluator] Batch failed, rule fallback: {e}")
                            for item in batch:
                                verdict, reason = rule_score(item)
                                item.verdict = verdict
                                item.verdict_reason = reason + "（批次失败）"
                        completed += 1
                        keep_now = sum(1 for it in items if it.verdict == "keep")
                        print(f"[Evaluator] Batch {completed}/{num_batches} ({keep_now} keep)")
                save_items_atomic(items, "after-llm")

    # Final LLM semantic selection (pick top 20 by semantic understanding)
    final = [it for it in items if it.verdict in ("keep", "keep_for_reader", "dispute")]
    print(f"[Evaluator] {len(final)} items passed rule/LLM, filtering to {target_selection}...")
    if len(final) > target_selection:
        final = final_llm_selection(final, target=target_selection)

    # Semantic priority (P0–P3) for exactly the rendered set — one LLM batch.
    final = assign_semantic_priorities(final)

    # Save final selection back to items.jsonl (overwrite with only selected items)
    items_file = Path(__file__).parent.parent / "data" / "items.jsonl"
    with open(items_file, "w", encoding="utf-8") as f:
        for item in final:
            # Convert dataclass/object to dict safely
            if hasattr(item, "__dict__"):
                d = item.__dict__
            elif isinstance(item, dict):
                d = item
            else:
                continue
            f.write(json.dumps(d, ensure_ascii=False, default=str) + "\n")
    print(f"[Evaluator] Saved {len(final)} items to items.jsonl")

    print(f"[Evaluator] Done — {len(final)} final items selected")
    return final


def _is_recent_enough(item: Item, current_year_month: str) -> bool:
    if not item.date or item.date in ("", "unknown"):
        return True
    m = re.search(r"(\d{4}-\d{2})(?:-\d{2})?", item.date)
    if not m:
        return True
    return m.group(1) == current_year_month


if __name__ == "__main__":
    from env_loader import load_env

    load_env()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--skip-llm", action="store_true", help="Skip LLM phase, use rule verdicts only (fastest)"
    )
    args = parser.parse_args()
    results = evaluate_items(skip_llm=args.skip_llm)
    print(f"\nFinal {len(results)} items selected.")
