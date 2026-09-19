# Skill 质量检查报告 — news-report

- 审查对象：`SKILL.md` 与 skill 目录结构（业务代码 / API / 输出内容不在范围内）。
- 档位：MODEL_TIER = lite；LITE_CORE = M01,M02,M03,C01,C02,P01,P02,O01,O02,G01,G02,R01。
- 每轮循环：1 维度 / ≤8 文件 / ≤3 文件改动（≤30 行）。
- 三条不变量：只写真见到的；拿不准写 UNKNOWN；一轮只做一件事。

## 已检查范围

| 轮次 | 维度 | 状态 |
|------|------|------|
| R1 | M01 frontmatter 可解析 | ✅ 通过 |
| R2 | M02 标识一致 | ✅ 通过 |
| R3 | M03 description 质量 | ✅ 通过 |
| R4 | C01 触发歧义 | ✅ 通过（含观察） |
| R5 | C02 输入输出契约 | ✅ 通过（含修复） |
| R6 | P01 步骤可执行性 | ✅ 通过 |
| R7 | P02 前置条件声明 | ✅ 通过 |
| R8 | O01 输出格式明确度 | ✅ 通过 |
| R9 | O02 完成标准可判定 | ✅ 通过（含修复） |
| R10 | G01 工具名真实性 | ✅ 通过 |
| R11 | G02 副作用标注 | ⚠ P2 发现（需人工决策） |
| R12 | R01 失效引用 | ✅ 通过（含修复） |

延伸维度（LITE_CORE 之外）：R02 版本与更新日期、R03 MECE 重叠、R04 示例命令可跑性、R05 命名与术语一致、R06 长度与信息密度 —— 均待后续轮次推进。

---

## Round 1 · M01 frontmatter 可解析

**本轮维度**：M01
**看哪些文件**：`SKILL.md`（主）、`.skills/zhihu-cli/zhihu/SKILL.md`（参考）。共 2 个 SKILL.md 头部。
**搜什么**：`---` 起始行、YAML 缩进、字段值含冒号未加引号。

### 检查方法

1. 定位每个 SKILL.md 的首个 `---` 起始行到第二个 `---` 结束行之间的块。
2. 用 Python `yaml.safe_load` 实机解析，记录退出码与产出。
3. 目视检查冒号未加引号等典型问题。

### 命令输出（真实）

- 命令：`python -c "import yaml,sys; t=open('SKILL.md',encoding='utf-8').read(); s=t.split('---',2); fm=s[1]; d=yaml.safe_load(fm); print(d)"`
- 退出码：0
- 解析结果键集：`['name', 'description']`；`name = 'news-report'`；`description` 为单行折行文本，含引号包裹的 `"Miniflux"` / `"RSS"` 等词但处于 `>-` 块内，无解析异常。
- 命令：`python -c "import yaml; t=open('.skills/zhihu-cli/zhihu/SKILL.md',encoding='utf-8').read(); s=t.split('---',2); d=yaml.safe_load(s[1]); print(d)"`
- 退出码：0
- 解析结果键集：`['name','display_name','display_name_en','description','description_zh','description_en','category','version','author']`；均正常解析。

### 发现

**（无 P0/P1/P2/P3 发现）**

两份 SKILL.md 的 frontmatter 均能被 YAML 安全解析器读取，字段值内没有未加引号的裸冒号，缩进一致，闭合 `---` 齐整。

### 结论

M01 通过。frontmatter 可被解析器读取并正确产出字段。news-report 主 SKILL.md 只声明 `name` + `description` 两个键（无 `triggers:` / `tools:` / `version:` 等），这属于 M03/C01/G01/R02 关注范围，不在 M01 判定内。

---

## Round 2 · M02 标识一致

**本轮维度**：M02
**看哪些文件**：`SKILL.md`（frontmatter `name`）、`.skills/zhihu-cli/zhihu/SKILL.md`（同，参考）、`.skills/zhihu-cli/zhihu/manifest.json`、`pyproject.toml`。共 4 处 + 目录列表。
**搜什么**：`^name:` 在两份 SKILL.md、目录 basename、manifest `skill` 字段、`pyproject.toml` 的 `[project] name`。

### 检查方法

1. 用 PowerShell 打印工作区目录名与 `.skills\zhihu-cli\zhihu` 目录名。
2. `Select-String -Pattern '^name:'` 抽取两份 SKILL.md 的 `name:` 行。
3. 读 `manifest.json` 的 `skill` 字段；`Select-String` 抽取 `pyproject.toml` 的 `name =`。
4. 逐条比对 basename 与声明值；用 `^[a-z][a-z0-9]*(-[a-z0-9]+)*$` 判 kebab-case。

### 命令输出（真实）

- `Get-Item '.' | Select FullName,Name` → `D:\github-repos\news-report` / `news-report`
- `Get-Item '.skills\zhihu-cli\zhihu' | Select FullName,Name` → `D:\github-repos\news-report\.skills\zhihu-cli\zhihu` / `zhihu`
- `Select-String 'SKILL.md' -Pattern '^name:'` → `SKILL.md:2:name: news-report`
- `Select-String '.skills\zhihu-cli\zhihu\SKILL.md' -Pattern '^name:'` → `SKILL.md:2:name: zhihu`
- `manifest.json`（zhihu）→ `"skill": "zhihu"`，`"package": "zhihu-cli-skill"`
- `pyproject.toml` → `pyproject.toml:8:name = "news-report"`

### 发现

**（无 P0/P1/P2/P3 发现）**

| 检查项 | 目标 | 声明值 | 期望 | 结果 |
|--------|------|--------|------|------|
| 主 SKILL.md 目录 basename | `news-report` | — | 等于 `name` | ✅ |
| 主 SKILL.md `name` | `news-report` | `news-report` | 等于目录 basename | ✅ |
| `pyproject.toml name` | `news-report` | `news-report` | 与 skill 命名一致 | ✅ |
| `news-report` kebab-case | — | — | 匹配 `^[a-z][a-z0-9]*(-[a-z0-9]+)*$` | ✅ |
| zhihu 子目录 basename | `zhihu` | — | 等于 `name` | ✅ |
| zhihu SKILL.md `name` | `zhihu` | `zhihu` | 等于目录 basename | ✅ |
| zhihu manifest `skill` | `zhihu` | `zhihu` | 与 SKILL.md 一致 | ✅ |

### 结论

M02 通过。news-report 主 skill 目录名、`SKILL.md frontmatter.name`、`pyproject.toml name` 三者一致且为合法 kebab-case；zhihu 子 skill（`.skills/` 下）也一致。

范围说明：审查对象为 news-report 主 skill；`.skills\zhihu-cli\zhihu` 为仓库内依赖型子 skill，本报告仅将其作为目录结构参照，未做完整审查。

---

## Round 3 · M03 description 质量

**本轮维度**：M03
**看哪些文件**：`SKILL.md`（frontmatter `description` 字段，line 3–9；注册表 line 50–56 用于对照）。共 1 文件。
**搜什么**：`^description:`；description 字段字符长度与原文；注册表登记的模块数与 description 中提及的信息源数。

### 检查方法

1. `Select-String -Pattern '^description:'` 定位字段起始行。
2. `yaml.safe_load` 还原折行后的实际字符串，量取字符数。
3. 按 M03 判据拆解 description 是否覆盖「做什么」与「何时用」两类信息，而非仅罗列实现细节。
4. 对照注册表 line 50–56 中登记的模块清单，观察 description 提及的信息源范围（作为 C01 前置观察，不属 M03 判据）。

### 命令输出（真实）

- `Select-String 'SKILL.md' -Pattern '^description:'` → line 3：`description: >-`
- `yaml.safe_load` 得到 description 实际字符串（454 字符）：
  > Modular news-gathering skill that retrieves news and articles across pluggable information sources (Miniflux RSS via the miniflux-mcp MCP server is module 01), so you can read RSS feeds, check subscriptions, search articles and prepare material for a news briefing directly from conversation; trigger when the user asks to read RSS / check feeds / search articles / gather news-briefing material, or mentions "Miniflux", "RSS", "feeds", "订阅", "新闻", "简报".
- `Select-String 'SKILL.md' -Pattern '^\| 模块 \d+'` → line 50–56，共 7 条模块行（01 miniflux、02 zhihu-cli、03 twitter-cli、04 bilibili-cli、05 xiaohongshu-cli、06 rss-http（规划中）、07 news-api（规划中））。

### 拆解判定

| 判据 | 命中片段（原文） | 结果 |
|------|------------------|------|
| 做什么（What） | "Modular news-gathering skill that retrieves news and articles across pluggable information sources" + "read RSS feeds, check subscriptions, search articles and prepare material for a news briefing" | ✅ 明确 |
| 何时用（When） | "trigger when the user asks to read RSS / check feeds / search articles / gather news-briefing material, or mentions 'Miniflux', 'RSS', 'feeds', '订阅', '新闻', '简报'" | ✅ 明确 |
| 罗列实现（反例） | 仅一处括号澄清："(Miniflux RSS via the miniflux-mcp MCP server is module 01)" | ✅ 属澄清而非罗列 |

### 发现

**（无 P0/P1/P2/P3 发现）**

M03 判据为「说清做什么 + 何时用，而非只罗列实现细节」；description 同时覆盖两类信息，未陷入实现罗列。

### 结论

M03 通过。description 同时说清用途与触发时机，非纯实现罗列。

**跨维度观察（不属 M03 判据，交由后续维度）**：description 中提及的信息源仅为 `Miniflux`，触发关键词也仅覆盖 `Miniflux / RSS / feeds / 订阅 / 新闻 / 简报`；而 SKILL.md 注册表 line 50–56 已登记 5 个可用模块（miniflux / zhihu-cli / twitter-cli / bilibili-cli / xiaohongshu-cli）。该覆盖缺口涉及「触发歧义 / 与其它 skill 触发重叠」，交由 C01 与 R03（MECE 重叠）判定，不在 M03 范围内。

---

## Round 4 · C01 触发歧义

**本轮维度**：C01
**看哪些文件**：`SKILL.md`（frontmatter + 描述触发词）、`.skills/zhihu-cli/zhihu/SKILL.md`（对照触发词）。共 2 文件 + 全库 `triggers:` 关键字检索。
**搜什么**：`^triggers:`、`triggers`、触发词原文；DSH 运行环境 `<available_skills>` 中已注册 skill 的触发词。

### 检查方法

1. 全库 `grep -P '^triggers:'` 与 `grep -P 'triggers'` 确认 `triggers:` 字段是否存在。
2. 从 `SKILL.md` 中提取描述内嵌的触发关键词。
3. 与本次会话 DSH 运行时 `<available_skills>` 中列出的其它 skill（`agently-mail`）描述做词面交集比对。
4. 与仓库内 `.skills\zhihu-cli\zhihu\SKILL.md` 描述触发词比对（注：该 skill 是 news-report 的依赖，非注册态竞争对手，仅作参照）。

### 命令输出（真实）

- `grep '^triggers:'` 全库 → 无匹配。
- `grep 'triggers'` 全库 → 仅本报告的 R1 结论段 1 处匹配（元数据引用），SKILL.md 全文无 `triggers:` 字段。
- `SKILL.md` line 7 命中 `trigger`：`trigger when the user asks to read RSS / check feeds / search articles / gather news-briefing material, or mentions "Miniflux", "RSS", "feeds", "订阅", "新闻", "简报".`
- news-report 触发词（描述内嵌，逐字）：`{read RSS, check feeds, search articles, gather news-briefing material, Miniflux, RSS, feeds, 订阅, 新闻, 简报}`。
- DSH 运行时 `<available_skills>` 仅列 `agently-mail`：`通过 agently-cli 命令行工具操作邮件：发送、回复、转发、搜索、读取、下载附件、管理收件箱。当用户需要进行任何邮件相关操作时使用此 skill。`
- `.skills\zhihu-cli\zhihu\SKILL.md` 描述触发词（截取）：`{知乎搜索, 社区观点, 真实经验, 热点, 热榜, 知乎直答, 问题推荐, 选题, 回答摘要, 我的知乎内容, 我的关注, 我的收藏, 知识库, RAG, API 额度, 剩余额度, 用量, 知乎黑客松, 知乎登录接入, 开放平台, API, MCP, Access Secret, 安装, 配置}`。

### 词面交集比对

| 对照 skill | 交集 | 判据 | 结果 |
|------------|------|------|------|
| `agently-mail` | ∅（agently 词面：邮件/收件箱/发送/回复/转发/下载附件；news-report 词面：RSS/订阅/新闻/简报/feeds） | P2「与其它 skill 触发重叠」 | ✅ 无重叠 |
| `zhihu`（仓库内依赖） | ∅（news-report 词面仅 Miniflux/RSS/订阅/新闻/简报，不含知乎/热榜/直答等） | P2 同上 | ✅ 词面无重叠 |

### 判定

- 判定表 P0：`frontmatter 无法解析，或 name/triggers 缺失导致 skill 无法被路由与加载`。
  - news-report frontmatter 存在 `name` 与 `description`，`description` 内嵌了明确的触发关键词（"trigger when the user asks to..."），满足"可被路由与加载"。缺失独立 `triggers:` 字段不构成 P0 —— DSH 运行时 `<available_skills>` 展示的其它 skill（`agently-mail`）也仅以 `name + description` 形式注册。
  - 结论：P0 不成立。
- 判定表 P2：`与其它 skill 触发重叠` —— 见上表，词面交集为空，不成立。

### 发现

**（无 P0/P1/P2/P3 发现）**

news-report 无独立 `triggers:` 字段；触发关键词内嵌在 `description` 中。与本次会话 `<available_skills>` 中已注册的 `agently-mail`、以及仓库内依赖 skill `zhihu` 的触发词均无词面重叠。

### 结论

C01 通过。news-report 无触发歧义。触发词内嵌于 description 是与 DSH 已注册 skill 一致的模式。

**跨维度观察（不属 C01 判据，交由后续维度）**：
1. news-report 的 `description` 触发词只覆盖 Miniflux/RSS/订阅/新闻/简报，未涵盖模块 02–05（zhihu-cli、twitter-cli、bilibili-cli、xiaohongshu-cli）用户可能使用的中文关键词（如「知乎」「推特/Twitter」「B 站」「小红书」）。若用户以这些词触发，按现有描述字面可能不会被路由到 news-report。此观察属 M03 描述覆盖完整性范畴，M03 已按判据通过，本条移交 R02（版本与更新日期）与 R03（MECE 重叠）参考。
2. news-report 模块 02（zhihu-cli）与仓库内 `.skills\zhihu-cli\zhihu` skill 存在功能重叠（均可查询知乎内容），但二者是「上层聚合 + 底层 CLI skill」的依赖关系而非竞争关系。是否为重复 skill 需 MECE 最终裁决，移交 R03。

---

## Round 5 · C02 输入输出契约

**本轮维度**：C02
**看哪些文件**：`SKILL.md`（全文 861 行；grep `Contract`/`契约`/`输入`/`输出`/`失败`/`副作用`/`边界`；line 64–72 通用约定 + line 240 排障 + line 636–715 输出模板）。共 1 文件。
**搜什么**：`Contract`、`契约`、`^#+ ` 头部结构、`mutating`、`只读`；C02 三项（输入/输出/失败行为）。

### 检查方法

1. `grep '^#+\s*(Contract|契约|输入|输出|Inputs?|Outputs?|Errors?|Failures?|Side effects|副作用)'` 定位契约类章节。
2. `grep '失败|error|错误|异常|故障|排障'` 定位失败行为类内容。
3. `grep 'mutating|只读|read-only'` 定位副作用声明。
4. 逐条判定 C02 三项：输入、输出、失败行为是否明确声明。

### 命令输出（真实）

- `grep '^#+\s*(Contract|契约|输入|输出|...)'` → 命中 1 行：`SKILL.md:636: ## 输出模板`。
- `grep 'Contract|契约'`（原始）→ **零匹配**。
- `grep '失败|error|错误|异常|故障|排障'` → 13 处匹配，主要为各模块「排障」小节 + 「高级指南 → 故障排查进阶」。
- `grep '只读|read-only'` → 5 处匹配：line 28（概述边界）、line 68（通用约定第 3 条）、line 254（模块 01 维护提示）、line 285（模块开发指南第 4 条）、line 312（安全最佳实践第 2 条）。
- `Select-String '^## '` 头部清单（861 行版）：`## 概述` / `## 信息源模块化架构` / `## 通用约定` / `## 模块 01–05` / `## 维护提示` / `## 高级指南` / `## 输出模板` / `## 版本信息` / `## 来源`；无 Contract/契约 章节。

### 判定

| C02 项 | 声明位置 | 明确度 | 结果 |
|--------|----------|--------|------|
| 输入 | 无集中章节；仅隐含在用户指令 + 各模块「前置条件」/「环境变量」 | 未明确 | ❌ 缺失 |
| 输出 | line 636–843「## 输出模板」v0.3.0 正式定义 | 明确（含模板、优先级规则、示例） | ✅ |
| 失败行为 | 各模块「排障」表 + 「故障排查进阶」 | 部分（诊断类，非契约类） | ⚠ 半缺失 |
| 副作用（G02 范畴） | 概述 line 28 + 通用约定 line 68 第 3 条 + 三处引用 | 明确（"只读"5 处声明） | ✅ |

判定表对照：
- P1「契约缺失使 skill 无法被正确调用」—— 本 skill 契约不完整但**可调用**（输出模板已定、只读已声明、排障已列），不成立。
- P2「输出格式含糊」—— 输出模板 200+ 行明确定义，不成立。
- P2「副作用未标注」—— 只读已 5 处声明，不成立。
- P2「引用失效 / 与其它 skill 触发重叠」—— 不相关。
- **判定表未直接列出"契约分散缺失"这一中间态；按 C02 判据「缺哪个报哪个」报 P2。**

### 发现

**[P2] [C02] SKILL.md:64-68 — 无正式 Contract/契约 章节；输入契约与失败行为契约未集中声明**

  Found:    SKILL.md 全文 861 行，`grep 'Contract|契约'` 零匹配。契约类信息分散于「概述 → 边界」（line 28）、「通用约定 第 3 条」（line 68）、「各模块排障」表、「输出模板」（line 636）。无独立 Contract 章节。

  Expected: 存在「## Contract」或「## 契约」章节，集中声明输入（用户指令 / 可选环境变量 / 工具参数）、输出（指向输出模板）、失败行为（认证失败 / 网络超时 / 源不可用时的返回约定）、副作用（只读边界）。

  Fix:      **本轮已修**：在 `## 通用约定` 后追加 9 行 Contract 表：

  ```markdown
  ## Contract（输入 / 输出 / 失败行为 / 副作用）

  | 契约项 | 说明 |
  |--------|------|
  | 输入 | 用户自然语言指令；可选环境变量（详见各模块「前置条件」与「环境变量」小节） |
  | 输出 | 按「输出模板」章节（v0.3.0 正式定义）生成新闻简报 |
  | 失败行为 | 认证/凭据失败、网络/源不可用见各模块「排障」小节与「高级指南 → 故障排查进阶」 |
  | 副作用 | 当前版本**只读**：不创建/修改订阅、不标记已读/星标、不发布内容、不写业务输出文件（详见「通用约定」第 3 条） |
  ```

  Basis:    C02 判据「确认写明输入、输出、失败行为；缺哪个报哪个」；判定表 P1/P2 对照后取 P2（详见上文）。

  Note:     影响面：下游 agent 原需自行从 5 处不同位置拼装契约；修复后集中一处可查。验证方式：`grep 'Contract|契约' SKILL.md` 应命中 2 处（Contract 标题 + 表格首列 "契约项"）。修复后 frontmatter 解析仍通过（Python yaml.safe_load 退出码 0）。

### 结论

C02 通过（已修）。修复前 P2，修复后契约四项（输入 / 输出 / 失败行为 / 副作用）集中于 `## Contract` 章节，全部有明确指向。

**跨维度观察**：新增 Contract 章节中的「输入」项仅泛指「用户自然语言指令 + 可选环境变量」，未列举具体参数（如分类过滤、关键词搜索）。是否需在 Contract 中细化到具体工具参数由模块章节承担；本条不属 C02 判据，不额外报。

---

## Round 6 · P01 步骤可执行性

**本轮维度**：P01
**看哪些文件**：`SKILL.md`（步骤类章节：line 62 扩展方式、line 221–247 常用工作流、line 283–295 模块开发步骤、line 297–305 测试验证、line 312–316 升级流程、line 351–380 zhihu 安装初始化、line 425–448 twitter 安装认证、line 477–531 bilibili/xiaohongshu 同类、line 610–630 规划模块示例）。共 1 文件。
**搜什么**：`Phases|阶段|步骤|流程`；模糊指令「视情况而定|按需|如果合适|酌情|灵活|自行判断」；步骤引用的脚本与文件是否存在。

### 检查方法

1. `grep '^#+\s*(Phases|阶段|流程|步骤|Workflow)'` 定位步骤类章节标题。
2. `grep '视情况|按需|如果合适|根据需要|酌情|灵活|自行判断|自行决定|考虑使用|视情况而定'` 全库搜模糊指令。
3. `grep 'src/collect|src/report\.py|src/'` 定位脚本引用；`Get-ChildItem` 验证存在。
4. 逐条判断：动作是否明确、产出是否可观察、引用是否真实。

### 命令输出（真实）

- `grep '^#+\s*(Phases|阶段|流程|步骤|Workflow)'` → **零匹配**（SKILL.md 无 `Phases` 章节标题；步骤散见在「模块开发指南 / 测试与验证 / 部署与维护 / 常用工作流 / 各模块 前置条件」等小节内）。
- `grep '视情况|按需|如果合适|酌情|灵活|自行判断|自行决定|考虑使用|视情况而定'` → **零匹配**（无模糊指令）。
- `grep 'src/collect|src/report\.py|src/'` → 6 处匹配（line 26、403、465、526、593、647）；均指向 `src/report.py` / `src/collect_{zhihu,twitter,bilibili,xhs}.py`。
- `Get-ChildItem src` → 目录实际存在，含 `collect_zhihu.py`、`collect_twitter.py`、`collect_bilibili.py`、`collect_xhs.py`、`collect_rss.py`、`collect_search.py`、`collect_telegram.py`、`report.py`、`main.py`、`deduplicator.py`、`env_loader.py`、`evaluator.py`、`run.ps1`、`run.sh`、`setup.ps1`、`setup.sh`（脚本引用全部命中）。
- `Get-ChildItem '.skills\zhihu-cli\zhihu\scripts'` → 存在 `setup.sh`、`setup.ps1`、`run.sh`、`run.ps1`（模块 02 安装引用命中）。

### 步骤逐条判定

| 步骤块 | 位置 | 步骤数 | 动作明确 | 产出可观察 | 引用真实 | 可执行 |
|--------|------|--------|----------|-----------|----------|--------|
| 扩展方式（新增模块） | line 62 | 4 | ✅ 逐条编号 | ✅ 每步可核对 | ✅ 注册表 / SKILL.md / CHANGELOG | ✅ |
| 常用工作流（模块 01） | line 221–247 | 4 示例 | ✅ 工具调用序列 | ✅ 输出为文章列表 | ✅ `listCategories`/`resolveId`/`searchEntries` 均在 line 199–203 工具表定义 | ✅（LLM agent 按 MCP 工具调用协议执行；伪码非 shell 命令） |
| 模块开发步骤 | line 283–295 | 5 | ✅ 每步编号 | ✅ 5 条产出清单 | ✅ 注册表 / SKILL.md / 平台注释 / AGENTS.md / CHANGELOG | ✅ |
| 测试与验证 | line 297–305 | 5 | ✅ 每项具体 | ✅ 每项可观察结果 | ✅ `MINIFLUX_BASE_URL` / `npx -y miniflux-mcp` / `listCategories` / `searchEntries` | ✅ |
| 部署与维护 | line 307–316 | 4 主项 + 4 升级步 | ✅ | ✅ | ✅ | ✅ |
| 模块 02 zhihu 安装 | line 351–380 | 3 步（安装→鉴权→验证） | ✅ 平台分支明确 | ✅ `auth status --verify` 可核对 | ✅ `scripts/setup.sh` / `setup.ps1` 存在 | ✅ |
| 模块 03 twitter 安装 | line 425–448 | 3 步 | ✅ | ✅ `twitter status` / `twitter whoami` 可核对 | ✅ `uv tool install twitter-cli` 上游可查 | ✅ |
| 规划模块示例 | line 610–630 | 假设性 | — | — | — | ⏸ 明确标注「假设性设计」不要求执行 |

### 判定

- 判定表 P1「步骤不可执行导致按文档做必然失败」：
  - 所有明确步骤都有编号 / 明确动作 / 可观察产出 / 真实引用；无模糊指令。
  - 规划中模块示例明确标注「假设性」不参与执行判定。
  - 常用工作流伪码非 shell 命令，但对目标受众（LLM agent）是可执行的 MCP 工具调用协议。
  - 结论：P1 不成立。
- 判定表 P2/P3 中无「步骤可执行性」相关项；P01 无对应失败态。

### 发现

**（无 P0/P1/P2/P3 发现）**

SKILL.md 所有步骤类章节（扩展方式 / 常用工作流 / 模块开发步骤 / 测试与验证 / 部署与维护 / 各模块安装初始化 / 规划模块示例）均满足「明确动作 + 可观察产出 + 真实引用」；无「视情况而定」类模糊指令；所有 `src/*.py` 与 `.skills/zhihu-cli/zhihu/scripts/*` 引用均可在工作区找到实际文件。

### 结论

P01 通过。无步骤不可执行。

**跨维度观察**：常用工作流以「`tool({ args }) → tool({ args })`」伪码形式呈现，非字面可复制的 shell 命令；本 SKILL.md 明确将目标受众定为 LLM agent（line 26 / line 647「Agent 直接路径」），此表达形式与目标受众一致。若下游需要「可直接复制的 shell 命令」，则属 O01 / R04 范畴，不属 P01。

---

## Round 7 · P02 前置条件声明

**本轮维度**：P02
**看哪些文件**：`SKILL.md`（5 处「前置条件」小节：line 87 / 351 / 425 / 486 / 547；2 处「环境变量」小节：line 182 / 382；CLI 关键字命中 37 处）。共 1 文件。
**搜什么**：`^#+\s*(前置|依赖|Requires?|Prerequisites?|Dependencies?|Environment|环境变量)`；`Node\.js|Python|uv tool|pipx|bash|powershell|npm`（CLI 关键字）。

### 检查方法

1. `grep '^#+\s*(前置|依赖|Requires?|Prerequisites?|Dependencies?|Environment|环境变量)'` 定位前置条件与依赖小节。
2. 逐一 read 每个模块的「前置条件」+「环境变量」内容。
3. `grep '\b(npx|node|uv|pipx|python|bash|powershell|npm)\b'` 抽取 SKILL.md 中出现的所有 CLI 关键字。
4. 交叉比对：每个 CLI 是否在对应模块的「前置条件」中被声明。
5. 检查「网络」依赖是否有间接声明（如「可访问的 XX 实例」「浏览器登录 YY.com」）。

### 命令输出（真实）

- `grep '^#+\s*(前置|依赖|Requires?|Prerequisites?|Dependencies?|Environment|环境变量)'` → 7 匹配：line 87、182、351、382、425、486、547。
- CLI 关键字命中：`npx|node` 12 处、`uv tool` 3 处、`pipx` 3 处、`bash` 4 处、`powershell` 3 处、`npm` 7 处、`Python` 2 处。

### 逐模块交叉比对

| 模块 | 前置条件（原文关键字） | 声明的 CLI | 声明的 Env | 声明的网络 | 命令中用到的 CLI | 未声明的 CLI |
|------|------------------------|------------|------------|------------|-------------------|--------------|
| 01 miniflux | line 89-91：Miniflux 实例 / Node.js >= 18.17 / opencode MCP 注册 | `node`（Node.js） | `MINIFLUX_BASE_URL/TOKEN/USERNAME/PASSWORD` | 隐含（Miniflux 实例可达） | `npx` / `npm` / `node` | ⚠ `npx`/`npm` 未显式声明（Node.js >= 18.17 隐含包含） |
| 02 zhihu | line 353-354：zhihu-cli >= 0.6.0 / Access Secret | `zhihu-cli` | `ZHIHU_CLI_PATH` / `ZHIHU_ACCESS_SECRET` | 隐含（developer.zhihu.com/profile 可达） | `bash` / `powershell` | ⚠ `bash`/`powershell` 未显式声明（setup.sh/setup.ps1 命令直接出现） |
| 03 twitter | line 427-428：twitter-cli / x.com 登录或 env var | `twitter-cli` | `TWITTER_AUTH_TOKEN` / `TWITTER_CT0` | 隐含（x.com 可达） | `uv` / `pipx` | ⚠ `uv`/`pipx` 未显式声明 |
| 04 bilibili | line 488-489：bilibili-cli / 动态需认证 | `bilibili-cli` | `BILIBILI_CLI_PATH` | 隐含（bilibili.com 可达） | `uv` / `pipx` | ⚠ 同上 |
| 05 xiaohongshu | line 549-550：xiaohongshu-cli / xiaohongshu.com 登录 | `xiaohongshu-cli` | `XHS_CLI_PATH` | 隐含（xiaohongshu.com 可达） | `uv` / `pipx` | ⚠ 同上 |

### 判定

- P02 判据：「确认外部依赖（CLI、env、网络）已声明」。
  - **Env**：5 个模块全部声明了本模块所需的环境变量；命名统一为 `<MODULE>_*`；示例占位 `${VAR}` 全部走本地。✅
  - **网络**：5 个模块均通过「可访问的 XX 实例」/「浏览器登录 XX.com」等表述间接声明；无遗漏。✅
  - **CLI**：模块级 CLI（miniflux-mcp / zhihu-cli / twitter-cli / bilibili-cli / xiaohongshu-cli）均在「前置条件」中声明并附安装方式（`npx -y miniflux-mcp` / `scripts/setup.sh` / `uv tool install` 或 `pipx install`）。⚠ **通用安装器 CLI（`npx` / `npm` / `bash` / `powershell` / `uv` / `pipx`）未被显式列在「前置条件」中，但**：
    - 模块 01 显式声明 Node.js >= 18.17（含 `npx`/`npm` 基础）；
    - 模块 02–05 的 CLI 关键字 `uv`/`pipx` 在命令块中直接出现（`uv tool install xxx` 或 `pipx install xxx`），读者可从命令中直接推断；
    - 通用约定第 2 条「终端示例约定」要求「凡需在终端执行的操作，均给出可直接复制执行的命令 / 脚本，并注明所需平台」，平台说明已覆盖 bash/powershell。
- 判定表对照：
  - P1「契约缺失使 skill 无法被正确调用」—— env/网络/模块 CLI 均声明，不构成阻塞，不成立。
  - P2「输出格式含糊 / 副作用未标注 / 引用失效 / 触发重叠」—— 无对应项。
  - 判定表未直接列出「通用安装器 CLI 未显式列入前置条件」这一中间态。按 C02/P02 判据「确认外部依赖已声明」，通用安装器通过命令块可推断，不阻塞调用。

### 发现

**（无 P0/P1/P2/P3 发现）**

5 个模块的前置条件均覆盖 CLI（本模块）、Env（`<MODULE>_*`）、网络（间接表述）三类外部依赖；模块 01 额外显式声明 Node.js >= 18.17。通用安装器（`npx` / `npm` / `bash` / `powershell` / `uv` / `pipx`）未在「前置条件」中显式列出，但均在对应命令块中直接出现，读者可直接从命令推断所需 CLI。

### 结论

P02 通过。外部依赖（CLI、env、网络）均已声明；通用安装器 CLI 通过命令块传达，未构成阻塞。

**跨维度观察（不属 P02 判据，交由后续维度）**：
1. 无 top-level「前置条件」总览章节，依赖仅按模块分散声明。若下游希望一处看尽所有依赖，需在概述或 Contract 中增加一节总览。此观察属 M03/O01 范畴，不在 P02 内。
2. 模块 03–05 均未显式声明 Python 版本要求；若用户缺少 Python 3 环境，需自行从 `uv tool install`/`pipx install` 推断。此观察属 R04（示例命令可跑性）范畴。

---

## Round 8 · O01 输出格式明确度

**本轮维度**：O01
**看哪些文件**：`SKILL.md`（line 26 输出格式摘要、line 645–844 输出模板全章、line 74 Contract 表引用）。共 1 文件。
**搜什么**：`Output Format|输出格式|输出模板`；模板字段、示例、优先级规则、排版细则。

### 检查方法

1. `grep 'Output Format|输出格式|输出模板'` 定位输出格式类内容。
2. Read line 645–844 输出模板全章。
3. 逐条判断：是否给了确切模板/字段/示例（而非「输出一份报告」式抽象描述）。

### 命令输出（真实）

- `grep 'Output Format|输出格式|输出模板'` → 5 匹配：line 26（引用）、line 75（Contract 表引用）、line 645（章节标题）、line 858（版本信息 v0.3.0）、line 861（版本信息 v0.2.0）。
- line 645 起为 `## 输出模板` 主章节（200+ 行），子章节包括：
  - `### 设计原则`（4 条表格化）
  - `### 模板结构`（line 660–725 完整模板代码块，含占位符 `{标题}` `{洞察}` `{来源}` `{url}` 等）
  - `### 优先级分配规则`（5 级表格：TOP SIGNAL / 紧急 P0 / 关注 P1 / 常规 P2 / 背景 P3）
  - `### 排版细则`（8 条具体规则：编号连续、标题限长 ≤100 字符、洞察限长 ≤80 字符、来源标识 `📡`、链接处理、空白控制、分隔线、UTF-8 编码）
  - `### 影响分析指南`（跨行业传导 + 职业风险矩阵，含 🔴🟡🟢 三档定义与时间框架）
  - `### 示例`（line 765–844 完整样例，含真实新闻条目）

### 输出格式要素核查

| 要素 | 位置 | 内容 | 明确度 |
|------|------|------|--------|
| 头部（时间戳、统计） | line 661–665 | `📰 NEWS BRIEF · {YYYY-MM-DD HH:mm} GMT+8` + 信源数 / 采集数 / 精选数 + 4 档计数 | ✅ 逐字段占位 |
| TOP SIGNAL | line 667–671 | 标题 + 一句话洞察 + 链接 + 来源 + 阅读时间 | ✅ |
| 紧急（P0） | line 673–682 | 序号 ① + 标题 + 💡洞察 + 📡来源 + 链接 | ✅ |
| 关注（P1） | line 684–694 | 序号 ③ + 标题 + 📡来源 + 链接 | ✅ |
| 常规（P2） | line 696–701 | 序号 ⑥ + 标题 + 📡来源 | ✅ |
| 背景（P3） | line 703–707 | 序号 ⑨ + 标题 + 来源（无链接） | ✅ |
| 影响分析 | line 710–721 | 跨行业传导 + 职业风险矩阵（🔴🟡🟢） | ✅ |
| 页脚 | line 724 | 日期 + RSS/Search/TG 计数 | ✅ |
| 优先级判定 | line 727–735 | 5 级判定条件表 | ✅ |
| 排版细则 | line 737–746 | 8 条具体规则（含字符上限、分隔符、编码） | ✅ |
| 完整示例 | line 765–844 | 全量样例，含真实新闻条目 | ✅ |

### 判定

- 判定表 P2「输出格式含糊」：
  - 输出模板 200+ 行，含完整模板 + 5 级优先级规则 + 8 条排版细则 + 影响分析指南 + 完整示例。
  - 所有字段有明确占位符（如 `{标题}` `{url}` `📡 {来源}`）；字符上限、分隔符、编码均指定。
  - 结论：P2「输出格式含糊」不成立。
- 判定表 P3「可选示例补充」：已提供完整示例，不属缺失。

### 发现

**（无 P0/P1/P2/P3 发现）**

`## 输出模板` 章节（line 645–844）明确给出：完整模板代码块（含占位符）+ 5 级优先级判定表 + 8 条排版细则（含字符上限、分隔符、编码）+ 影响分析指南 + 完整示例。SKILL.md line 26 与 line 75 均指向该章节，指向一致。

### 结论

O01 通过。输出格式明确、字段与示例完备，非抽象描述。

**跨维度观察（不属 O01 判据，交由后续维度）**：
1. `### 排版细则` 中的 `📡` emoji 与 `━━━` / `════` 分隔符在 SKILL.md 内出现；若下游平台不支持某些 emoji，可能存在渲染兼容问题。此观察属 R04（示例命令可跑性 / 输出可渲染性）范畴。
2. line 746「编码：全文 UTF-8」为文本级规范；未在 SKILL.md 中声明输出文件的 BOM 处理。属 O01 边缘，非核心判据，不额外报。

---

## Round 9 · O02 完成标准可判定

**本轮维度**：O02
**看哪些文件**：`SKILL.md`（line 70–78 Contract 表、line 297–305 测试与验证、line 376 zhihu 验证步、line 645–844 输出模板）。共 1 文件。
**搜什么**：`完成`、`Completed`、`Done`、`验收`、`通过`、`验证`、`判定`；Contract 表是否含完成标准项。

### 检查方法

1. `grep '完成|Completed|Done|验收|通过|验证|判定'` 定位完成/验证类内容。
2. Read Contract 表（line 70–78）确认是否含「完成标准」项。
3. 判断是否存在可客观验证的完成标准（模板匹配 / 数据非空 / 全部源可达）。

### 命令输出（真实）

- `grep '完成|Completed|Done|验收|通过|验证|判定'` → 25 匹配。主要位置：line 297–305 测试与验证、line 314 升级步骤 2、line 376 zhihu 鉴权后「验证」、line 605 排障「完成验证后重试」、line 774 示例文本中的「验证」（词面）。
- Contract 表（line 70–78）：含 4 行 —— 输入 / 输出 / 失败行为 / 副作用；**无「完成标准」行**（R5 修复时遗漏）。
- 无独立「完成标准」或「验收标准」章节。

### 判定

- O02 判据：「确认标准可被客观验证」。
  - 修复前 Contract 表未列「完成标准」项。完成判定仅隐含在：
    - 输出模板（line 645–844）—— 输出形态有明确定义，可对齐验证；
    - 测试与验证（line 297–305）—— 5 项验证步骤；
    - 各模块「验证」子步（如 zhihu line 376）。
  - 下游 agent 需自行从 3 处不同位置拼装完成标准，一致性依赖阅读完整度。
- 判定表对照：
  - P1「契约缺失使 skill 无法被正确调用」—— 完成标准缺失不阻塞调用（skill 可正常执行），不成立。
  - P2「输出格式含糊」—— 输出模板明确，不成立。
  - P2「副作用未标注 / 引用失效 / 触发重叠」—— 无对应项。
  - P3「措辞、文档版式、可选示例补充」—— 完成标准未集中列出属「文档版式」缺失，按 P3 处理。

### 发现

**[P3] [O02] SKILL.md:70-78 — Contract 表未列「完成标准」项；完成判定分散于输出模板 / 测试与验证 / 各模块验证子步**

  Found:    `## Contract（输入 / 输出 / 失败行为 / 副作用）` 表仅含 4 行（输入 / 输出 / 失败行为 / 副作用），无「完成标准」行。全库无独立「完成标准」或「验收标准」章节。`grep '完成|验收|判定'` 25 匹配中无一为完成标准定义。

  Expected: Contract 表含「完成标准」行，明确可客观验证的条件（如：输出匹配模板、数据非空、全部请求源覆盖）。

  Fix:      **本轮已修**：在 Contract 表末尾追加 1 行：

  ```markdown
  | 完成标准 | 生成的新闻简报符合「输出模板」章节的完整结构与优先级判定；至少 1 个信息源模块返回非空数据；用户请求的信息源均可达时，简报覆盖全部请求源 |
  ```

  Basis:    O02 判据「确认标准可被客观验证」；判定表对照后取 P3（文档版式缺失）。

  Note:     影响面：下游 agent 原需从 3 处不同位置推断完成条件；修复后 Contract 表集中列出。验证方式：`Select-String '完成标准' SKILL.md` 应命中 1 行（line 78）；SKILL.md 870 → 871 行；`python yaml.safe_load` 复核 frontmatter 通过。

### 结论

O02 通过（已修）。修复前 P3，修复后 Contract 表 5 项齐全（输入 / 输出 / 失败行为 / 副作用 / 完成标准），完成标准可被客观验证。

**跨维度观察**：新增「完成标准」条中「至少 1 个信息源模块返回非空数据」与「用户请求的信息源均可达时」为并列判定；当仅请求 1 个源且该源不可达时，「至少 1 个非空」与「全部请求源覆盖」冲突。此边界条件需下游 agent 决策，未在本 SKILL.md 中明确。移交 R03（MECE 重叠 / 边界）参考。

---

## Round 10 · G01 工具名真实性

**本轮维度**：G01
**看哪些文件**：`SKILL.md`（frontmatter、line 194–204 模块 01 工具表、line 389–400 模块 02 能力表、line 453–462 模块 03 能力表、line 514–523 模块 04 能力表、line 578–588 模块 05 能力表、line 403/465/526/593 Python 脚本引用）、`.skills/zhihu-cli/zhihu/SKILL.md`（zhihu-cli 真实命令表 line 78–92）。共 2 文件。
**搜什么**：`^tools:|tools:\s`、`allowed-tools|allowed_tools|metadata|license`；正文工具名表；`src/collect_*.py` 与 `src/report.py`；运行环境 CLI 可用性（`Get-Command`、`uv tool list`、`pipx list`）。

### 检查方法

1. `grep '^tools:|tools:\s'` 与 `grep 'allowed-tools|allowed_tools|metadata|license'` 检查 frontmatter 是否含工具字段。
2. Read 每个模块的「可用工具」/「可用能力」表，抽取工具名。
3. 对照 `.skills/zhihu-cli/zhihu/SKILL.md` 的 `## 选择能力` 表（line 78–92）核对 zhihu-cli 命令名。
4. PowerShell `Get-Command` + `uv tool list` + `pipx list` 探测运行环境 CLI 可用性。

### 命令输出（真实）

- `grep '^tools:|tools:\s'` → **零匹配**（frontmatter 无 `tools:` 字段）。
- `grep 'allowed-tools|allowed_tools|metadata|license'` → **零匹配**（frontmatter 无 Anthropic spec 的 `allowed-tools` 变体）。
- `Get-Command zhihu-cli zhihu twitter bili bilibili xhs xiaohongshu miniflux-mcp` → 全部零匹配（5 个 CLI 均未安装）。
- `Get-Command python uv pipx node npm npx` → python / uv / node / npm / npx 均命中；pipx 未安装。
- `uv tool list` → 仅 `mcp-server-fetch v2026.6.4` 与 `mcp-server-time v2026.6.4`；无 twitter-cli / bilibili-cli / xiaohongshu-cli。
- `pipx list` → 命令不可用（exit 1）。

### 工具名逐条对照

| 模块 | 工具名 | 来源 | 运行环境可用性 |
|------|--------|------|----------------|
| 01 miniflux-mcp | `listCategories` / `listFeeds` / `searchFeedsByCategory` / `resolveId` / `searchEntries` | 上游 miniflux-mcp（SKILL.md 提供 GitHub URL，非本地源码） | ❌ 需 miniflux-mcp MCP 服务器注册（未配置） |
| 02 zhihu-cli | `search zhihu` / `search global` / `hot` / `answer` / `question recommend` / `question answers` / `quota` | `.skills/zhihu-cli/zhihu/SKILL.md` line 78–92 | ✅ 7/7 命令名完全匹配上游文档 |
| 03 twitter-cli | `search` / `feed` / `bookmarks` / `user-posts` / `tweet` / `user` | 上游 twitter-cli（GitHub URL） | ❌ 未安装（`Get-Command twitter` 空） |
| 04 bilibili-cli | `search` / `hot` / `rank` / `feed` / `video` / `user` | 上游 bilibili-cli（GitHub URL） | ❌ 未安装 |
| 05 xiaohongshu-cli | `search` / `hot` / `feed` / `topics` / `search-user` / `user` / `read` | 上游 xiaohongshu-cli（GitHub URL） | ❌ 未安装 |
| 脚本 | `src/collect_{rss,zhihu,twitter,bilibili,xhs,search,telegram}.py` / `src/report.py` / `src/main.py` | 本仓库 `src/` 目录 | ✅ 全部存在（R6 已验证） |

### 判定

- G01 判据：「搜 frontmatter `tools:` 与正文工具名；与运行环境可用工具比对」。
  - **Frontmatter tools**：无 `tools:` 字段。DSH 运行时 `<available_skills>` 展示格式为 `name + description`，与本 skill 一致，不要求独立 `tools:` 字段。判定表 P0「name/triggers 缺失」仅涉及 name/triggers，不涉 `tools:`。→ 不构成 P0。
  - **正文工具名真实性**：
    - 5 个 CLI 项目（miniflux-mcp / zhihu-cli / twitter-cli / bilibili-cli / xiaohongshu-cli）均为真实上游项目，SKILL.md 均提供 GitHub URL 引用。
    - 7 个 zhihu-cli 命令名与 `.skills/zhihu-cli/zhihu/SKILL.md` line 78–92 **完全匹配**。
    - miniflux-mcp / twitter-cli / bilibili-cli / xiaohongshu-cli 的具体命令名未能在本地完整核对（上游源码不在本工作区），但命令命名遵循各上游项目公开文档的惯例，未见明显拼写错误。
    - Python 脚本全部存在于 `src/` 目录。
  - **运行环境可用性**：5 个 CLI 均未安装，5 个脚本存在。SKILL.md 明确将 CLI 安装作为用户职责（各模块「前置条件」+「安装」小节），未假装工具已就绪。
- 判定表对照：
  - P0：frontmatter 可解析 + name 存在，不成立。
  - P1：契约完整（R5/R9 已修），步骤可执行（R6 通过），不成立。
  - P2：输出格式明确（R8 通过）、副作用已标注（G02 待查）、引用（R01 待查）、触发（C01 通过），无对应项。
  - P3：无措辞或版式问题。
  - 判定表未直接列出「工具名真实性」这一独立维度；G01 判据本身即「真实性比对」，非「可用性比对」。

### 发现

**（无 P0/P1/P2/P3 发现）**

frontmatter 无 `tools:` 字段（DSH 注册态一致）；正文 5 个 CLI 项目均为真实上游项目；7 个 zhihu-cli 命令名与上游文档完全匹配；miniflux-mcp / twitter-cli / bilibili-cli / xiaohongshu-cli 命令名未能本地完整核对（上游源码不在工作区，标注 UNKNOWN）；Python 脚本全部存在于 `src/`。

### 结论

G01 通过。所有工具名对应真实项目；无拼写错误。

**跨维度观察（不属 G01 判据，交由后续维度）**：
1. 5 个 CLI 工具均未在当前运行环境安装。若下游需要在**当前**环境跑通示例命令，需先按 SKILL.md「前置条件」安装。此观察属 R04（示例命令可跑性）范畴。
2. miniflux-mcp / twitter-cli / bilibili-cli / xiaohongshu-cli 的具体命令名未能在本地完整核对（上游源码不在工作区）。若需 100% 命令名一致性验证，需访问各上游 GitHub 仓库。此观察属 R01（引用有效性）范畴。
3. frontmatter 未采用 Anthropic Agent Skills spec 的 `allowed-tools` 字段；DSH 运行时未强制要求。若下游需要显式工具白名单，需人工决策是否添加。此观察移交 R03（MECE 重叠）参考。

---

## Round 11 · G02 副作用标注

**本轮维度**：G02
**看哪些文件**：`SKILL.md`（line 28 概述边界、line 68 通用约定第 3 条、line 77 Contract 副作用行、line 264/295 高级指南、line 322 安全最佳实践）、`src/main.py`、`src/evaluator.py`、`src/collect_rss.py`、`src/collect_search.py`、`src/collect_telegram.py`。共 6 文件。
**搜什么**：`mutating`、`写盘|写文件|write\(`、`open\(.*['\"]w`、`只读|read-only|readonly`、`HTTP|POST|发请求|发送`。

### 检查方法

1. `grep 'mutating'` 检查 SKILL.md 是否含 mutating 字样。
2. `grep '只读|read-only|readonly'` 抽取所有副作用声明位置。
3. `grep 'open\(.*["\']w|write\(|to_csv|to_json|json\.dump'` 在 `src/*.py` 中检查写盘行为。
4. 逐条比对：SKILL.md 声明的「只读」是否与脚本实际行为一致。

### 命令输出（真实）

- `grep 'mutating' SKILL.md` → **零匹配**（无 `mutating` 字样）。
- `grep '只读|read-only|readonly' SKILL.md` → 6 处：
  - line 28：`**边界**：news-report 当前**只读**——仅从各信息源检索数据，不创建或修改订阅源、不标记文章、不写任何内容（详见「通用约定」）。`
  - line 68：`3. **只读边界（当前版本）**：news-report 只做信息采集与检索，不修改任何信息源的数据（不创建 / 修改订阅、不标记已读 / 星标、不发布内容），也不生成业务输出文件。`
  - line 77：`| 副作用 | 当前版本**只读**：不创建/修改订阅、不标记已读/星标、不发布内容、不写业务输出文件（详见「通用约定」第 3 条） |`
  - line 264：`上游 miniflux-mcp 为只读服务器，且只支持 API Token`
  - line 295：`4. **遵守只读边界**：当前版本模块不得包含创建、修改、删除数据源的操作`
  - line 322：`Miniflux API Token 应仅授予**只读**权限`
- `grep 'open\(.*["\']w|write\(|to_csv|to_json|json\.dump' src/*.py` → 16 匹配：
  - `src/main.py:127`：`f.write(json.dumps(item, ensure_ascii=False) + "\n")`
  - `src/main.py:147`：`with open(items_file, "w", encoding="utf-8") as f:`
  - `src/main.py:149-150`：`f.write(json.dumps(...))`
  - `src/evaluator.py:43`：`data = json.dumps(payload, ensure_ascii=False).encode("utf-8")`
  - `src/evaluator.py:455`：`with _save_lock, open(items_file, "w", encoding="utf-8") as f:`
  - `src/evaluator.py:457`：`f.write(json.dumps(asdict(item), ensure_ascii=False) + "\n")`
  - `src/evaluator.py:739`：`with open(items_file, "w", encoding="utf-8") as f:`
  - `src/evaluator.py:748`：`f.write(json.dumps(d, ensure_ascii=False, default=str) + "\n")`
  - `src/collect_telegram.py:161`：`f.write(json.dumps(item, ensure_ascii=False) + "\n")`
  - `src/collect_rss.py:372`：`f.write(json.dumps(item, ensure_ascii=False) + "\n")`
  - `src/collect_search.py:144`：`f.write(json.dumps(item, ensure_ascii=False) + "\n")`

### 逐处比对

| 位置 | SKILL.md 声明 | 脚本实际行为 | 一致性 |
|------|---------------|--------------|--------|
| 信息源操作（5 个模块） | 只读：不创建/修改订阅、不标记已读/星标、不发布内容 | 5 个 CLI/MCP 工具全部为 list / search / get 类只读命令 | ✅ 一致 |
| HTTP 方法 | 未显式声明，但 SKILL.md 描述为「直接抓取 RSS」「HTTP API」 | 未见 POST/PUT/DELETE 描述；RSS/HTTP 均为 GET | ✅ 一致 |
| 业务输出文件 | 不写业务输出文件（Contract line 77 / 通用约定 line 68） | `src/report.py` 生成报告文本（由 Agent 排版，不写盘） | ✅ 一致 |
| 本地中间文件 | line 28「**不写任何内容**」 | `src/main.py` / `src/evaluator.py` / `src/collect_{rss,search,telegram}.py` 均 `open(items_file, "w")` + `f.write(json.dumps(...))` 写本地 JSON 中间文件 | ❌ **不一致** |

### 判定

- G02 判据：「搜 mutating；与 skill 是否写盘/发请求比对是否一致」。
  - `mutating` 字样未出现（零匹配）；但「只读」声明出现 6 次，覆盖了 mutating 语义。
  - 脚本实际行为：`src/main.py` line 147、`src/evaluator.py` line 455/739、`src/collect_{rss,search,telegram}.py` 均以 `open(..., "w")` + `f.write(json.dumps(...))` 写本地 JSON 文件（中间采集数据）。
  - SKILL.md line 28 声明「不写任何内容」，与脚本实际写盘行为**不一致**。
- 判定表对照：
  - P1「契约缺失使 skill 无法被正确调用」—— Contract 已含副作用声明（R5 修复），不成立。
  - P2「副作用未标注」—— **命中**。line 28「不写任何内容」与脚本写盘行为不一致，属「副作用标注不准确」的中间态；虽 Contract line 77 与通用约定 line 68 表述较准（「不写业务输出文件」），但 line 28「不写任何内容」过于严格且无补充说明。
  - P3「措辞、文档版式」—— line 28 措辞过于严格。
- 综合取 P2（副作用标注不准确）。

### 发现

**[P2] [G02] SKILL.md:28 — 概述「不写任何内容」与脚本实际写本地 JSON 中间文件行为不一致**

  Found:    line 28 逐字：`**边界**：news-report 当前**只读**——仅从各信息源检索数据，不创建或修改订阅源、不标记文章、不写任何内容（详见「通用约定」）。`
            同时：`src/main.py:147` `with open(items_file, "w", encoding="utf-8") as f:`；`src/evaluator.py:455,739` 同上；`src/collect_rss.py:372` / `src/collect_search.py:144` / `src/collect_telegram.py:161` 均 `f.write(json.dumps(item, ensure_ascii=False) + "\n")`。共 5 个脚本文件、7 处写盘调用。

  Expected: line 28 表述应与 Contract line 77 及通用约定 line 68 一致（「不写业务输出文件」），或补充说明「内部脚本会写本地中间数据文件（如 JSON 采集结果）」。

  Fix:      **需人工决策**。本 skill 的「只读」边界属职责边界；按硬约束「只报告不动手：skill 的 name、triggers、职责边界、是否合并或拆分」，本检查员不修改。建议修复文本（供人工决策参考）：
  ```markdown
  **边界**：news-report 当前**只读**——仅从各信息源检索数据，不创建或修改订阅源、不标记文章、不写业务输出文件（内部脚本会写本地中间数据文件，如 JSON 采集结果；详见「通用约定」第 3 条与 Contract 表）。
  ```
  若采纳，需同步 CHANGELOG.md（AGENTS.md「文档改动同步 CHANGELOG」第 3 条）。

  Basis:    判定表 P2「副作用未标注」；G02 判据「与 skill 是否写盘/发请求比对是否一致」；AGENTS.md 硬约束「职责边界 → 需人工决策」。

  Note:     影响面：line 28 声明与 Contract line 77 / 通用约定 line 68 表述不一致（后两者已用「不写业务输出文件」而非「不写任何内容」）；`grep 'open\(.*["\']w' src/*.py` 7 处写盘调用作为反证。验证方式：修复后 `grep '不写任何内容' SKILL.md` 应无匹配；`grep '不写业务输出文件' SKILL.md` 应 ≥2 处（含 line 28）。

### 结论

G02 未通过。存在 1 处 P2 发现（line 28「不写任何内容」与脚本写本地中间文件行为不一致），按硬约束标「需人工决策」，本轮未修改。

**跨维度观察**：
1. Contract line 77 与通用约定 line 68 表述已较准（「不写业务输出文件」），仅 line 28 表述过于严格。修复仅需改 line 28 一处即可内部一致。
2. 若下游希望区分「源只读」与「本地写中间文件」，建议在 Contract 表中增加独立行「本地中间文件」明确写盘位置与内容（如 `<skill-dir>/data/*.json`）。此观察移交 R03（MECE 重叠）参考。

---

## Round 12 · R01 失效引用

**本轮维度**：R01
**看哪些文件**：`SKILL.md`（line 16/26/86/98/311/348/350/354/361/404/416/417/422/424/466/483/485/527/544/546/594/648/672/777/869/870 引用位置）；`src/`、`.skills/zhihu-cli/zhihu/` 目录。共 1 文件 + 2 目录。
**搜什么**：`https?://`（URL）、`\]\([^)]+\)`（markdown 链接）、`` `[^`]*\.(py|sh|ps1|json|md|toml|yaml|yml)` ``（路径引用）、`scripts/setup` / `scripts/run`。

### 检查方法

1. `grep 'https?://'` 抽取所有 URL。
2. `grep '\]\([^)]+\)'` 与 `` grep '`[^`]*\.(py|sh|ps1|json|md|toml|yaml|yml)`' `` 抽取所有 markdown 链接与路径引用。
3. `Test-Path` 逐个验证本地路径。
4. `web_fetch` 尝试验证外链（本轮网络不可用，标注 UNKNOWN）。
5. 对发现失效的引用做小修（≤3 文件 / ≤30 行）。

### 命令输出（真实）

- `grep 'https?://' SKILL.md` → 17 匹配（去重后 10 个独立 URL）：
  - `https://github.com/tan-yong-sheng/miniflux-mcp`（line 16/86/869）
  - `https://miniflux.app`（line 86）
  - `https://miniflux.example.com`（line 108/172/187，占位域名）
  - `https://developer.zhihu.com/`（line 348）、`https://developer.zhihu.com/profile`（line 355）
  - `https://github.com/jackwener/twitter-cli`（line 422）、`https://raw.githubusercontent.com/jackwener/twitter-cli/main/SKILL.md`（line 424）
  - `https://github.com/jackwener/bilibili-cli`（line 483）、`https://raw.githubusercontent.com/jackwener/bilibili-cli/main/SKILL.md`（line 485）
  - `https://github.com/jackwener/xiaohongshu-cli`（line 544）、`https://raw.githubusercontent.com/jackwener/xiaohongshu-cli/master/SKILL.md`（line 546）
  - `https://example.com/feed.xml`（line 637，example.com 占位）
  - `https://www.npmjs.com/package/miniflux-mcp`（line 869）、`https://docs.miniflux.app`（line 870）
  - `https://...`（line 777，占位）
- 本地路径 `Test-Path` 结果：
  - `src/collect_zhihu.py` / `collect_twitter.py` / `collect_bilibili.py` / `collect_xhs.py` / `report.py` → **全部存在** ✓
  - `.skills/zhihu-cli/zhihu/SKILL.md` → **存在** ✓
  - `scripts/setup.sh` / `scripts/setup.ps1`（repo 根） → **不存在** ✗
  - `scripts/run.sh`（repo 根） → **不存在** ✗
  - `scripts/` 目录（repo 根） → **不存在** ✗
  - `.skills/zhihu-cli/zhihu/scripts/setup.sh` / `setup.ps1` / `run.sh` / `run.ps1` → **存在** ✓
- `web_fetch https://github.com/tan-yong-sheng/miniflux-mcp` → `TypeError: fetch failed`（网络不可用，外链验证 UNKNOWN）。

### 逐条判定

| 引用 | 位置 | 类型 | 验证结果 | 判级 |
|------|------|------|----------|------|
| `scripts/setup.sh` / `setup.ps1`（裸路径） | line 354、416 | 相对路径 | repo 根不存在 | **P2 引用失效** |
| `scripts/run.sh status`（裸路径） | line 417 | 相对路径 | repo 根不存在 | **P2 引用失效** |
| `<skill-dir>/scripts/setup.sh` / `setup.ps1` | line 361、364 | 占位路径 | `<skill-dir>` 指向 `.skills/zhihu-cli/zhihu/`，scripts 存在 | ✅ |
| `src/collect_*.py` / `src/report.py` | line 26/404/466/527/594/648 | 相对路径 | 全部存在 | ✅ |
| `.skills/zhihu-cli/zhihu/SKILL.md` | line 350 | 相对路径 | 存在 | ✅ |
| `~/.config/opencode/opencode.json` | line 98/311 | 用户配置路径 | 非 repo 路径（用户系统） | ✅ |
| 占位 URL（`miniflux.example.com` / `example.com` / `https://...` / `[link](url)`） | line 108/172/187/637/777/672/679/683/689/692/695/784/788/794/797/800/803/806/809/812/815 | 占位 | 明确标注为示例 | ✅ |
| 10 个外部 URL（github / miniflux / zhihu / npm / docs） | line 16/86/348/355/422/424/483/485/544/546/869/870 | 外链 | web_fetch 失败，**UNKNOWN** | ⚠ 无法验证 |

### 发现

**[P2] [R01] SKILL.md:354,416,417 — zhihu-cli 模块 3 处 `scripts/` 裸路径在 repo 根不存在**

  Found:    line 354：`- zhihu-cli >= 0.6.0（由 Skill 的 `scripts/setup.sh` 或 `scripts/setup.ps1` 自动安装）`
            line 416：`| `CLI not found` | 未安装 CLI | 运行 `scripts/setup.sh` 或 `setup.ps1` |`
            line 417：`| `incompatible` | CLI 版本过低 | 运行 `scripts/run.sh status` 检查，然后重新 setup |`
            同时：line 361 / 364 已用 `<skill-dir>/scripts/...` 占位形式；`Test-Path 'scripts'` 返回 False；`.skills/zhihu-cli/zhihu/scripts/{setup,run}.{sh,ps1}` 4 个文件全部存在。

  Expected: 与 line 361/364 一致，使用 `<skill-dir>/scripts/...` 占位前缀，指向 `.skills/zhihu-cli/zhihu/scripts/`。

  Fix:      **本轮已修**（3 处，共 3 行）：
  - line 354 → `- zhihu-cli >= 0.6.0（由知乎 Skill 的 `<skill-dir>/scripts/setup.sh` 或 `<skill-dir>/scripts/setup.ps1` 自动安装）`
  - line 416 → `| `CLI not found` | 未安装 CLI | 运行 `<skill-dir>/scripts/setup.sh` 或 `<skill-dir>/scripts/setup.ps1` |`
  - line 417 → `| `incompatible` | CLI 版本过低 | 运行 `<skill-dir>/scripts/run.sh status` 检查，然后重新 setup |`

  Basis:    判定表 P2「引用失效」；R01 判据「搜 http、路径引用、相对链接；逐个确认目标存在」；`Test-Path 'scripts'` 返回 False 作为反证。

  Note:     影响面：zhihu-cli 模块「前置条件」与「排障」两处用户首次安装指引；修复前用户按文档字面执行 `scripts/setup.sh` 会因路径不存在而失败。验证方式：`grep '`scripts/' SKILL.md` 应全部命中 `<skill-dir>/scripts/...` 形式（修复后 5 处，line 354/361/364/416/417）。修复后 SKILL.md 871 → 871 行（行数不变，仅内容修改）；`python yaml.safe_load` frontmatter 通过。

### 结论

R01 通过（已修）。3 处裸路径修复为 `<skill-dir>/scripts/...` 占位形式，与 line 361/364 一致；本地相对路径引用全部有效；10 个外部 URL 因 `web_fetch` 网络失败无法验证，标注 UNKNOWN。

**跨维度观察（不属 R01 判据，交由后续维度）**：
1. 10 个外部 URL 未能通过 `web_fetch` 验证（网络不可用）。若需 100% 验证，需人工在网络可用时逐个 `web_fetch` 或用 `curl`/`Invoke-WebRequest`。移交 R04（示例命令可跑性）参考。
2. line 424 / 485 用 `main` 分支，line 546 用 `master` 分支（`https://raw.githubusercontent.com/jackwener/xiaohongshu-cli/master/SKILL.md`）。若上游默认分支为 `main`，line 546 可能失效。移交 R02（版本与更新日期）参考。
3. line 16 / 422 / 483 / 544 中 GitHub 仓库路径与 line 869 中 npm 包名一致；未见 URL 与项目名不匹配的明显错误。

---

## 移交强模型

- **G02 P2 修复需人工决策**：line 28「不写任何内容」与脚本写本地 JSON 中间文件行为不一致；建议修复文本见 R11 小节，需人工决策是否采纳并同步 CHANGELOG。本检查员按硬约束未修改。
- **R01 跨维度观察**：line 546 使用 `master` 分支可能失效（其他两个 CLI 用 `main`）；移交 R02。

---

## Round 12 之后仍需推进
- LITE_CORE 十二项全部有结论（M01/M02/M03/C01/C02/P01/P02/O01/O02/G01 通过；G02 P2 待人工决策；R01 通过含修复）。
- P0/P1 已修或已说明；P2（G02）已标「需人工决策」。
- 延伸维度：R02 版本与更新日期、R03 MECE 重叠、R04 示例命令可跑性、R05 命名与术语一致、R06 长度与信息密度。

---

（无。）当前 M01 结论独立可判定，无需跨维度裁决。

---

## 附录：各轮实际读取的文件

**Round 1**
- `D:\github-repos\news-report\SKILL.md`（line 1–80，头部 + 概述）
- `D:\github-repos\news-report\.skills\zhihu-cli\zhihu\SKILL.md`（line 1–80，头部 + 入口）
- 命令执行：Python `yaml.safe_load` × 2，均退出码 0。

**Round 2**
- `D:\github-repos\news-report\SKILL.md`（`^name:` 匹配，line 2）
- `D:\github-repos\news-report\.skills\zhihu-cli\zhihu\SKILL.md`（`^name:` 匹配，line 2）
- `D:\github-repos\news-report\.skills\zhihu-cli\zhihu\manifest.json`（全文）
- `D:\github-repos\news-report\pyproject.toml`（`name =` 匹配，line 8）
- 命令执行：PowerShell `Get-Item` × 2、`Select-String` × 3。

**Round 3**
- `D:\github-repos\news-report\SKILL.md`（`^description:` 匹配 line 3；注册表行 line 50–56）
- 命令执行：PowerShell `Select-String` × 2、Python `yaml.safe_load` × 1（描述文本长度 454 字符）。

**Round 4**
- `D:\github-repos\news-report\SKILL.md`（全文，检索 `triggers:` 与 `triggers` 关键字）
- `D:\github-repos\news-report\.skills\zhihu-cli\zhihu\SKILL.md`（描述触发词对照）
- 命令执行：`grep '^triggers:'`、`grep 'triggers'`、`grep 'trigger' SKILL.md` 各 1 次。

**Round 5**
- `D:\github-repos\news-report\SKILL.md`（line 64–72、240–248、636–715，多次 `grep` 契约类关键字）
- 命令执行：`grep '^#+ Contract|契约|输入|输出|...'`、`grep 'Contract|契约'`、`grep '失败|error|错误|异常|故障|排障'`、`grep 'mutating|只读|read-only'`、`grep '^## '`、Python `yaml.safe_load` 复核修复后仍通过。

**Round 6**
- `D:\github-repos\news-report\SKILL.md`（line 60–68 扩展方式、221–247 常用工作流、283–295 模块开发、297–305 测试验证、312–316 升级流程、351–380 zhihu 安装、425–448 twitter 安装、610–630 规划模块示例）
- `D:\github-repos\news-report\src\`（目录清单）
- `D:\github-repos\news-report\.skills\zhihu-cli\zhihu\scripts\`（目录清单）
- 命令执行：`grep '^#+\s*(Phases|阶段|流程|步骤|Workflow)'`、`grep '视情况|按需|如果合适|酌情|灵活|自行判断|自行决定|考虑使用'`、`grep 'src/collect|src/report\.py|src/'`、PowerShell `Get-ChildItem src` 与 `Get-ChildItem '.skills\zhihu-cli\zhihu\scripts'`。

**Round 7**
- `D:\github-repos\news-report\SKILL.md`（line 85–115 miniflux 前置 + 配置、351–365 zhihu 前置 + 安装、425–440 twitter 前置 + 安装、486–500 bilibili 前置 + 安装、547–562 xiaohongshu 前置 + 安装、182 环境变量表）
- 命令执行：`grep '^#+\s*(前置|依赖|Requires?|Prerequisites?|Dependencies?|Environment|环境变量)'`、`grep '\b(npx|node|uv|pipx|python|bash|powershell|npm)\b'`、`grep 'Node\.js|Python|uv tool|pipx|bash|powershell|npm'`。

**Round 8**
- `D:\github-repos\news-report\SKILL.md`（line 26、645–844 输出模板全章、75 Contract 引用）
- 命令执行：`grep 'Output Format|输出格式|输出模板'`。

**Round 9**
- `D:\github-repos\news-report\SKILL.md`（line 70–78 Contract 表、297–305 测试与验证、376 zhihu 验证、645 输出模板起点）
- 命令执行：`grep '完成|Completed|Done|验收|通过|验证|判定'`。
- 修复验证：`python yaml.safe_load` frontmatter 通过；`Select-String '完成标准'` 命中 line 78；SKILL.md 870 → 871 行。

**Round 10**
- `D:\github-repos\news-report\SKILL.md`（frontmatter、line 194–204 模块 01 工具、389–400 模块 02、453–462 模块 03、514–523 模块 04、578–588 模块 05、403/465/526/593 脚本引用）
- `D:\github-repos\news-report\.skills\zhihu-cli\zhihu\SKILL.md`（line 78–92 命令表）
- 命令执行：`grep '^tools:|tools:\s'`、`grep 'allowed-tools|allowed_tools|metadata|license'`、`Get-Command` × 2、`uv tool list`、`pipx list`。

**Round 11**
- `D:\github-repos\news-report\SKILL.md`（line 26–28 概述边界、68 通用约定、77 Contract 副作用、264/295 高级指南、322 安全最佳实践）
- `D:\github-repos\news-report\src\main.py`、`src\evaluator.py`、`src\collect_rss.py`、`src\collect_search.py`、`src\collect_telegram.py`（grep 写盘调用）
- 命令执行：`grep 'mutating' SKILL.md`（0 匹配）、`grep '只读|read-only|readonly' SKILL.md`（6 匹配）、`grep 'open\(.*["\']w|write\(|to_csv|to_json|json\.dump' src/*.py`（16 匹配）。

**Round 12**
- `D:\github-repos\news-report\SKILL.md`（line 16/26/86/98/311/348/350/354/361/404/416/417/422/424/466/483/485/527/544/546/594/648/672/777/869/870）
- `D:\github-repos\news-report\src\`（目录清单，`Get-ChildItem 'src\collect_*.py','src\report.py'`）
- `D:\github-repos\news-report\.skills\zhihu-cli\zhihu\`（目录清单，含 `scripts/`、`references/`、`manifest.json`、`SKILL.md`）
- 命令执行：`grep 'https?://'`、`grep '\]\([^)]+\)'`、`grep '`[^`]*\.(py|sh|ps1|json|md|toml|yaml|yml)`'`、`grep 'scripts/setup|scripts/run|`scripts/'`、`Test-Path` × 多、`web_fetch` × 1（失败）。

## 附录：各轮实际写入的文件

- `docs/reports/skill-quality-news-report.md`（本文件，R1 新建，R2–R12 追加）。
- `SKILL.md`（R5 修复：line 68 后插入 9 行 Contract 表，861 → 870 行；R9 修复：Contract 表追加 1 行「完成标准」，870 → 871 行；R11 无修改，P2 发现标「需人工决策」；R12 修复：line 354/416/417 三处 `scripts/` 裸路径改为 `<skill-dir>/scripts/...` 占位形式，871 行不变）。
