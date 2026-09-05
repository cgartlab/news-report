# 仓库指南 — news-report

**面向对象**：后续修改本仓库的 AI / 贡献者。先读本文件，再动文件。

---

## 项目定位与边界

- 本仓库是 **news-report**：模块化信息源驱动的新闻采集（news-gathering）Agent Skill（文档型仓库），前身为 miniflux-mcp-skill。
- **只读采集**：Skill 只从信息源检索 / 整理数据，不写业务输出文件、不改信息源数据。
- **输出格式未设计**：本阶段（v0.2.x）只做信息检索与整理；任何新增内容不得声称已提供新闻简报 / 报告的输出模板。
- **信息源模块化**：每个信息源是独立模块。当前唯一可用模块为 **模块 01 · miniflux**（内容在 SKILL.md 中完整保留）；`rss-http`、`news-api` 仅为注册表占位，状态为「规划中」——**不得为占位模块编造已实现的工具名 / 命令 / 配置**，相关能力一律标注「待下阶段」。

## 关键约束

1. **密钥只走本地环境变量**：示例一律用 `${VAR}` 占位；绝不硬编码真实 API key / token，不得写入输出文件、配置样本或提交历史。
2. **终端示例必须可直接执行**：给出可复制命令 / 脚本并注明平台（Linux / macOS / Windows PowerShell），平台差异分别写出。
3. **文档改动同步 CHANGELOG**：改名、定位变化、新增 / 删除模块、结构或约定变更，必须在 CHANGELOG.md 加对应条目（Keep a Changelog 风格，版本号见下）。
4. **禁止越界**：只修改本仓库（news-report/）内容，不触碰其他目录；默认不 push、不打 tag / release、不 merge；确需时另行明确指示。
5. **文档一致性**：SKILL.md（技能本体）、README.md（对外简介）、AGENTS.md（本文件）与 CHANGELOG.md 描述的行为必须一致；SKILL.md 是核心资产，修订时保留既有实用细节（参数表、排障条目等勿删减）。

## 分支与提交规范（参考本工作区习惯）

- 工作基于 `main` 新建分支，分支命名用 `dev-xxx`（本仓库重构即 `dev-news-report`）或 `feat/`、`fix/` 前缀。
- 提交遵循 [Conventional Commits](https://www.conventionalcommits.org/)：

  ```
  <type>(<scope>): <描述>
  ```

  type 可选：`feat | fix | docs | style | refactor | perf | test | chore`；scope 常用 `skill`、`module`、`docs`、`repo`。示例：
  - `feat(news-report): rebrand and restructure into modular news-gathering skill v0.2.0`
  - `docs(module): document rss-http source planning state`
- 提交原子化：一个逻辑变更一个提交；提交后留在当前工作分支。

## 文件地图

| 文件 | 职责 |
|------|------|
| `SKILL.md` | Skill 指令本体：概述、模块化架构、通用约定、模块 01（Miniflux）细节、维护提示、版本信息 |
| `README.md` | 对外简介（模块化定位、指向 SKILL.md、许可证） |
| `AGENTS.md` | 本文件：AI 贡献者约束 |
| `CHANGELOG.md` | 版本历史（Keep a Changelog + SemVer） |
| `LICENSE` | CC BY-NC-SA 4.0 |

## 版本

语义化版本。当前：**v0.2.0**（更名重定位版）；v0.1.0 为原 miniflux-mcp-skill 初始发布。

---

(C) 2026 CGArtLab · CC BY-NC-SA 4.0
