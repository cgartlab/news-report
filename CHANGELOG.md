# Changelog

All notable changes to **news-report** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

---

## [0.7.1] - 2026-10-08

### Changed

- **模块 02 迁移：`zhihu-cli` → `zhihu-search`**：PyPI 上 `zhihu-cli` 停在 v1.2.0（2020），锁死 `lxml==4.3.4`，Python 3.10+ 编译失败已无法安装。本项目改用 [zhihu-search](https://github.com/klarkxy/zhihu-search) v2.x（2026 维护中，知乎开放平台官方平替），支持站内搜索 / 全网搜索 / AI 直答 / 热榜 / 问题推荐 / 回答摘要 / 知识库 / PDF / PPT / OAuth，并提供 MCP stdio 形态。
  - `src/collect_zhihu.py` 已重写：调用 `zhihu-search search --scope zhihu|web`、`zhihu-search trending`、`zhihu-search --check-token`；解析新版 JSON 结构（`{"success", "kind", "data": {"Items": [...]}}`）
  - 新增环境变量 `ZHIHU_SEARCH_CLI_PATH`（canonical）；保留 `ZHIHU_CLI_PATH` 作为兼容别名
  - `.env.example` 同步更新 Zhihu 章节
  - 安装方式：`uv tool install zhihu-search`（旧 `scripts/setup.sh` 已不适用）

- **采集源按开关运行**：`config/config.json` 新增 `enabled_sources` 和 `disabled_reasons` 字段，`src/main.py` 的 `step_collect` 会按开关跳过未启用的源，并在日志中打印跳过原因。默认只启用 `rss` + `zhihu`，其余源（`search` / `telegram` / `twitter` / `bilibili` / `xhs`）默认禁用——要么凭证缺失，要么依赖未就绪。老板按需打开：填入 `.env` 里的凭证或修好对应 CLI，把 `enabled_sources.X = true` 即可。
- **SKILL.md 模块状态列更新**：模块 03 / 04 / 05 状态从"✅ 可用（需鉴权）"改为"⏸️ 默认禁用"，附带默认关闭原因；模块 06 / 07 仍为占位。

### Fixed

- 修复 `src/collect_zhihu.py` 在 Python 3.10+ 环境下无法调用的问题（旧版依赖 `zhihu-cli auth set` 与 `zhihu-cli status`，两者在新版 CLI 中已不存在）
- 修复 JSON 输出解析：`zhihu-search` 部分子命令会在 stdout 尾部追加 `===` 分隔符，新版解析器带容错 fallback
- 修复 pipeline 崩溃：`collect_bilibili.py` 在响应结构上假设 dict 但实际返回 list 导致 `AttributeError`——现在通过禁用 bilibili 源避免，`enabled_sources.bilibili = true` 前需先修脚本

---

## [0.7.0] - 2026-10-07

### Added

- **元数据字段体系（5 字段强制标注）**：每一条进入简报的新闻必须带以下字段，用于让读者快速判断价值与真伪。参考 [news-pipeline-n8n](https://github.com/jeremylongshore/news-pipeline-n8n) 的 Significance + Status + Key Entities 与 [news-aggregator](https://github.com/tony-stark-eth/news-aggregator) 的 Data Quality + Sentiment。
  - **Significance 1-5**：1=边缘信息 / 2=常规 / 3=值得关注的次要 / 4=重要产品或公司动作 / 5=颠覆性行业变革
  - **Development Status 10 种**：🚀 已发布 · 📢 预告 · 🔧 进行中 · ✅ 已完成 · 📋 讨论中 · ⚠️ 事故/危机 · 📉 裁员/衰退 · 🤝 合作/收购 · 📈 融资/估值 · 🏛️ 政策/监管
  - **Key Entities 1-3 个**：公司/产品/人物三类，格式 `[Apple] [iPhone Duo]`
  - **Sentiment 4 值**：`[+]` 正面 · `[~]` 中性 · `[-]` 负面 · `[?]` 未知（宁标 [?] 也不瞎猜）
  - **Data Quality 1-10**：按信源权威度 + 内容完整度打分，官方 9-10 / 二线媒体 7-8 / 社区 5-6 / 聚合 3-4 / 内容农场 1-2
  - **硬门槛**：Significance < 3 或 Data Quality < 4 一律剔除（除 🔴 独家信源）

- **打分细则章节**：Significance 5 档判定条件、Data Quality 按信源类型默认分表、Key Entities 提取优先级，让 Agent 生成简报时可直接对照，避免主观判断漂移。

- **状态存储与冷却机制（跨简报去重）**：解决同一事件被多个信源报道导致早报刷屏的问题。参考 news-aggregator 的 alert cooldown 与 news-pipeline-n8n 的事件签名。
  - `state/pushed_events.json`：按日期分片的事件签名存储
  - `scripts/cooldown_check.py`：CLI 工具，4 个子命令（check / push / list / prune）
  - **冷却规则**：同一 `key_entity + event_type` 24 小时内已推则跳过；24 小时后允许，但需有实质新进展；超过 7 天的日期自动清理
  - **Agent 集成流程**：生成前读签名 → 筛选中比对 → 生成后 push 记录 → 失败兜底跳过冷却检查但记录 warning

- **输出模板双路径说明**：v0.7.0 补充说明文档中的两个模板路径分工——
  - **代码路径**：`src/report.py` 消费本 SKILL.md 的【输出模板】章节（TOP SIGNAL + 优先级分区 + 影响分析 + 职业风险矩阵），生成深度分析报告
  - **对话直跑路径**：老板要求生成日报/早报时，Agent 使用运行时 skill `~/.hermes/skills/news-report/SKILL.md` 的【输出模板】（Telegram 友好的日常简报模板），每条新闻带 5 元数据字段并在结尾调用冷却脚本记录签名

- **仓库新增目录**：
  - `scripts/cooldown_check.py`：冷却机制 CLI（与 `~/.hermes/skills/news-report/scripts/` 同源）
  - `state/.gitkeep`：状态目录占位，`pushed_events.json` 运行时生成

### Fixed

- 修复 v0.3.0 之后输出模板章节与运行时 Agent 简报模板的语义混淆：两者现在明确分工（长版深度分析 vs 日常简报），Agent 不会误用 TOP SIGNAL 长模板作为 Telegram 早报模板。

### Breaking

- 无。所有新增内容为纯增量。

---

## [0.6.1] - 2026-09-18

### Added

- **SKILL.md Contract 表**：新增输入/输出/失败行为/副作用/完成标准 5 项契约定义，集中声明 skill 的调用约定与完成判定条件。
- **只读边界表述修正**：概述「不写任何内容」改为「不写业务输出文件（内部脚本会写本地中间数据文件，如 JSON 采集结果）」，与 Contract 表及通用约定第 3 条一致。

### Fixed

- **zhihu-cli 模块路径引用**：line 354/416/417 三处 `scripts/setup.sh` 等裸路径改为 `<skill-dir>/scripts/...` 占位形式，与 line 361/364 一致。修复前用户按文档字面执行会因路径不存在而失败。

---

## [0.6.0] - 2026-09-18

### Added

- **模块 05 · `xiaohongshu-cli`（小红书 CLI）**：新增小红书信息源模块，通过 [jackwener/xiaohongshu-cli](https://github.com/jackwener/xiaohongshu-cli) 接入笔记搜索、热门榜、推荐 Feed、用户资料与话题。Apache 2.0 开源。
  - `src/collect_xhs.py`：小红书 CLI 采集脚本，支持笔记搜索（`search`）、热门榜（`hot`，支持多分类：food/fashion/cosmetics/movie/career/love/home/gaming/travel/fitness）、推荐 Feed（`feed`），无鉴权时优雅跳过。
  - CLI 路径自动检测：`XHS_CLI_PATH` → `config.json` → 已知路径 → PATH 搜索。
  - 集成到 `main.py` 的 `step_collect()`，作为第 7 个采集源。
- **SKILL.md 模块 05 章节**：完整记录小红书 CLI 的前置条件、安装、鉴权、可用能力、使用方式与排障指南。
- **信息源注册表更新**：模块 05 = `xiaohongshu-cli`（✅ 可用），原 rss-http/news-api 顺延为模块 06/07。
- **config.json 新增字段**：`xhs_cli_path`、`xhs_include_hot`、`xhs_hot_categories`。
- **.env.example 新增字段**：`XHS_CLI_PATH`。

### Changed

- **模块编号调整**：rss-http 从 05 → 06，news-api 从 06 → 07。
- **SKILL.md 扩展模块示例**：rss-http 示例标记为模块 06。

---

## [0.5.0] - 2026-09-18

### Added

- **模块 03 · `twitter-cli`（Twitter/X CLI）**：新增 Twitter/X 信息源模块，通过 [jackwener/twitter-cli](https://github.com/jackwener/twitter-cli) 接入推文搜索、时间线、书签与用户资料。Apache 2.0 开源。
  - `src/collect_twitter.py`：Twitter CLI 采集脚本，支持推文搜索（`search`）、时间线采集（`feed`），无鉴权时优雅跳过。
  - CLI 路径自动检测：`TWITTER_CLI_PATH` → `config.json` → 已知路径 → PATH 搜索。
  - 集成到 `main.py` 的 `step_collect()`，作为第 5 个采集源。
- **模块 04 · `bilibili-cli`（Bilibili CLI）**：新增 B 站信息源模块，通过 [jackwener/bilibili-cli](https://github.com/jackwener/bilibili-cli) 接入视频搜索、热门榜、排行榜与用户资料。Apache 2.0 开源。
  - `src/collect_bilibili.py`：Bilibili CLI 采集脚本，支持视频搜索（`search`）、热门榜（`hot`）、排行榜（`rank`），部分命令无需鉴权。
  - CLI 路径自动检测：`BILIBILI_CLI_PATH` → `config.json` → 已知路径 → PATH 搜索。
  - 集成到 `main.py` 的 `step_collect()`，作为第 6 个采集源。
- **SKILL.md 模块 03/04 章节**：完整记录 Twitter CLI 和 Bilibili CLI 的前置条件、安装、鉴权、可用能力、使用方式与排障指南。
- **信息源注册表更新**：模块 03 = `twitter-cli`（✅），模块 04 = `bilibili-cli`（✅），原 rss-http/news-api 顺延为模块 05/06。
- **config.json 新增字段**：`twitter_cli_path`、`twitter_include_feed`、`bilibili_cli_path`、`bilibili_include_hot`。
- **.env.example 新增字段**：`TWITTER_CLI_PATH`、`TWITTER_AUTH_TOKEN`、`TWITTER_CT0`、`BILIBILI_CLI_PATH`。

### Changed

- **模块编号调整**：rss-http 从 03 → 05，news-api 从 04 → 06。
- **SKILL.md 扩展模块示例**：rss-http 示例标记为模块 05。

---

## [0.4.0] - 2026-09-18

### Added

- **模块 02 · `zhihu-cli`（知乎开放平台 CLI）**：新增知乎信息源模块，通过知乎官方 CLI 接入社区搜索、全网搜索、热榜、AI 直答、问题推荐与回答摘要。
  - `src/collect_zhihu.py`：Zhihu CLI 采集脚本，支持知乎社区搜索（`search zhihu`）、全网搜索（`search global`）、热榜采集（`hot`），无鉴权时优雅跳过。
  - CLI 路径自动检测：`ZHIHU_CLI_PATH` 环境变量 → `config.json` → 已知路径 → PATH 搜索。
  - 集成到 `main.py` 的 `step_collect()`，作为第 4 个采集源（RSS + Search + Telegram + Zhihu）。
- **SKILL.md 模块 02 章节**：完整记录知乎 CLI 的前置条件、安装初始化、环境变量、可用能力、使用方式与排障指南。
- **信息源注册表更新**：模块 02 = `zhihu-cli`（✅ 可用），原 rss-http/news-api 顺延为模块 03/04。
- **config.json 新增字段**：`zhihu_cli_path`、`zhihu_include_hot`。
- **.env.example 新增字段**：`ZHIHU_CLI_PATH`、`ZHIHU_ACCESS_SECRET`。

### Changed

- **模块编号调整**：rss-http 从 02 → 03，news-api 从 03 → 04。
- **SKILL.md 扩展模块示例**：模块 02 占位替换为正式 zhihu-cli 章节，rss-http 示例标记为模块 03。

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
