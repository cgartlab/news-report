# Copyright (c) 2026 CGArtLab. CC BY-NC-SA 4.0.

# news-report — Contribution Guide

Thank you for considering contributing to **news-report**, a modular news-gathering Agent Skill.

## Prerequisites

- Python >= 3.10 (for the Python pipeline in `src/`)
- Node.js >= 18.17 (for Miniflux MCP, if using module 01)
- Git

## Development Setup

```bash
# Clone
git clone https://github.com/cgartlab/news-report.git
cd news-report

# Python pipeline
python -m pip install ruff mypy pre-commit
pre-commit install

# Miniflux MCP (module 01)
npx -y miniflux-mcp --help  # verify installation
```

## Branch Strategy

| Branch | Purpose | Protection |
|--------|---------|------------|
| `main` | Stable release branch | Protected, PR-only |
| `feat/*` | New features / modules | Free to push |
| `fix/*` | Bug fixes | Free to push |
| `docs/*` | Documentation-only changes | Free to push |

## Commit Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>
```

Types: `feat | fix | docs | style | refactor | perf | test | chore`

Scopes: `skill | module | docs | repo | src | config`

Examples:
```
feat(skill): add rss-http module as module 02
fix(module): correct searchEntries params in SKILL.md
docs(repo): upgrade AGENTS.md to v3
chore: add GitHub Actions lint workflow
```

## Code Quality

All changes must pass:

```bash
# Lint
ruff check src/

# Format check
ruff format --check src/

# Type check
mypy src/

# Pre-commit (runs all hooks)
pre-commit run --all-files
```

## Adding a New Module

1. Register in SKILL.md info source registry (module id, access method, capabilities, status)
2. Add module section in SKILL.md (structure aligned with module 01)
3. Provide copyable commands with platform notes
4. Update CHANGELOG.md
5. Update pyproject.toml if new dependencies are needed

**Planning modules only**: Register with status `规划中` — do not write implementation details, tool names, or config.

## Key Constraints

1. **Secrets only via env vars** — never hardcode API keys, tokens, or credentials
2. **Terminal examples must be copy-pasteable** — specify platform (Linux/macOS/Windows)
3. **Documentation changes must sync CHANGELOG.md**
4. **Only modify this repository** — do not touch other directories
5. **No push / tag / merge without explicit instruction**

## Quality Gates

- Code blocks balanced (even number of triple backticks per .md file)
- Version references consistent across SKILL.md, AGENTS.md, CHANGELOG.md
- No placeholder tool names in planning module sections
- Technical claims sourced (official docs, upstream source, or tested)
- Examples verified on target platform (or marked as illustrative)
- Standard ASCII hyphens only (no U+2010~U+2013, U+2212)

## License

By contributing, you agree that your contributions are licensed under [CC BY-NC-SA 4.0](./LICENSE).

---

(C) 2026 CGArtLab · CC BY-NC-SA 4.0
