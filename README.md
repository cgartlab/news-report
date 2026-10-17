# news-report

[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)
[![CI: Lint & Type Check](https://github.com/cgartlab/news-report/actions/workflows/lint.yml/badge.svg)](https://github.com/cgartlab/news-report/actions/workflows/lint.yml)
[![CI: Docs Check](https://github.com/cgartlab/news-report/actions/workflows/docs-check.yml/badge.svg)](https://github.com/cgartlab/news-report/actions/workflows/docs-check.yml)
[![Release](https://img.shields.io/github/v/tag/cgartlab/news-report)](https://github.com/cgartlab/news-report/tags)

news-report 是一个**模块化信息源**驱动的新闻采集（news-gathering）[Agent Skill](https://agentskills.io)：在对话中直接跨各信息源检索新闻 / 文章、查看订阅、搜索文章，并整理成新闻简报等任务的素材。

**Miniflux RSS**（经 `miniflux-mcp` MCP 服务器）作为 **模块 01** 已可用（完整保留原 miniflux-mcp-skill 集成内容）；另有模块 02 · Zhihu Search、模块 03 · Twitter/X CLI、模块 04 · Bilibili CLI、模块 05 · Xiaohongshu CLI 与模块 06 · X-Browser（Edge CDP）已登记（详见 [SKILL.md](./SKILL.md) 信息源注册表）；RSS 直取（`rss-http`）、News API（`news-api`）为规划中占位（模块 07 / 08）。**输出格式：见 SKILL.md「输出模板」章节**。

## Architecture

```
news-report/
├── SKILL.md          # 技能指令本体（模块化架构、模块 01 Miniflux、高级指南）
├── AGENTS.md         # AI 贡献者约束（定位、启动清单、质量门禁、提交规范）
├── CONTRIBUTING.md   # 贡献指南（开发设置、分支策略、代码质量）
├── CHANGELOG.md      # 版本历史（Keep a Changelog + SemVer）
├── README.md         # 本文件（对外简介）
├── LICENSE           # CC BY-NC-SA 4.0
├── pyproject.toml    # Python 项目配置（ruff, mypy）
├── .pre-commit-config.yaml  # Pre-commit hooks
└── .github/
    ├── CODEOWNERS              # 代码所有权
    ├── PULL_REQUEST_TEMPLATE.md
    ├── ISSUE_TEMPLATE/
    │   ├── bug_report.md
    │   └── feature_request.md
    └── workflows/
        ├── lint.yml            # Python lint + type check + config validation
        ├── release.yml         # 自动化发布（tag → GitHub Release）
        └── docs-check.yml      # 文档格式检查
```

## Information Source Registry

| Module | Access | Capabilities | Status |
|--------|--------|-------------|--------|
| 01 · `miniflux` | MCP server | Categories, feeds, search, unread, favorites | ✅ Active |
| 02 · `zhihu-search` | CLI / MCP | Search, AI Q&A, hot list, summaries, OAuth | ✅ Active |
| 03 · `twitter-cli` | CLI binary | Tweet search, timeline, bookmarks, users | ⏸️ Disabled (auth) |
| 04 · `bilibili-cli` | CLI binary | Video search, hot/rank lists, users | ⏸️ Disabled (bug) |
| 05 · `xiaohongshu-cli` | CLI binary | Note search, hot list, feed, topics | ⏸️ Disabled (auth) |
| 06 · `x-browser` | CDP (HTTP+WS) | Deep timeline scroll, retweet attribution | ⏸️ Disabled (needs CDP browser) |
| 07 · `rss-http` | HTTP (direct RSS/Atom) | — | 📋 Planned |
| 08 · `news-api` | HTTP API | — | 📋 Planned |

## Usage

Skill 指令位于 [SKILL.md](./SKILL.md)。在 agent 运行时中按名称 **`news-report`** 加载本 Skill（触发词与使用说明见 SKILL.md 的 frontmatter description 与正文）。

### Quick Start (Module 01: Miniflux)

```bash
# 1. Set environment variables
export MINIFLUX_BASE_URL="https://miniflux.example.com"
export MINIFLUX_TOKEN="your-api-token-here"

# 2. Configure MCP server in opencode
#    Add to ~/.config/opencode/opencode.json:
#    {
#      "mcp": {
#        "miniflux-mcp": {
#          "type": "local",
#          "command": ["npx", "-y", "miniflux-mcp"],
#          "enabled": true,
#          "env": {
#            "MINIFLUX_BASE_URL": "${MINIFLUX_BASE_URL}",
#            "MINIFLUX_TOKEN": "${MINIFLUX_TOKEN}"
#          }
#        }
#      }
#    }

# 3. Load skill in agent
#    /skill news-report
```

## Development

```bash
# Install dev tools
python -m pip install ruff mypy pre-commit
pre-commit install

# Run quality checks
ruff check src/
ruff format --check src/
mypy src/

# Run all pre-commit hooks
pre-commit run --all-files
```

### Branch Strategy

| Branch | Purpose | Protection |
|--------|---------|------------|
| `main` | Stable release | Protected, PR-only |
| `feat/*` | New features / modules | Free to push |
| `fix/*` | Bug fixes | Free to push |
| `docs/*` | Documentation-only | Free to push |

## Releases

This project uses **Semantic Versioning**. Releases are automated via GitHub Actions:

1. Update CHANGELOG.md with the new version entry
2. Bump version in SKILL.md, AGENTS.md, CHANGELOG.md (three places)
3. Create and push tag: `git tag v0.3.0 && git push origin v0.3.0`
4. GitHub Actions validates CHANGELOG and creates a GitHub Release

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for the full contribution guide.

**Quick reference:**
- Follow [Conventional Commits](https://www.conventionalcommits.org/)
- All changes must pass lint + type check
- Documentation changes must sync CHANGELOG.md
- Secrets only via environment variables, never hardcoded

## License

[CC BY-NC-SA 4.0](./LICENSE) — Copyright (C) 2026 CGArtLab
