# Changelog

All notable changes to **news-report** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

---

## [0.2.0] - 2026-09-06

### Changed

- **仓库更名与重新定位**：`miniflux-mcp-skill` → **`news-report`**。定位由「把 Miniflux 接入 AI Agent」扩展为「**模块化信息源**驱动的新闻采集 Skill」：跨多个信息源检索新闻 / 文章并整理素材，Miniflux RSS 是其中一个来源。
- `SKILL.md` 重写：frontmatter 更名为 `news-report`，description 覆盖跨模块检索与触发词（读 RSS / 查订阅 / 搜文章 / 简报素材 / "Miniflux" / "RSS" / "feeds" / "订阅"）。
- 新增「信息源模块化架构」：模块约定（module id、数据访问方式、可用检索能力、配置项、状态）+ 信息源注册表（模块 01 · miniflux 可用；`rss-http`、`news-api` 为规划中示例占位，不编造实现细节）。
- 新增「通用约定」：密钥一律本地环境变量（示例 `${VAR}` 占位）、终端示例可直接复制执行并注明平台、当前只读边界。
- 明确「输出格式：下一阶段设计」，本版聚焦信息检索与整理。
- 原 miniflux-mcp-skill 全部集成内容（前置条件、MCP 配置方案 A / B、环境变量表、可用工具、searchEntries 参数、常用工作流、排障）完整保留，归入「模块 01：Miniflux」章节。
- `README.md` 重写为 news-report 简介；新增 `AGENTS.md`（仓库级 AI 协作约束）与 `CHANGELOG.md`。
- Skill 版本号升至 v0.2.0；Skill 创建时间（2026-08-01）保留原记录。

---

## [0.1.0] - 2026-08-01

### Added

原 **miniflux-mcp-skill** 初始发布：

- `SKILL.md` — 将 Miniflux RSS 阅读器经 `miniflux-mcp` MCP 服务器接入 AI Agent：前置条件、MCP 服务器配置（方案 A：npx 直接运行；方案 B：本地安装 + Basic Auth 补丁）、`MINIFLUX_*` 环境变量表、可用工具（listCategories / listFeeds / searchFeedsByCategory / resolveId / searchEntries）、searchEntries 参数表、常用工作流、排障、维护提示。
- `README.md` — 项目简介与使用方式。
- `LICENSE` — CC BY-NC-SA 4.0。
- Git 初始提交与 `v0.1.0` tag。
