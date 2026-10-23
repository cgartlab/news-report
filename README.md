# news-report

[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)
[![CI: Lint & Type Check](https://github.com/cgartlab/news-report/actions/workflows/lint.yml/badge.svg)](https://github.com/cgartlab/news-report/actions/workflows/lint.yml)
[![CI: Docs Check](https://github.com/cgartlab/news-report/actions/workflows/docs-check.yml/badge.svg)](https://github.com/cgartlab/news-report/actions/workflows/docs-check.yml)
[![Release](https://img.shields.io/github/v/tag/cgartlab/news-report)](https://github.com/cgartlab/news-report/tags)

news-report 是一个**模块化信息源**驱动的新闻采集（news-gathering）[Agent Skill](https://agentskills.io)：在对话中跨各信息源检索新闻 / 文章、查看订阅、搜索文章，并整理成新闻简报。仓库同时带一条可独立运行的 Python 流水线（采集 → 去重 → LLM 评估 → 排版输出），供脚本 / 定时批量使用。

**Miniflux RSS**（经 `miniflux-mcp` MCP 服务器）作为 **模块 01** 已可用；模块 02-06 已登记（详见 [SKILL.md](./SKILL.md) 信息源注册表）；RSS 直取（`rss-http`）、News API（`news-api`）为规划中占位（模块 07 / 08）。**输出格式：见 SKILL.md「输出模板」章节**。

## Architecture

```
news-report/
├── SKILL.md              # 技能指令本体（模块化架构、模块 01-06、打分细则、输出模板）
├── AGENTS.md             # AI 贡献者约束（定位、启动清单、质量门禁、提交规范）
├── LESSONS.md            # 从真实失误沉淀的「教训 → 规则」清单
├── CONTRIBUTING.md       # 贡献指南
├── CHANGELOG.md          # 版本历史（Keep a Changelog + SemVer）
├── README.md             # 本文件（对外简介）
├── pyproject.toml        # Python 项目配置（ruff / mypy / pytest / 入口 news-report）
├── src/                  # 采集 → 去重 → 评估 → 排版流水线
│   ├── main.py           # 流水线入口（按 config 开关跑各采集器）
│   ├── collect_*.py      # 各信息源采集器（miniflux / rss / zhihu / twitter / ...）
│   ├── deduplicator.py   # 去重（阈值 dedup_threshold）
│   ├── evaluator.py      # 规则打分 + LLM 过滤 + P0-P3 语义判定
│   ├── report.py         # 简报排版（NEWS REPORT 四优先级区 + 来源统计）
│   ├── textclean.py      # 中文排版 / 前置样板 / Markdown 残留清洗
│   └── x_cdp.py          # 零依赖 CDP 客户端（模块 06）
├── tests/                # pytest：采集清洗、评估规则、渲染、CDP
├── config/               # config.json 开关 + RSS 源 / 搜索词 / TG 频道清单
├── bin/                  # edge-cdp.ps1 / edge-cdp.sh（浏览器 CDP 启动器）
├── docs/reports/         # 质量评估报告
└── .github/
    ├── actions/publish/action.yml   # 发布到 ClawHub / SkillHub 的 composite action
    └── workflows/
        ├── lint.yml        # ruff check + ruff format + mypy（3.10-3.13）+ pytest + 配置校验
        ├── docs-check.yml   # 文档门禁：空白/制表符、代码块配平、五处版本一致
        ├── release.yml      # tag → 校验版本 → GitHub Release
        └── publish.yml      # Release 发布后 → ClawHub / SkillHub
```

## Information Source Registry

| Module | Access | Capabilities | Status |
|--------|--------|-------------|--------|
| 01 · `miniflux` | MCP server / REST | Categories, feeds, search, unread, favorites | ✅ Active |
| 02 · `zhihu-search` | CLI / MCP | Search, AI Q&A, hot list, summaries, OAuth | ✅ Active |
| 03 · `twitter-cli` | CLI binary | Tweet search, timeline, bookmarks, users | ⏸️ Disabled (auth) |
| 04 · `bilibili-cli` | CLI binary | Video search, hot/rank lists, users | ⏸️ Disabled (bug) |
| 05 · `xiaohongshu-cli` | CLI binary | Note search, hot list, feed, topics | ⏸️ Disabled (auth) |
| 06 · `x-browser` | CDP (HTTP+WS) | Deep timeline scroll, retweet attribution | ⏸️ Disabled (needs CDP browser) |
| 07 · `rss-http` | HTTP (direct RSS/Atom) | — | 📋 Planned |
| 08 · `news-api` | HTTP API | — | 📋 Planned |

## Usage

Skill 指令位于 [SKILL.md](./SKILL.md)。在 agent 运行时中按名称 **`news-report`** 加载本 Skill（触发词与使用说明见 frontmatter description 与正文）。

### 路径 A：对话侧（MCP 服务器，模块 01）

```bash
# 1. 环境变量
export MINIFLUX_BASE_URL="https://miniflux.example.com"
export MINIFLUX_API_KEY="your-api-token-here"

# 2. 在 agent 配置里注册 miniflux-mcp（示例见 SKILL.md「配置 MCP 服务器」）
# 3. 对话中加载 skill：/skill news-report
```

### 路径 B：脚本流水线（批量 / 定时）

```bash
pip install -e '.[dev]'

# 需要 .env 里的信息源凭证（见 .env.example），并按需打开 config/config.json 的 enabled_sources
python -m src.main          # 采集 → 去重 → 评估 → 输出 output/latest.md
```

> 对话侧走 MCP（一次工具调用拿结果），脚本侧走 REST（一次请求覆盖全部订阅源）——两者互补，细节见 SKILL.md「两条接入路径」。

## Development

```bash
pip install -e '.[dev]'

ruff check src/ tests/          # lint
ruff format --check src/        # 格式门禁（CI 同款）
mypy src/                       # 类型检查
pytest -q                       # 测试
```

`ruff` 未固定版本，CI 装最新版；本地格式门禁在 Windows 上会因 CRLF 检出产生假阳性——用 LF 副本验证或相信 CI。

### Branch Strategy

| Branch | Purpose | Protection |
|--------|---------|------------|
| `main` | Stable release | Protected, PR-only |
| `feat/*` | New features / modules | Free to push |
| `fix/*` | Bug fixes | Free to push |
| `docs/*` | Documentation-only | Free to push |

## Releases

版本号遵循 **Semantic Versioning**，`docs-check.yml` 要求以下**五处**一致（`release.yml` 另对其中三处做硬校验）：

1. `SKILL.md` frontmatter `version:`
2. `SKILL.md` 正文 `**Skill 版本**：vX.Y.Z`
3. `pyproject.toml` `version = "X.Y.Z"`
4. `CHANGELOG.md` 最新的 `## [X.Y.Z]`
5. `AGENTS.md` `**项目版本**：vX.Y.Z`

发布流程：

```bash
git tag v0.9.1 && git push origin v0.9.1   # → release.yml 校验后建 Release
```

## Publishing (ClawHub / SkillHub)

发布逻辑内联在 [`.github/actions/publish/action.yml`](./.github/actions/publish/action.yml)，`.github/workflows/publish.yml` 只做参数绑定——**不依赖跨仓库 reusable workflow**（跨仓库 reusable workflow 只在双方同为 private 时可用，本仓库是 public）。

| 项 | 值 |
|---|---|
| slug | `cgartlab-news-report`（kebab-case，ClawHub / SkillHub 均未占用） |
| 版本来源 | `SKILL.md` frontmatter 的 `version:` |
| 触发 | `release: published`，或手动 `workflow_dispatch` |
| secrets | `CLAWHUB_TOKEN`（`clh_...`）、`SKILLHUB_API_KEY`（`skh_...`） |

先试跑再真发：

```bash
gh workflow run publish.yml -f dry_run=true      # 只校验 + 打包，不联系注册表
gh workflow run publish.yml -f publish_skillhub=false   # 半途失败时只补发另一侧
```

注意事项：

- **SkillHub 拒收无扩展名文件**（`LICENSE`、`Dockerfile` 会被自动剔除），因此授权声明同时写在 `SKILL.md` 正文里；`--dry-run` 不会暴露这类拒收，必须真发才知道。
- SkillHub CLI 要求 `SKILL.md` 带 `slug` / `displayName` / `version`，action 是在 `$RUNNER_TEMP` 的**副本**上注入的，仓库里的 `SKILL.md` 保持干净。
- registry 上的版本来自 `SKILL.md`，与 git tag 是两件事；两者不一致会导致上架版本在仓库里不存在。

## Contributing

见 [CONTRIBUTING.md](./CONTRIBUTING.md)。要点：

- Conventional Commits（`<type>(<scope>): <描述>`）
- 改动必须过 lint + 类型检查 + 测试
- 文档改动同步 CHANGELOG
- 凭据只走环境变量，绝不硬编码

## License

[CC BY-NC-SA 4.0](./LICENSE) — Copyright (C) 2026 CGArtLab
