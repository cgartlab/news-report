# news-report

[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)

news-report 是一个**模块化信息源**驱动的新闻采集（news-gathering）[Agent Skill](https://agentskills.io)：在对话中直接跨各信息源检索新闻 / 文章、查看订阅、搜索文章，并整理成新闻简报等任务的素材。

**Miniflux RSS**（经 `miniflux-mcp` MCP 服务器）作为 **模块 01** 已可用（完整保留原 miniflux-mcp-skill 集成内容）；架构预留了 RSS 直取（`rss-http`）、News API（`news-api`）等扩展模块（规划中）。**输出格式：下一阶段设计**，本版聚焦信息检索与整理。

## Usage

Skill 指令位于 [SKILL.md](./SKILL.md)。在 agent 运行时中按名称 **`news-report`** 加载本 Skill（触发词与使用说明见 SKILL.md 的 frontmatter description 与正文）。

## License

CC BY-NC-SA 4.0
