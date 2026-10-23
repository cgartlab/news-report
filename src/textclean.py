#!/usr/bin/env python3
"""中文排版清洗 —— 共享给采集层与渲染层。

Feed 内容经过 HTML 去标签后常在句中留下多余空格：`<span>` 包住的短语被替换成
空格，于是 "华为 鸿蒙 HarmonyOS 操作系统装机量突破 9,500 万台 ，" 这种句子直接
印进简报。人眼一眼就能看出这不是人写的，但规则层不做处理就不会消失。

本模块只做「中文排版」层面的收敛，不改动词句，也不碰英文内部的空格：

  - 中文字符之间的空白删除（"华为 鸿蒙" → "华为鸿蒙"）
  - 中文 / 全角标点前、后的空白删除（"万台 ，" → "万台，"、"。 一边是" → "。一边是"）
  - 零宽字符（U+200B~200D、U+FEFF）删除，NBSP / 全角空格归一
  - 连续空白折叠为单个空格

有意保留：中文与数字 / 英文之间的空格（"9,500 万台"、"Mac 版 Perplexity"），
这符合中文排版惯例，不是脏数据。
"""

import re

# 中日韩统一表意文字 + 扩展 A + 兼容区
_CJK = r"\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff"

# 全角标点：闭合型（其后的空格是 HTML 残留）+ 分隔型
_FULL_PUNCT = "，。！？；：、）》」』】〕”’…—～"
_OPEN_PUNCT = "（《「『【〔‘“"

_CJK_GAP_RE = re.compile(rf"(?<=[{_CJK}])[ \t]+(?=[{_CJK}])")
_BEFORE_PUNCT_RE = re.compile(rf"[ \t]+(?=[{_FULL_PUNCT}])")
_AFTER_PUNCT_RE = re.compile(rf"(?<=[{_FULL_PUNCT}])[ \t]+")
_AFTER_OPEN_RE = re.compile(rf"(?<=[{_OPEN_PUNCT}])[ \t]+")
_ZERO_WIDTH_RE = re.compile(r"[\u200b-\u200d\u2060\ufeff]")
_SPACE_RUN_RE = re.compile(r"[ \t]{2,}")

# Markdown residue from feed bodies: `*Psychological Medicine*` arrives as
# literal asterisks. Our template owns the formatting, and a summary truncated
# mid-emphasis leaves a dangling `*` that breaks downstream Markdown renderers.
_MD_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_MD_ITALIC_RE = re.compile(r"(?<![*\w])\*([^*\n]{1,120})\*(?![*\w])")
_STRAY_STAR_RE = re.compile(r"\*+")


def strip_markdown_noise(text: str) -> str:
    """Drop Markdown emphasis markers that leaked out of feed bodies."""
    if not text:
        return ""
    t = _MD_BOLD_RE.sub(r"\1", text)
    t = _MD_ITALIC_RE.sub(r"\1", t)
    t = _STRAY_STAR_RE.sub("", t)
    return t


def normalize_cjk_spacing(text: str) -> str:
    """收敛中文排版：删掉句中/标点旁的多余空格。幂等，对纯英文文本无副作用。"""
    if not text:
        return ""
    t = _ZERO_WIDTH_RE.sub("", text)
    # NBSP / 全角空格先变成普通空格，交给下面统一的规则处理。
    t = t.replace("\u00a0", " ").replace("\u3000", " ")
    t = _CJK_GAP_RE.sub("", t)
    t = _BEFORE_PUNCT_RE.sub("", t)
    t = _AFTER_PUNCT_RE.sub("", t)
    t = _AFTER_OPEN_RE.sub("", t)
    t = _SPACE_RUN_RE.sub(" ", t)
    return t.strip()
