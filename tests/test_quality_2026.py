#!/usr/bin/env python3
"""Quality-gate tests for the 2026-10-21 report/eval changes:
low-value filtering, {{...}} placeholder stripping, 140-char summaries, and
priority fallback. These guard the behaviours we fixed after the first Miniflux run."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from collect_rss import _strip_noise
from evaluator import Item, _rule_priority_fallback, rule_score
from report import _summary_140, assign_priority


def make_item(title="t", summary="s", source="IT之家", source_type="rss",
              verdict="keep", priority="", url="https://example.com"):
    return Item(
        id=f"test_{abs(hash(title))}",
        title=title,
        url=url,
        summary=summary,
        source=source,
        source_type=source_type,
        tags=[],
        date="2026-10-21",
        verdict=verdict,
        priority=priority,
    )


# ─── Low-value filtering (rule layer, no LLM) ──────────────────────────────

class TestLowValueRule:
    def test_star_gossip_discarded(self):
        item = make_item(title="某明星深夜约会，粉丝热议")
        assert rule_score(item)[0] == "discard"

    def test_rumor_discarded(self):
        item = make_item(title="网传苹果将推出全新产品")
        assert rule_score(item)[0] == "discard"

    def test_astrology_discarded(self):
        item = make_item(title="今日星座运势：白羊座运势大好")
        assert rule_score(item)[0] == "discard"

    def test_real_tech_with_marriage_word_not_killed(self):
        # "结婚" is a weak marker — a tech story mentioning it must survive.
        item = make_item(title="英伟达发布新GPU，创始人称比结婚还激动",
                         summary="黄仁勋在发布会上打趣……" * 5)
        v, _ = rule_score(item)
        assert v in ("keep", "dispute")  # not auto-discard

    def test_weak_marker_demotes_but_keeps(self):
        item = make_item(title="某公司疑似推出新手机", summary="消息尚未证实……")
        v, _ = rule_score(item)
        assert v != "keep"  # demoted below keep threshold


# ─── {{...}} placeholder stripping ──────────────────────────────────────────

class TestPlaceholderStrip:
    def test_postmeta_placeholders_removed(self):
        out = _strip_noise(
            "收藏已收藏{{ postmeta.bookmark }} 点赞已赞{{ postmeta.postlike }} 正文开始",
            "标题",
        )
        assert "{{" not in out
        assert "postmeta" not in out
        assert out.startswith("正文开始") or "正文开始" in out

    def test_clean_text_untouched(self):
        out = _strip_noise("这是干净的摘要文本。", "标题")
        assert out == "这是干净的摘要文本。"


# ─── 140-char summary ───────────────────────────────────────────────────────

class TestSummary140:
    def test_short_stays(self):
        item = make_item(summary="很短的摘要")
        assert _summary_140(item) == "很短的摘要"

    def test_long_cut_with_ellipsis(self):
        item = make_item(summary="。".join("内容" * 10 for _ in range(40)))
        out = _summary_140(item)
        assert len(out) <= 145
        assert out.endswith("…")

    def test_empty_returns_empty(self):
        item = make_item(summary="")
        assert _summary_140(item) == ""


# ─── Priority fallback / assignment ─────────────────────────────────────────

class TestPriority:
    def test_stored_priority_wins(self):
        item = make_item(priority="P1", verdict="keep",
                         title="任意标题", source="IT之家")
        assert assign_priority(item) == "P1"

    def test_load_curated_items_preserves_priority(self, tmp_path):
        # Regression: load_curated_items' field whitelist dropped `priority`,
        # so every LLM-assigned priority was lost before rendering.
        import json

        import report as report_mod

        report_mod.SKILL_DIR = tmp_path
        (tmp_path / "data").mkdir()
        entry = {
            "id": "x", "title": "T", "url": "U", "summary": "S",
            "source": "央视新闻", "source_type": "rss", "tags": [], "date": "2026-10-21",
            "verdict": "keep", "priority": "P0", "raw_text": "",
        }
        (tmp_path / "data" / "items.jsonl").write_text(
            json.dumps(entry, ensure_ascii=False), encoding="utf-8"
        )
        loaded = report_mod.load_curated_items()
        assert len(loaded) == 1
        assert loaded[0].priority == "P0"

    def test_news_breaking_strong_falls_to_p0(self):
        item = make_item(title="突发！某地发生紧急事件", source="央视新闻", verdict="keep")
        assert assign_priority(item) == "P0"

    def test_blog_critical_not_p0(self):
        # The regression case: a blog with "critical" must NOT become P0.
        item = make_item(
            title="Advancing digital sovereignty with greater control and choice",
            summary="critical considerations for sovereign clouds",
            source="The Official Microsoft Blog",
            verdict="keep",
        )
        assert assign_priority(item) in ("P1", "P2")

    def test_fallback_no_llm_news_weak_p1(self):
        item = make_item(title="重大突破！国产芯片量产", source="雷峰网", verdict="keep")
        assert _rule_priority_fallback(item) == "P1"

    def test_aggregate_title_capped_at_p2(self):
        item = make_item(
            title="停止加薪！大众计划冻结薪酬；突发！美国发布禁令；马斯克：赠送股票",
            source="雷峰网", verdict="keep",
        )
        assert assign_priority(item) == "P2"
