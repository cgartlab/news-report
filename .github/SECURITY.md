# Copyright (c) 2026 CGArtLab. CC BY-NC-SA 4.0.

# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.2.x | Yes |
| 0.1.x | No |

## Reporting a Vulnerability

**Please do not report security vulnerabilities via public GitHub issues.**

To report a security issue:

1. Email the maintainer: **cgartlab** (via GitHub profile)
2. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We aim to respond within **48 hours** and will work on a fix as soon as possible.

## Security Guidelines

When contributing, please follow:

1. **Never hardcode secrets** — API keys, tokens, and credentials must use environment variables
2. **Validate all external input** — especially from RSS feeds, search results, and API responses
3. **Report, don't exploit** — if you find a vulnerability, report it privately first

## Dependencies

This project depends on:
- `miniflux-mcp` (npm) — for Miniflux MCP server
- Python standard library (no external Python dependencies for the pipeline in `src/`)

We use Dependabot for automated dependency updates.

---

(C) 2026 CGArtLab · CC BY-NC-SA 4.0
