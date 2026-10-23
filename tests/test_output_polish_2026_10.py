#!/usr/bin/env python3
"""输出质量测试（2026-10-23 打磨批次）。

覆盖四类真实缺陷，全部取自 2026-10-21 那次 run 的实际输出：

1. 中文排版脏：`华为 鸿蒙`、`万台 ，`、`。 一边是` —— HTML 内联标签被替换成空格
2. 前置样板：`感谢IT之家网友…线索投递！`、`IT之家 10 月 20 日消息，`、`业界消息 2026/10/20 青小蛙`
3. 模板不统一：P1 缺日期、P3 裸标题无链接
4. 单源淹没：P2 里 AWS 博客 4 条 + IT之家 5 条（共 11 条）
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from collect_rss import _strip_html, _strip_noise
from evaluator import Item
from report import MAX_PER_SOURCE_P2, _meta_line, _summary_140, render_item_p3
from textclean import normalize_cjk_spacing


def make_item(title="t", summary="s", source="IT之家", source_type="rss",
              verdict="keep", priority="P2", url="https://example.com/a",
              date="2026-10-21"):
    return Item(
        id=f"t_{abs(hash((title, source, priority, url)))}",
        title=title,
        url=url,
        summary=summary,
        source=source,
        source_type=source_type,
        tags=[],
        date=date,
        verdict=verdict,
        priority=priority,
    )


# ─── 1. 中文排版 ─────────────────────────────────────────────────────────────


class TestCjkSpacing:
    def test_inline_markup_gap_removed(self):
        assert normalize_cjk_spacing("华为 鸿蒙 HarmonyOS 装机量") == "华为鸿蒙 HarmonyOS 装机量"

    def test_space_before_fullwidth_punct_removed(self):
        assert normalize_cjk_spacing("突破 9,500 万台 ，目前约") == "突破 9,500 万台，目前约"

    def test_space_after_fullwidth_punct_removed(self):
        assert normalize_cjk_spacing("一个现象。 一边是字节跳动") == "一个现象。一边是字节跳动"

    def test_english_untouched(self):
        text = "Canadian organizations building generative AI applications"
        assert normalize_cjk_spacing(text) == text

    def test_digit_cjk_space_preserved(self):
        # "9,500 万台" / "Mac 版" 是合法中文排版，不该被清掉
        assert normalize_cjk_spacing("9,500 万台，Mac 版 Perplexity") == "9,500 万台，Mac 版 Perplexity"

    def test_nbsp_and_zero_width_stripped(self):
        assert normalize_cjk_spacing("华为\u00a0鸿蒙\u200b系统") == "华为鸿蒙系统"

    def test_idempotent(self):
        once = normalize_cjk_spacing("数据显示， 华为 鸿蒙 装机量 ，目前")
        assert normalize_cjk_spacing(once) == once


class TestStripHtml:
    def test_inline_tag_leaves_no_space(self):
        assert _strip_html("<p>华为<span>鸿蒙</span>系统</p>") == "华为鸿蒙系统"

    def test_block_tag_is_a_boundary(self):
        assert _strip_html("<p>第一段</p><p>第二段</p>") == "第一段 第二段"

    def test_literal_comparison_not_eaten(self):
        assert "a" in _strip_html("a &lt; b &amp;&amp; c &gt; d")


# ─── 2. 前置样板 ─────────────────────────────────────────────────────────────


class TestLedeBoilerplate:
    def test_thanks_and_dateline_stripped(self):
        raw = "感谢IT之家网友 猫言喵语 的线索投递！ IT之家 10 月 20 日消息，华为官网迎来更新。"
        assert _strip_noise(raw) == "华为官网迎来更新。"

    def test_dateline_stripped(self):
        raw = "IT之家 10 月 20 日消息，比亚迪官方在 10 月 18 日宣布，方程豹销量达成。"
        assert _strip_noise(raw) == "比亚迪官方在 10 月 18 日宣布，方程豹销量达成。"

    def test_section_date_byline_stripped(self):
        raw = "业界消息 2026/10/20 青小蛙 10 月 19 日，腾讯正式发布 WorkBuddy 教育公益版。"
        assert _strip_noise(raw) == "10 月 19 日，腾讯正式发布 WorkBuddy 教育公益版。"

    def test_leading_full_stop_stripped(self):
        assert _strip_noise("。相关研究表明，这一习惯有助于改善心理健康。") == "相关研究表明，这一习惯有助于改善心理健康。"

    def test_body_date_not_eaten(self):
        # 正文里的日期不是 lede 样板，必须保留
        raw = "报道指出，2026/10/20 当天发布的版本存在问题。"
        assert "2026/10/20" in _strip_noise(raw)


# ─── 3. 模板统一 ─────────────────────────────────────────────────────────────


class TestUnifiedTemplate:
    def test_p1_meta_carries_date(self):
        item = make_item(priority="P1")
        assert _meta_line(item).strip() == "📡 IT之家 · 2026-10-21"

    def test_meta_omits_date_when_missing(self):
        item = make_item(priority="P1", date="")
        assert _meta_line(item).strip() == "📡 IT之家"

    def test_p3_has_link(self):
        rendered = render_item_p3(make_item(priority="P3"))
        assert rendered.startswith("[t](https://example.com/a)")

    def test_p3_without_url_is_bare(self):
        rendered = render_item_p3(make_item(priority="P3", url=""))
        assert rendered.startswith("t  📡")

    def test_summary_budget_ignores_artifacts(self):
        # 清洗前 140 字里有 5 个空格是 HTML 残留；清洗后同样的预算装下更多正文
        dirty = "华 为 鸿 蒙 系 统 装 机 量 突 破 " + "正文" * 90
        cleaned = _summary_140(make_item(summary=dirty))
        assert "华 为" not in cleaned
        assert cleaned.endswith("…")
        assert len(cleaned) <= 141


# ─── 4. 单源上限 ─────────────────────────────────────────────────────────────


class TestSourceDiversity:
    def test_cap_constant(self):
        assert MAX_PER_SOURCE_P2 == 3

    def test_cap_moves_overflow_to_p3(self):
        from report import generate_report

        items = [make_item(title=f"AWS {i}", source="AWS", priority="P2") for i in range(5)]
        report = generate_report(items)
        p2_block = report.split("🟢 常规 (P2)")[1].split("🔵 背景 (P3)")[0]
        assert p2_block.count("https://example.com/a") == MAX_PER_SOURCE_P2
        # 超出的条目进入背景区，不丢弃
        assert "🔵 背景 (P3)" in report
        assert report.count("https://example.com/a") == 5

    def test_selected_count_unchanged(self):
        from report import generate_report

        items = [make_item(title=f"X {i}", source="单一源", priority="P2") for i in range(6)]
        report = generate_report(items, collected=99, sources=7)
        assert "精选 6 条" in report
