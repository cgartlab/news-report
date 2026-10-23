# Changelog

本文件记录 news-report 的所有显著变更。

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本 2.0.0](https://semver.org/lang/zh-CN/)。

---

## [Unreleased]

### Changed

- **发布流程内联（`.github/actions/publish`）**：`publish.yml` 不再调用 `cgartlab/cgartlab-skills` 的 reusable workflow。跨仓库 reusable workflow 只在「调用方与被调用方同为 private」时可用，本仓库一旦转 public（当前 private 仓库的 Actions 因账户账单不可用）发布 job 会直接失败。现改为仓库自带 composite action，与本工作区其余 skill 仓库（cgartlab-search / down / person-profile / quill）保持同一套实现。
- 手动 dispatch 增加 `publish_clawhub` / `publish_skillhub` 单侧补发开关（发布半途失败时只补发另一侧）；SkillHub 侧会自动剔除无扩展名文件（`LICENSE` / `Dockerfile`），License 声明仍保留在 SKILL.md。
- **输出模板真正统一（四条路径共用元信息行）**：🟡 P1 此前只有 `📡 来源`、没有日期，而同一条数据在 🟢 P2 却带日期——v0.9.0 声称的「统一单条模板」实际只覆盖 P2。现在 P0/P1/P2/P3 全部输出 `📡 {来源} · {日期}`。
- **🔵 背景条目可点击**：P3 此前是裸标题 + 来源，读者无法打开；现输出 `[标题](链接)  📡 来源 · 日期`。
- **🟢 P2 条目间空行**：每条是「标题 / 摘要 / 元信息」三行，不留空行会糊成一片。
- **来源多样性上限**：🟢 P2 内同一来源最多 3 条（`report.MAX_PER_SOURCE_P2`），超出降级到 🔵 背景而非丢弃。实测依据：2026-10-21 那次 run 的 P2 共 11 条，AWS 博客独占 4 条、IT之家 5 条。

### Added

- **`src/textclean.py`（中文排版清洗）**：`normalize_cjk_spacing` 删除中文字符之间、中文/全角标点旁的多余空格，删零宽字符，折叠连续空白；保留中文与数字/英文之间的合法空格（`9,500 万台`、`Mac 版 Perplexity`）。采集层（`_strip_noise` 出口）与渲染层（标题、摘要）各过一遍。
- **HTML 去标签按块级/内联区分**（`collect_rss._strip_html`）：内联标签（`span` / `a` / `strong` …）直接删除，块级标签才留一个空格。此前每个标签都被替换成空格，是 `华为 鸿蒙 HarmonyOS`、`万台 ，` 这类脏排版的根因。
- **摘要前置样板清洗**（`collect_rss._strip_noise`）：`感谢…线索投递！`、`IT之家 10 月 20 日消息，`、`业界消息 2026/10/20 青小蛙 `、开头残留的 `。；` 一律删除——它们吃掉 15-20 字摘要预算，信息却已由元信息行承担。正文中间的同形日期不处理。
- 测试 `tests/test_output_polish_2026_10.py` 新增 23 条，覆盖中文排版、内联/块级标签、三类前置样板、「正文日期不被误删」、模板统一、P3 链接与单源上限。

### Fixed

- **`src/evaluator.py` 未通过 `ruff format`**：CI 的 `ruff format --check src/` 会失败。仅格式调整（切片空格、长行换行、print 换行），无行为变化。

---

## [0.9.0] - 2026-10-21 _(无 tag)_

> **一句话概括**：这是一次**输出质量与评估链路重构**更新。P0 判定从「关键词猜测」改为「LLM 语义判定」（人身安全 / 重大技术变革 / 影响历史 / 市场剧烈变动 / 革命性产品）；统一单条模板（标题内嵌真实链接 + 140 字摘要 + 来源）；按高价值兴趣反推剔除低价值内容（明星八卦 / 小道消息 / 星座鸡汤）；修复 `{{ postmeta.* }}` 模板占位符残留。

### Added

- **P0 语义判定（`evaluator.assign_semantic_priorities`）**：最终精选的 20 条在渲染前由 LLM 批量判 P0–P3。P0 只给真正重大的信号，宁缺毋滥：
  - ① 可能危及人身安全；② 重大技术变革；③ 可能影响人类历史的信号；④ 市场剧烈变动信号；⑤ 伟大革命性产品发布
  - 报告层 `assign_priority` 只消费 LLM 结果，不再靠关键词猜（修复「微软数字主权博客因含 critical 被判 P0」）
  - 无 LLM 时的规则兜底保守化：仅「新闻源（雷峰/IT之家/央视/新华…）+ 明确突发词」才 P0；非新闻源（博客/论坛/雪球）一律不因关键词进 P0
- **低价值内容剔除（按高价值反推）**：`rule_score` 增加标题级强负面信号——明星八卦（`明星|八卦|绯闻|恋情|出轨|塌房`）、小道消息（`网传|传闻|爆料|知情人士`）、星座玄学（`星座|运势|占卜|塔罗`）、鸡汤成功学（`心灵鸡汤|成功学|养生秘方`），命中即 `discard`；弱信号（`离婚|疑似|减肥|饭圈`）降分不杀，避免误伤正文提及的科技报道
- **LLM 评估批次输出 priority**：`FILTER_BATCH_TEMPLATE` 增加 `priority: P0/P1/P2/P3` 输出项，dispute 条目在过滤阶段一并获得优先级，不额外增加 API 调用

### Changed

- **统一单条渲染模板（`src/report.py`）**：P0/P1/P2 三条路径统一为「标题（内嵌原文链接）+ 摘要 ≤140 字 + 来源 · 日期」；`_summary_140` 在句子边界截断并加 `…`。P2 从此不再裸标题
- **摘要从 200/300 字统一到 140 字**：每条摘要足够判断是否值得打开，信息密度最大化（Telegram 简报场景）
- **`collect_rss._strip_noise` 增加 `{{...}}` 模板占位符清洗**：修复 `收藏已收藏{{ postmeta.bookmark }}` 残留
- **SKILL.md 输出模板 / 打分细则同步**：P0 语义五标准、单条模板、低价值剔除清单写入文档

### Fixed

- 微软「数字主权」博客（含 critical）不再误判 P0
- 「人人都是产品经理」摘要残留 `{{ postmeta.bookmark }}` / `{{ postmeta.postlike }}`
- P2 条目裸标题无摘要、无链接

### 测试

- `tests/test_quality_2026.py` 新增 15 条：低价值规则（含「正文提及结婚不误杀」）、占位符清洗、140 字截断、priority 兜底与聚合标题限位。`ruff` / `mypy` / `pytest` 全绿（23 passed）

---

## [0.8.0] - 2026-10-17 _(无 tag)_

### Added

- **新增 Miniflux 采集器（模块 01 · `src/collect_miniflux.py`）——一次 API 请求覆盖全部已订阅 feed**：走 Miniflux REST API 的 `/v1/entries`，替代「逐个抓 RSS 源」。实测该实例有 **85 个订阅源**，而 `config/rss-sources.json` 只有 27 个启用源，信息源数量大幅提升。
  - 认证：优先 `MINIFLUX_API_KEY`（作 Basic Auth 密码，用户名任意，Miniflux 官方推荐）；无 Key 时退回 `MINIFLUX_USERNAME` / `MINIFLUX_PASSWORD`
  - 时间窗 `miniflux_hours`（默认 24h，走 `published_after`）、总量上限 `miniflux_limit`（默认 100）、分类过滤 `miniflux_categories`、**单源上限 `miniflux_per_feed_limit`（默认 5）**
  - 输出字段与其它采集器一致（`id` 前缀 `mf_`、`source_type: "rss"`），下游评估/去重/渲染无需改动
  - **`miniflux_per_feed_limit` 不是可选优化**：实测不加限制时最终 300 条里 IT之家 独占 182 条；设 5 后降到 5，覆盖来源数从 14 升到 27。高流量单源（IT之家 100+/天）会淹没其他所有源
  - SKILL.md 模块 01 改为「两条接入路径」：采集器（pipeline）+ MCP 服务器（对话侧），并说明为何 pipeline 不走 MCP（N 次往返 vs 1 次）

### Fixed

- **RSS 日期解析：`Invalid Date` 被当成有效日期输出**：`_normalize_date()` 的兜底分支 `return date_str[:10]` 会把上游的 `Invalid Date` 截成 `Invalid Da`，直接印在简报里。上游数据源本身就坏（RSSHub 的豆瓣路由直接返回 `<pubDate>Invalid Date</pubDate>`），但解析器不该原样透传。
  - 现先识别 `invalid` / `unknown` / `n/a` / `none` / `null` / `undefined` 等无效值返回空串
  - 兜底只接受真正以日期开头的字符串（`^\d{4}-\d{2}(-\d{2})?`），`2007-06`（豆瓣出版年月）这类既有行为保留
  - 16 条用例覆盖中英文日期、RFC 822、ISO 8601、相对日期与各类垃圾值

> **一句话概括**：这是一次**新采集能力 + 默认行为变化**更新。新增 x-browser 模块——通过已登录的浏览器（Edge CDP）深度采集 X/Twitter 时间线；同时采集源改为按开关运行，默认只启用 `rss` + `zhihu`。**如需采集 X / 搜索 / Telegram / B 站 / 小红书，请把 `config/config.json` 的 `enabled_sources` 对应项设为 `true` 并配好凭证；zhihu 模块已从 `zhihu-cli` 迁移到 `zhihu-search`（安装方式改为 `uv tool install zhihu-search`）。**

### Added

- **现在可以采集 X/Twitter 时间线了（新增模块 06 · `x-browser`，需先通过已登录浏览器的 Edge CDP 接入）**：与模块 03（twitter-cli）互补——支持 For You / Following / 自定义 Timeline 标签、深度滚动（不受 `--max` 限制）、转帖归属（`retweeted_by` 字段）与按推文 ID 去重。
  - `src/x_cdp.py`：零第三方依赖的 CDP 客户端（HTTP target 发现 + 手写最小 RFC 6455 WebSocket），支持 `Runtime.evaluate` / `Page.navigate` / `Input.dispatchMouseEvent`（滚动），可作 CLI 使用（`list` / `eval` / `nav`）
  - `src/collect_x_browser.py`：时间线采集器，输出与其他模块一致的标准 item 结构；CDP 不可达或无 x.com 页面时优雅跳过
  - `bin/edge-cdp.ps1` / `bin/edge-cdp.sh`：跨平台浏览器启动器（本地代理 + 独立 profile + CDP 端口），幂等且支持 `-Stop` / `--stop`
  - 环境变量：`X_BROWSER_CDP_ENDPOINT`（默认 `http://127.0.0.1:9222`）、`X_BROWSER_TIMELINE`（`following` / `for_you` / `both`）；`config/config.json` 新增 `enabled_sources.x_browser`、`x_browser_timeline`、`x_browser_scroll_rounds`
- **规划中占位模块重编号**：`rss-http` 06 → **07**，`news-api` 07 → **08**（注册表与「扩展模块示例」同步更新）
- **版本信息口径同步**：SKILL.md 版本信息补记 v0.7.0 / v0.7.1（此前 CHANGELOG 已到 0.7.1 而 SKILL.md 停留在 v0.6.1）

---

### Changed

- **模块 02 迁移：`zhihu-cli` → `zhihu-search`**：PyPI 上 `zhihu-cli` 停在 v1.2.0（2020），锁死 `lxml==4.3.4`，Python 3.10+ 编译失败已无法安装。本项目改用 [zhihu-search](https://github.com/klarkxy/zhihu-search) v2.x（2026 维护中，知乎开放平台官方平替），支持站内搜索 / 全网搜索 / AI 直答 / 热榜 / 问题推荐 / 回答摘要 / 知识库 / PDF / PPT / OAuth，并提供 MCP stdio 形态。
  - `src/collect_zhihu.py` 已重写：调用 `zhihu-search search --scope zhihu|web`、`zhihu-search trending`、`zhihu-search --check-token`；解析新版 JSON 结构（`{"success", "kind", "data": {"Items": [...]}}`）
  - 新增环境变量 `ZHIHU_SEARCH_CLI_PATH`（canonical）；保留 `ZHIHU_CLI_PATH` 作为兼容别名
  - `.env.example` 同步更新 Zhihu 章节
  - 安装方式：`uv tool install zhihu-search`（旧 `scripts/setup.sh` 已不适用）

- **采集源按开关运行**：`config/config.json` 新增 `enabled_sources` 和 `disabled_reasons` 字段，`src/main.py` 的 `step_collect` 会按开关跳过未启用的源，并在日志中打印跳过原因。默认只启用 `rss` + `zhihu`，其余源（`search` / `telegram` / `twitter` / `bilibili` / `xhs`）默认禁用——要么凭证缺失，要么依赖未就绪。老板按需打开：填入 `.env` 里的凭证或修好对应 CLI，把 `enabled_sources.X = true` 即可。
- **SKILL.md 模块状态列更新**：模块 03 / 04 / 05 状态从"✅ 可用（需鉴权）"改为"⏸️ 默认禁用"，附带默认关闭原因；模块 06 / 07 仍为占位。

- **`docs-check.yml` 的版本一致性检查从 warning 升级为硬门禁**：原先只发 `::warning::`，且只比较 SKILL.md / AGENTS.md / CHANGELOG 三处正文的首个 `vX.Y.Z`——frontmatter 与 pyproject.toml 完全没被检查，所以「三处版本不一致但 CI 绿」可以长期存在。现在检查 5 处（SKILL.md frontmatter、SKILL.md 正文、pyproject.toml、CHANGELOG 最新段、AGENTS.md 正文），任一缺失或不一致即 `exit 1`。

### Fixed

- 修复 `src/collect_zhihu.py` 在 Python 3.10+ 环境下无法调用的问题（旧版依赖 `zhihu-cli auth set` 与 `zhihu-cli status`，两者在新版 CLI 中已不存在）
- 修复 JSON 输出解析：`zhihu-search` 部分子命令会在 stdout 尾部追加 `===` 分隔符，新版解析器带容错 fallback
- 修复 pipeline 崩溃：`collect_bilibili.py` 在响应结构上假设 dict 但实际返回 list 导致 `AttributeError`——现在通过禁用 bilibili 源避免，`enabled_sources.bilibili = true` 前需先修脚本
- **修复 SKILL.md frontmatter 版本号停留在 0.7.1**：`0961515`（"merge: 同步 main 并将版本统一为 0.8.0"）只更新了正文「版本信息」段落，未改 frontmatter，导致 `release.yml` 的「Check version consistency」在打 `v0.8.0` tag 时必然失败。现统一为 `0.8.0`。
- **`tests/` 此前从未被 CI 执行**：仓库有 `tests/test_x_cdp.py`（8 个测试，覆盖 RFC 6455 握手校验、掩码、分片、非 JSON 消息等），但 `lint.yml` 只跑 ruff 与 mypy，`dev` extra 也不含 pytest。现新增 `test` job，并把 `pytest>=8.0` 补进 `dev` extra。

---

## [0.7.0] - 2026-10-07 _(无 tag)_

> **一句话概括**：这是一次**简报质量与去重机制**更新。每条进入简报的新闻现在必须带 5 个元数据字段（Significance / Development Status / Key Entities / Sentiment / Data Quality），同一事件 24 小时内跨信源自动去重（冷却机制），输出模板明确了长版深度分析与日常简报的分工。**你不需要做任何事——本版为纯增量更新。**

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

## [0.6.1](https://github.com/cgartlab/news-report/compare/v0.6.0...v0.6.1) - 2026-09-18

> **一句话概括**：这是一次**文档契约与可用性修正**。SKILL.md 新增输入/输出/失败行为/副作用/完成标准五项契约，并修复 zhihu-cli 模块的路径引用（此前按文档字面执行会失败）。**你不需要做任何事——纯文档修正。**

### Added

- **SKILL.md Contract 表**：新增输入/输出/失败行为/副作用/完成标准 5 项契约定义，集中声明 skill 的调用约定与完成判定条件。
- **只读边界表述修正**：概述「不写任何内容」改为「不写业务输出文件（内部脚本会写本地中间数据文件，如 JSON 采集结果）」，与 Contract 表及通用约定第 3 条一致。

### Fixed

- **zhihu-cli 模块路径引用**：line 354/416/417 三处 `scripts/setup.sh` 等裸路径改为 `<skill-dir>/scripts/...` 占位形式，与 line 361/364 一致。修复前用户按文档字面执行会因路径不存在而失败。

---

## [0.6.0](https://github.com/cgartlab/news-report/compare/v0.5.0...v0.6.0) - 2026-09-18

> **一句话概括**：新增**小红书采集能力**（模块 05 · `xiaohongshu-cli`），支持笔记搜索、热门榜、推荐 Feed。**需要采集小红书请配置 `XHS_CLI_PATH`（或让 CLI 自动检测）；不需要该源则无需任何操作。**

### Added

- **现在可以采集小红书内容了（新增模块 05 · `xiaohongshu-cli`，需配置 `XHS_CLI_PATH` 或登录）**：通过 [jackwener/xiaohongshu-cli](https://github.com/jackwener/xiaohongshu-cli) 接入笔记搜索、热门榜、推荐 Feed、用户资料与话题。Apache 2.0 开源。
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

## [0.5.0](https://github.com/cgartlab/news-report/compare/v0.4.0...v0.5.0) - 2026-09-18

> **一句话概括**：新增 **Twitter/X 与 B 站采集能力**（模块 03 · `twitter-cli`、模块 04 · `bilibili-cli`）。**采集 Twitter 请配置 `TWITTER_CLI_PATH` / `TWITTER_AUTH_TOKEN` / `TWITTER_CT0`，采集 B 站请配置 `BILIBILI_CLI_PATH`；不需要这些源则无需任何操作。**

### Added

- **现在可以采集 Twitter/X 内容了（新增模块 03 · `twitter-cli`，需配置 `TWITTER_CLI_PATH` 或登录）**：通过 [jackwener/twitter-cli](https://github.com/jackwener/twitter-cli) 接入推文搜索、时间线、书签与用户资料。Apache 2.0 开源。
  - `src/collect_twitter.py`：Twitter CLI 采集脚本，支持推文搜索（`search`）、时间线采集（`feed`），无鉴权时优雅跳过。
  - CLI 路径自动检测：`TWITTER_CLI_PATH` → `config.json` → 已知路径 → PATH 搜索。
  - 集成到 `main.py` 的 `step_collect()`，作为第 5 个采集源。
- **现在可以采集 B 站内容了（新增模块 04 · `bilibili-cli`，需配置 `BILIBILI_CLI_PATH`；部分命令无需鉴权）**：通过 [jackwener/bilibili-cli](https://github.com/jackwener/bilibili-cli) 接入视频搜索、热门榜、排行榜与用户资料。Apache 2.0 开源。
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

## [0.4.0](https://github.com/cgartlab/news-report/compare/v0.3.0...v0.4.0) - 2026-09-18

> **一句话概括**：新增**知乎采集能力**（模块 02 · `zhihu-cli` 知乎开放平台 CLI），支持社区/全网搜索与热榜。**需要采集知乎请配置 `ZHIHU_CLI_PATH` 与 `ZHIHU_ACCESS_SECRET`（或登录）；不需要该源则无需任何操作。**

### Added

- **现在可以采集知乎内容了（新增模块 02 · `zhihu-cli` 知乎开放平台 CLI，需配置 `ZHIHU_CLI_PATH` 或登录）**：通过知乎官方 CLI 接入社区搜索、全网搜索、热榜、AI 直答、问题推荐与回答摘要。
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

## [0.3.0](https://github.com/cgartlab/news-report/compare/v0.2.0...v0.3.0) - 2026-09-18

> **一句话概括**：简报**输出格式正式定义**——7 个结构化章节（TOP SIGNAL → 紧急 → 关注 → 常规 → 背景 → 影响分析 → 来源统计），含排版原则与跨行业影响分析指南。**你不需要做任何事——输出格式从「下一阶段设计」变为正式可用，生成简报时自动生效。**

### Added

- **输出模板正式定义**（SKILL.md 新增「输出模板」章节）：完整定义新闻简报的输出格式，包含 7 个结构化章节——TOP SIGNAL（🎯 当日最重要信号）、紧急（🔴 P0）、关注（🟡 P1）、常规（🟢 P2）、背景（🔵 P3）、影响分析（📊 跨行业传导 + 职业风险矩阵）、来源统计。
- **排版设计原则**：信息密度最大化（每条一行核心 + 一行洞察 + 一行元数据）、阅读体验最优化（视觉层级 🎯→🔴→🟡→🟢→🔵，可扫描，💡 洞察高亮）、节奏从冲击到沉静的叙事弧。
- **影响分析指南**：跨行业传导路径（技术→直接→次生影响）+ 职业风险矩阵（🔴 高危/🟡 中危/🟢 安全，含时间框架）。
- **完整示例**：SKILL.md 内嵌完整示例输出，可直接参考排版。

### Changed

- **SKILL.md 输出格式声明**：从「下一阶段设计」更新为「见输出模板章节」，v0.3.0 起正式可用。
- **AGENTS.md 约束更新**：「输出格式未设计」→「输出格式已定义」，后续修改需遵循模板。

---

## [0.2.2] - 2026-09-18 _(无 tag)_

> **一句话概括**：这是一次**工程治理升级**：补齐 GitHub Actions（lint / 自动发布 / 文档检查）、`pyproject.toml`、pre-commit hooks 与仓库治理文件（CODEOWNERS、PR/Issue 模板、CONTRIBUTING.md），README 专业化重写。**对使用者无行为变化，你不需要做任何事。**

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

## [0.2.1] - 2026-09-11 _(无 tag)_

> **一句话概括**：这是一次**文档修正与深化**：修复工具签名、`searchEntries` 参数表与状态过滤值的误导性描述，移除编造内容，并新增「高级指南」章节。**你不需要做任何事——纯文档更新。**

### Fixed

- **工具签名与实际调用方式不一致**：将「可用工具」表的签名从 `listCategories(counts?)` 等改为对象参数形式 `listCategories({ counts? })`，与示例保持一致，避免误导。
- **searchEntries 参数表遗漏**：补全 `changed_before` / `changed_after`（更新时间过滤）与 `before_entry_id` / `after_entry_id`（游标分页）参数，同步上游 miniflux-mcp v0.0.12 的实际支持字段。
- **状态过滤值补充**：将 `status` 参数示例从 `"read,unread"` 扩展为 `"read,unread,removed"`，涵盖 Miniflux API 允许的全部状态。
- **审查修正**：移除编造的 2FA 排障条目，修正「默认只返回未读」的错误表述，澄清 MCP 无工具响应缓存机制，统一 opencode 与 User-Agent 的 Unicode 连字符混用，消除扩展模块示例中假设工具名被误用的风险。

### Documentation

- **新增高级指南章节**：在 SKILL.md 中新增「高级指南」，包含架构设计详解、模块开发指南、测试与验证、部署与维护、安全最佳实践、性能优化建议、故障排查进阶、扩展模块示例等专业内容。
- **完善模块化架构文档**：强化模块开发规范与最佳实践，为未来模块扩展提供清晰指引。
- **AGENTS.md 文档升级**：v1 → v3——新增「启动清单」「典型任务与操作原则」「质量门禁」章节，强化版本三处同步约束，更新文件地图与版本段。

## [0.2.0](https://github.com/cgartlab/news-report/compare/v0.1.0...v0.2.0) - 2026-09-06

> **一句话概括**：这是一次**更名与重新定位**：`miniflux-mcp-skill` → **`news-report`**，从「把 Miniflux 接入 AI Agent」扩展为「模块化信息源驱动的新闻采集 Skill」。**如果你在用旧版，请改用 `news-report` 名称触发；Miniflux 模块的全部集成内容原样保留。**

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

> **一句话概括**：**首个版本**：将 Miniflux RSS 阅读器经 `miniflux-mcp` MCP 服务器接入 AI Agent（前置条件、配置方案 A/B、可用工具、`searchEntries` 参数表、常用工作流、排障）。**这是初始发布，按 SKILL.md 配置即可使用。**

### Added

原 **miniflux-mcp-skill** 初始发布：

- `SKILL.md` — 将 Miniflux RSS 阅读器经 `miniflux-mcp` MCP 服务器接入 AI Agent：前置条件、MCP 服务器配置（方案 A：npx 直接运行；方案 B：本地安装 + Basic Auth 补丁）、`MINIFLUX_*` 环境变量表、可用工具（listCategories / listFeeds / searchFeedsByCategory / resolveId / searchEntries）、searchEntries 参数表、常用工作流、排障、维护提示。
- `README.md` — 项目简介与使用方式。
- `LICENSE` — CC BY-NC-SA 4.0。
- Git 初始提交与 `v0.1.0` tag。
