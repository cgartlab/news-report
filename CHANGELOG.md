# Changelog

All notable changes to **news-report** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

---

## [0.3.0] - 2026-09-18

### Added

- **输出模板正式定义**（SKILL.md 新增「输出模板」章节）：完整定义新闻简报的输出格式，包含 7 个结构化章节——TOP SIGNAL（🎯 当日最重要信号）、紧急（🔴 P0）、关注（🟡 P1）、常规（🟢 P2）、背景（🔵 P3）、影响分析（📊 跨行业传导 + 职业风险矩阵）、来源统计。
- **排版设计原则**：信息密度最大化（每条一行核心 + 一行洞察 + 一行元数据）、阅读体验最优化（视觉层级 🎯→🔴→🟡→🟢→🔵，可扫描，💡 洞察高亮）、节奏从冲击到沉静的叙事弧。
- **影响分析指南**：跨行业传导路径（技术→直接→次生影响）+ 职业风险矩阵（🔴 高危/🟡 中危/🟢 安全，含时间框架）。
- **完整示例**：SKILL.md 内嵌完整示例输出，可直接参考排版。

### Changed

- **SKILL.md 输出格式声明**：从「下一阶段设计」更新为「见输出模板章节」，v0.3.0 起正式可用。
- **AGENTS.md 约束更新**：「输出格式未设计」→「输出格式已定义」，后续修改需遵循模板。

---

## [0.2.2] - 2026-09-18

### Added

- **GitHub Actions: 代码质量检查**（`.github/workflows/lint.yml`）：ruff lint + ruff format check + mypy type check（Python 3.10–3.13 matrix）+ JSON 配置验证 + .env.example 格式检查。
- **GitHub Actions: 自动化发布**（`.github/workflows/release.yml`）：tag 推送或手动触发 → 验证 CHANGELOG 版本一致性 → 检查 SKILL.md / AGENTS.md / CHANGELOG.md 版本同步 → 自动创建 GitHub Release（含 release notes）。
- **GitHub Actions: 文档检查**（`.github/workflows/docs-check.yml`）：Markdown 尾随空格检查 + 代码块标记配平检查 + 版本一致性检查。
- **pyproject.toml**：Python 项目配置（ruff lint + format + mypy + isort），统一代码风格与类型检查规则。
- **Pre-commit hooks**（`.pre-commit-config.yaml`）：ruff fix/format、尾随空格、文件末尾换行、YAML/JSON 验证、merge 冲突检测、私钥检测、禁止直推 main。
- **仓库治理文件**：`CODEOWNERS`（代码所有权）、`PULL_REQUEST_TEMPLATE.md`（PR 模板）、`ISSUE_TEMPLATE/`（bug/feature 模板）、`CONTRIBUTING.md`（贡献指南，含开发设置、分支策略、提交规范、质量门禁）。

### Changed

- **README.md 专业化重写**：新增架构图、信息源注册表、Quick Start、开发指南、分支策略、发布流程、贡献指引；添加 CI/Release badge。
- **版权信息标准化**：所有新增文件头部添加 `Copyright (c) 2026 CGArtLab. CC BY-NC-SA 4.0.`。

---

## [0.2.1] - 2026-09-11

### Fixed

- **工具签名与实际调用方式不一致**：将「可用工具」表的签名从 `listCategories(counts?)` 等改为对象参数形式 `listCategories({ counts? })`，与示例保持一致，避免误导。
- **searchEntries 参数表遗漏**：补全 `changed_before` / `changed_after`（更新时间过滤）与 `before_entry_id` / `after_entry_id`（游标分页）参数，同步上游 miniflux-mcp v0.0.12 的实际支持字段。
- **状态过滤值补充**：将 `status` 参数示例从 `"read,unread"` 扩展为 `"read,unread,removed"`，涵盖 Miniflux API 允许的全部状态。
- **审查修正**：移除编造的 2FA 排障条目，修正「默认只返回未读」的错误表述，澄清 MCP 无工具响应缓存机制，统一 opencode 与 User-Agent 的 Unicode 连字符混用，消除扩展模块示例中假设工具名被误用的风险。

### Documentation

- **新增高级指南章节**：在 SKILL.md 中新增「高级指南」，包含架构设计详解、模块开发指南、测试与验证、部署与维护、安全最佳实践、性能优化建议、故障排查进阶、扩展模块示例等专业内容。
- **完善模块化架构文档**：强化模块开发规范与最佳实践，为未来模块扩展提供清晰指引。
- **AGENTS.md 文档升级**：v1 → v3——新增「启动清单」「典型任务与操作原则」「质量门禁」章节，强化版本三处同步约束，更新文件地图与版本段。

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
