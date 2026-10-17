# 仓库指南 — news-report

**面向对象**：后续修改本仓库的 AI / 贡献者。先读本文件，再动文件。

---

## 项目定位与边界

- 本仓库是 **news-report**：模块化信息源驱动的新闻采集（news-gathering）Agent Skill（文档型仓库），前身为 miniflux-mcp-skill。
- **只读采集**：Skill 只从信息源检索 / 整理数据，不写业务输出文件、不改信息源数据。
- **输出格式已定义**：v0.3.0 起 SKILL.md 包含「输出模板」章节，定义了新闻简报的完整格式（TOP SIGNAL → 紧急 → 关注 → 常规 → 背景 → 影响分析 → 来源统计）。新增内容应遵循该模板，修改模板需同步 CHANGELOG。
- **信息源模块化**：每个信息源是独立模块。当前唯一可用模块为 **模块 01 · miniflux**（内容在 SKILL.md 中完整保留）；`rss-http`、`news-api` 仅为注册表占位，状态为「规划中」——**不得为占位模块编造已实现的工具名 / 命令 / 配置**，相关能力一律标注「待下阶段」。

## 启动清单（动手前）

1. **先读后写**：任务开始先读本文件、SKILL.md 概览与 CHANGELOG.md 顶部，掌握当前定位、版本与既有约束，再动手。
2. **先问后做**：凡涉及版本号选择、模块增删、输出格式设计、跨仓库操作、发布动作（push / tag / merge），先用菜单或提问向用户确认，不擅自决定。
3. **最小改动**：只改完成任务必需的文件与行；SKILL.md 是核心资产，参数表、排障条目、环境变量表等既有实用细节**勿删减**。
4. **可溯源**：新增的技术论断（排障、参数、行为描述）必须有依据——官方文档、上游源码或实测；禁止编造（历史教训：曾编造 Miniflux 2FA 排障条目，审查时被移除）。

## 典型任务与操作原则

> 详细操作步骤见 SKILL.md「高级指南」对应章节，本表为速查。

| 任务 | 操作原则 |
|------|----------|
| 修订 SKILL.md | 结构对齐既有章节；参数表 / 排障条目增删需对照上游 miniflux-mcp 源码或 Miniflux 官方文档；同步 CHANGELOG |
| 新增 / 变更模块 | 注册表登记 → 编写模块章节（结构参照模块 01）→ 提供可复制示例并注明平台 → 同步 CHANGELOG；规划中模块只登记占位，不预写实现 |
| 文档 bug 修复 | 定位 → 对照来源核实 → 修改 → 保留原文细节再增补，不整段删除有效信息 |
| 搜索资料完善 | 外部信息注明来源 URL；技术细节以官方文档 / 上游源码为准；存疑处标注「待验证」 |
| 版本发布 | 按 SemVer 判断：bug 修复 / 文档补丁 → patch；新增模块 / 章节 / 定位变化 → minor；发布 tag 需用户明确指示 |

## 关键约束

1. **密钥只走本地环境变量**：示例一律用 `${VAR}` 占位；绝不硬编码真实 API key / token，不得写入输出文件、配置样本或提交历史。
2. **终端示例必须可直接执行**：给出可复制命令 / 脚本并注明平台（Linux / macOS / Windows PowerShell），平台差异分别写出。
3. **文档改动同步 CHANGELOG**：改名、定位变化、新增 / 删除模块、结构或约定变更，必须在 CHANGELOG.md 加对应条目（Keep a Changelog 风格）；版本号同步更新于 SKILL.md「版本信息」、本文件「版本」段与 CHANGELOG 顶部三处。
4. **禁止越界**：只修改本仓库（news-report/）内容，不触碰其他目录；默认不 push、不打 tag / release、不 merge；确需时另行明确指示。
5. **文档一致性**：SKILL.md（技能本体）、README.md（对外简介）、AGENTS.md（本文件）与 CHANGELOG.md 描述的行为必须一致；SKILL.md 是核心资产，修订时保留既有实用细节（参数表、排障条目等勿删减）。

## 质量门禁（改动后自检）

- **代码块配平**：改动后确认各 .md 中的三反引号（代码块标记）出现次数为偶数。
- **版本一致**：SKILL.md / AGENTS.md / CHANGELOG.md 中的版本引用一致。
- **无占位工具名残留**：规划中模块章节不得出现可被误调用的「工具名」。
- **技术论断可溯源**：每条排障 / 参数 / 行为说明有来源，不编造；存疑处标注「待验证」。
- **示例可执行**：新增命令均已按平台验证（或明确标注示意、非可执行）。
- **字符一致**：正文与代码使用标准 ASCII 连字符（`-`），不得混入 U+2010~U+2013、U+2212 等伪装连字符；中文破折号（`——`，U+2014）为合法标点除外。

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
| `SKILL.md` | Skill 指令本体：概述、模块化架构、通用约定、模块 01（Miniflux）细节、维护提示、高级指南（架构/模块开发/测试/部署/安全/性能/排障/扩展示例）、版本信息 |
| `README.md` | 对外简介（模块化定位、指向 SKILL.md、许可证） |
| `AGENTS.md` | 本文件：AI 贡献者约束（定位、启动清单、任务原则、质量门禁、提交规范） |
| `CHANGELOG.md` | 版本历史（Keep a Changelog + SemVer） |
| `LICENSE` | CC BY-NC-SA 4.0 |

## 版本

- **项目版本**：v0.8.0（新增模块 06 · x-browser X 时间线 Edge CDP）；v0.7.1 为 Contract 表 + 只读边界修正 + zhihu-cli 路径引用修复；v0.6.0 为新增模块 05 · xiaohongshu-cli 小红书 CLI；v0.5.0 为新增模块 03 · twitter-cli 和模块 04 · bilibili-cli；v0.4.0 为新增模块 02 · zhihu-cli；v0.3.0 为输出模板正式定义；v0.2.2 为专业化开发流程；v0.2.1 为工具签名与参数表修复 + 高级指南；v0.2.0 为更名重定位版；v0.1.0 为原 miniflux-mcp-skill 初始发布。
- **本文档版本**：v3.7（2026-10-17）—— 更新项目版本至 v0.8.0，反映模块 06 · x-browser 与占位模块重编号。

---

(C) 2026 CGArtLab · CC BY-NC-SA 4.0
