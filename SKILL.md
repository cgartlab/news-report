---
name: news-report
version: 0.7.1
description: >-
  Modular news-gathering skill that retrieves news and articles across pluggable
  information sources (Miniflux RSS via the miniflux-mcp MCP server is module 01),
  so you can read RSS feeds, check subscriptions, search articles and prepare
  material for a news briefing directly from conversation; trigger when the user
  asks to read RSS / check feeds / search articles / gather news-briefing material,
  or mentions "Miniflux", "RSS", "feeds", "订阅", "新闻", "简报".

metadata:
  kind: skill
---

# news-report

## 概述

news-report 是一个以**模块化信息源**驱动的新闻采集（news-gathering）Skill：每个信息源是一个独立模块，Skill 负责编排与检索。当前已可用模块为 **模块 01 · Miniflux RSS**（经 [miniflux-mcp](https://github.com/tan-yong-sheng/miniflux-mcp) MCP 服务器接入，完整保留原 miniflux-mcp-skill 的集成细节，见下文）；后续可扩展 RSS 直取（`rss-http`）、News API（`news-api`）等来源（规划中）。本 Skill 在 agent 中按名称 **`news-report`** 加载。

**核心能力**（当前由模块 01 提供，未来随模块扩展叠加）：

- 跨模块化信息源检索新闻 / 文章（当前可用源：Miniflux）
- 列出分类与订阅源，查看未读 / 文章计数
- 按分类、订阅源或关键词搜索文章（全文搜索）
- 浏览未读、星标文章，支持分页与排序
- 模糊解析名称 / 数字 ID 到 `category_id` / `feed_id`

> **输出格式**：见下文「输出模板」章节（v0.3.0 正式定义）。Skill 执行时按该模板生成新闻简报；Agent 直接路径由 Agent 按模板排版，脚本路径由 `src/report.py` 自动排版。

**边界**：news-report 当前**只读**——仅从各信息源检索数据，不创建或修改订阅源、不标记文章、不写业务输出文件（内部脚本会写本地中间数据文件，如 JSON 采集结果；详见「通用约定」第 3 条与 Contract 表）。

## 信息源模块化架构

news-report 将每个信息源封装为独立模块，避免与单一服务绑定。本仓库既是 Skill 指令本体（SKILL.md），也是各信息源模块的登记处。

### 模块约定

每个模块登记以下要素；规划中模块可暂缺「可用检索能力 / 配置项」，但**必须标注状态**：

| 要素 | 说明 |
|------|------|
| module id / 名称 | 全仓库唯一，小写短横线命名（如 `miniflux`） |
| 数据访问方式 | MCP 服务器 / HTTP API / 直接抓取 RSS |
| 可用检索能力 | 该源真实支持的查询原语（按分类 / 源 / 关键词 / 时间 / 状态过滤等） |
| 配置项 | 一律走本地环境变量，命名形如 `<MODULE>_*`（见「通用约定」） |
| 状态 | `可用` / `规划中` |

### 信息源注册表

| 模块 | 数据访问 | 可用检索能力 | 配置项（环境变量） | 状态 |
|------|----------|--------------|--------------------|------|
| 模块 01 · `miniflux`（Miniflux RSS，经 miniflux-mcp MCP） | MCP 服务器 | 分类 / 订阅源浏览、全文搜索、未读 / 星标、分页排序（详见下节） | `MINIFLUX_BASE_URL`、`MINIFLUX_TOKEN`、`MINIFLUX_USERNAME`、`MINIFLUX_PASSWORD` | ✅ 可用（默认启用） |
| 模块 02 · `zhihu-search`（知乎开放平台 CLI + MCP） | CLI / MCP | 知乎搜索（站内/全网）、AI 直答、热榜、问题推荐、回答摘要、知识库、PDF、PPT、OAuth（详见下节） | `ZHIHU_SEARCH_CLI_PATH`、`ZHIHU_ACCESS_SECRET` | ✅ 可用（默认启用） |
| 模块 03 · `twitter-cli`（Twitter/X CLI） | CLI 二进制 | 推文搜索、时间线、书签、用户资料、话题标签（详见下节） | `TWITTER_CLI_PATH`、`TWITTER_AUTH_TOKEN`、`TWITTER_CT0` | ⏸️ 默认禁用（未认证） |
| 模块 04 · `bilibili-cli`（Bilibili CLI） | CLI 二进制 | 视频搜索、热门榜、排行榜、用户资料、动态（详见下节） | `BILIBILI_CLI_PATH` | ⏸️ 默认禁用（收集脚本有 bug） |
| 模块 05 · `xiaohongshu-cli`（小红书 CLI） | CLI 二进制 | 笔记搜索、热门榜、推荐 Feed、用户资料、话题（详见下节） | `XHS_CLI_PATH` | ⏸️ 默认禁用（未认证） |
| 模块 06 · `rss-http`（直接抓取 RSS / Atom 源，示例占位） | HTTP | 待下阶段定义 | 待下阶段定义 | ⏳ 规划中 |
| 模块 07 · `news-api`（NewsAPI / NewsData.io 等聚合 API，示例占位） | HTTP API | 待下阶段定义 | 待下阶段定义 | ⏳ 规划中 |

> **默认启用的源**（`config/config.json` → `enabled_sources`）：`rss`、`zhihu`。其余源在默认配置中禁用，日志会打印跳过原因（`disabled_reasons`）。老板按需打开：填入 `.env` 里的凭证或修好对应 CLI，把 `enabled_sources.X = true` 即可。
>
> **默认关闭的源及原因**：
> - `search`：本机 SearXNG 8099 未开，改用 MCP `mcp__cgartlab__searxng_mcp__searxng_web_search` 或起 Docker 实例
> - `telegram`：`.env` 里 `TG_HISTORY_SCRIPT` 未配置
> - `twitter`：`TWITTER_AUTH_TOKEN` / `TWITTER_CT0` 未设置（未认证）
> - `bilibili`：`src/collect_bilibili.py` 在响应结构上崩溃（list vs dict 假设错误），待修
> - `xhs`：`xhs login` 未执行（未认证）

> 模块 06 / 07 **仅为架构示例占位**：当前不存在对应的工具、命令或脚本，检索能力与配置项一律待下阶段设计；本版不得向用户声称可调用它们，也不得在回复中伪造其工具名。

### 扩展方式

后续新增信息源时：① 在注册表登记一行并标注状态；② 在 SKILL.md 增加对应模块章节（结构对齐模块 01）；③ 新增脚本 / 配置须给出可复制的命令并注明平台；④ 同步更新 CHANGELOG。规划中模块只占位、不预写实现细节。

## 通用约定

1. **密钥策略**：API key / token 一律存放在本地环境变量（shell profile、agent 运行时 env 或本地密钥管理器），示例统一用 `${VAR}` 占位，**绝不硬编码真实密钥**，也不得把密钥写入任何输出文件、配置样本或提交历史。配置文件中的 `env` 段引用本地环境变量（见模块 01 的 MCP 配置示例）。
2. **终端示例约定**：凡需在终端执行的操作，均给出**可直接复制执行**的命令 / 脚本，并注明所需平台（Linux / macOS，或 Windows PowerShell）；平台差异处分别给出写法。
3. **只读边界（当前版本）**：news-report 只做信息采集与检索，不修改任何信息源的数据（不创建 / 修改订阅、不标记已读 / 星标、不发布内容），也不生成业务输出文件。

## Contract（输入 / 输出 / 失败行为 / 副作用）

| 契约项 | 说明 |
|--------|------|
| 输入 | 用户自然语言指令；可选环境变量（详见各模块「前置条件」与「环境变量」小节） |
| 输出 | 按「输出模板」章节（v0.3.0 正式定义）生成新闻简报 |
| 失败行为 | 认证/凭据失败、网络/源不可用见各模块「排障」小节与「高级指南 → 故障排查进阶」 |
| 副作用 | 当前版本**只读**：不创建/修改订阅、不标记已读/星标、不发布内容、不写业务输出文件（详见「通用约定」第 3 条） |
| 本地中间文件 | 采集脚本会将 JSON 数据写入本地文件（如 `src/main.py` → `items_file`）；最终报告由 Agent 排版，不写业务输出文件 |
| 完成标准 | 生成的新闻简报符合「输出模板」章节的完整结构与优先级判定；至少 1 个信息源模块返回非空数据；用户请求的信息源均可达时，简报覆盖全部请求源 |

---

## 模块 01：Miniflux（原 miniflux-mcp-skill 全部内容）

> 本节完整保留原 miniflux-mcp-skill 的集成内容。其中上游 npm 包名 `miniflux-mcp`、MCP 服务器名 `miniflux-mcp`、`MINIFLUX_*` 环境变量与本地安装目录 `~/.config/opencode/miniflux-mcp-server` 均属本模块配置，**保持不变**。

将 [Miniflux](https://miniflux.app) RSS 阅读器接入 AI Agent：通过 [miniflux-mcp](https://github.com/tan-yong-sheng/miniflux-mcp) MCP 服务器，在对话中直接浏览分类与订阅源、搜索文章、查看未读与星标，无需切换到浏览器。

### 前置条件

- 一个可访问的 Miniflux 实例（自托管或托管），且已登录
- Node.js **>= 18.17**（miniflux-mcp 依赖全局 `fetch`）
- 在 opencode 中注册 miniflux-mcp MCP 服务器（见下）

### 配置 MCP 服务器

#### 方案 A：npx 直接运行（推荐）

miniflux-mcp 仅支持 `X-Auth-Token` API Token 认证，这是最简单的方式。在 `~/.config/opencode/opencode.json` 的 `mcp` 段添加：

```json
{
  "mcp": {
    "miniflux-mcp": {
      "type": "local",
      "command": ["npx", "-y", "miniflux-mcp"],
      "enabled": true,
      "env": {
        "MINIFLUX_BASE_URL": "https://miniflux.example.com",
        "MINIFLUX_TOKEN": "${MINIFLUX_TOKEN}"
      }
    }
  }
}
```

> `MINIFLUX_BASE_URL` 填你的实例地址（此处为占位域名）；`${MINIFLUX_TOKEN}` 引用本地环境变量中的 Token —— 若你的运行时配置不支持 `${VAR}` 展开，可在本地文件中填入真实值，但该文件属于本地配置，**不得提交或外发**。`command` 必须是字符串数组；`type` 必填（此处为 `local`）。`npx` 每次启动会自动获取 npm 最新版；如需固定版本，改用 `["npx", "-y", "miniflux-mcp@0.0.12"]`。

#### 方案 B：本地安装 + Basic Auth 补丁（可选）

部分 Miniflux 实例或用户偏好使用用户名 / 密码（Basic Auth）而非 API Token。上游包不支持 Basic Auth，需要对本地安装的 `dist/server.js` 打补丁。

Linux / macOS（Windows 可在 Git Bash 中执行同样命令）：

```bash
mkdir -p ~/.config/opencode/miniflux-mcp-server
cd ~/.config/opencode/miniflux-mcp-server
npm install miniflux-mcp
```

编辑 `~/.config/opencode/miniflux-mcp-server/node_modules/miniflux-mcp/dist/server.js`，替换 `getEnv()` 与 `apiRequest()`：

```javascript
// 替换 getEnv()
function getEnv() {
    const baseUrl = process.env.MINIFLUX_BASE_URL || "";
    const token = process.env.MINIFLUX_TOKEN || undefined;
    const username = process.env.MINIFLUX_USERNAME || undefined;
    const password = process.env.MINIFLUX_PASSWORD || undefined;
    if (!baseUrl) {
        throw new Error("MINIFLUX_BASE_URL is required");
    }
    return { baseUrl: baseUrl.replace(/\/$/, ""), token, username, password };
}

// 替换 apiRequest()
async function apiRequest(path, init) {
    const { baseUrl, token, username, password } = getEnv();
    const url = `${baseUrl}${path}`;
    const headers = new Headers(init?.headers || {});
    if (token)
        headers.set("X-Auth-Token", token);
    else if (username && password) {
        const creds = Buffer.from(`${username}:${password}`).toString("base64");
        headers.set("Authorization", `Basic ${creds}`);
    }
    headers.set("accept", "application/json");
    const http = createHttpClient();
    return http(url, { ...init, headers });
}
```

随后把 MCP `command` 指向补丁后的文件（Windows 示例，按你的用户名替换 `YOUR_USER`）：

```json
{
  "mcp": {
    "miniflux-mcp": {
      "type": "local",
      "command": ["node", "C:\\Users\\YOUR_USER\\.config\\opencode\\miniflux-mcp-server\\node_modules\\miniflux-mcp\\dist\\server.js"],
      "enabled": true,
      "env": {
        "MINIFLUX_BASE_URL": "https://miniflux.example.com",
        "MINIFLUX_USERNAME": "${MINIFLUX_USERNAME}",
        "MINIFLUX_PASSWORD": "${MINIFLUX_PASSWORD}"
      }
    }
  }
}
```

Linux / macOS 使用：`"command": ["node", "/home/YOUR_USER/.config/opencode/miniflux-mcp-server/node_modules/miniflux-mcp/dist/server.js"]`

### 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `MINIFLUX_BASE_URL` | ✅ | Miniflux 实例地址，**不含** `/v1`（服务器内部追加）。示例：`https://miniflux.example.com` |
| `MINIFLUX_TOKEN` | ⚠️ | API Token（Miniflux 设置 → API Keys 生成）。方案 A 必须 |
| `MINIFLUX_USERNAME` | ⚠️ | Basic Auth 用户名（方案 B，与 TOKEN 二选一） |
| `MINIFLUX_PASSWORD` | ⚠️ | Basic Auth 密码（与 USERNAME 搭配使用） |

> 认证优先级：`MINIFLUX_TOKEN` > `MINIFLUX_USERNAME` + `MINIFLUX_PASSWORD`。两者都配置时，Token 优先。

### 可用工具

每个工具接受一个参数对象，属性如下表所示（`?` 表示可选）。

| 工具 | 说明 |
|------|------|
| `listCategories({ counts? })` | 列出所有分类。`counts: true` 附带未读 / 文章计数（需 Miniflux 2.0.46+） |
| `listFeeds()` | 列出全部订阅源（含所属分类） |
| `searchFeedsByCategory({ category_id, query? })` | 在指定分类内按标题 / 站点 URL / 订阅 URL 过滤订阅源（不区分大小写） |
| `resolveId({ query, limit? })` | 按名称或数字 ID 模糊匹配分类与订阅源 |
| `searchEntries({ ... })` | 全局全文搜索，或按 `category_id` / `feed_id` 限定范围 |

#### searchEntries 参数

| 参数 | 说明 |
|------|------|
| `search` | 全文关键词 / 短语。**不支持** `AND` / `OR` 等布尔运算符 |
| `category_id` / `feed_id` | 限定搜索范围（可选） |
| `status` | 状态过滤，逗号分隔多值，如 `"read,unread,removed"` |
| `starred` | 仅星标文章（布尔） |
| `limit` / `offset` | 分页 |
| `order` | 排序字段：`id`、`status`、`published_at`、`category_title`、`category_id` |
| `direction` | `asc` / `desc` |
| `before` / `after` | 创建时间过滤（Unix 秒或 `YYYY-MM-DD` / ISO 日期） |
| `published_before` / `published_after` | 发布时间过滤（同上） |
| `changed_before` / `changed_after` | 更新时间过滤（Unix 秒或 `YYYY-MM-DD` / ISO 日期） |
| `before_entry_id` / `after_entry_id` | 游标分页过滤（基于 entry ID） |

### 常用工作流

#### 按分类查看未读文章

```
listCategories({ counts: true })
→ searchEntries({ category_id: 14, status: "unread", limit: 10 })
```

#### 找到某个订阅源并浏览文章

```
resolveId({ query: "Hacker News" })
→ searchEntries({ feed_id: 42, limit: 5 })
```

#### 按主题搜索文章

```
searchEntries({ search: "Rust programming", status: "unread", limit: 10 })
```

#### 浏览星标文章

```
searchEntries({ starred: true, limit: 10 })
```

### 排障

| 问题 | 解决 |
|------|------|
| `access unauthorized` | 检查凭据。Token 认证失败时可改用方案 B 的 Basic Auth |
| `404 page not found` | 确认 `MINIFLUX_BASE_URL` **不含** `/v1`，服务器会自行追加 |
| `Cannot find package '@modelcontextprotocol/sdk'` | 在服务器目录执行 `npm install` 补装依赖 |
| 服务器无法启动 | 确认 Node.js >= 18.17，并检查 `command` 路径是否正确 |
| 方案 B 升级后 Basic Auth 失效 | `npm update` 会覆盖补丁，需重新执行打补丁步骤 |

## 维护提示

- 本仓库由 `miniflux-mcp-skill` 于 v0.2.0 更名重定位为 `news-report`（当前版本 v0.6.0）；后续新增 / 修改模块请遵守「信息源模块化架构」与「通用约定」，并同步 CHANGELOG。
- **模块 01 专属**：方案 B 的 Basic Auth 补丁是本地改动，**不随 npm 包分发**；升级 `miniflux-mcp` 后必须重新打补丁。
- **模块 01 专属**：上游 miniflux-mcp 为只读服务器，且只支持 API Token；如上游后续原生支持 Basic Auth，可放弃方案 B。
- 若不确定搜索意图（`search` 是关键词还是某个订阅源名称），先向用户澄清，避免误判。

## 高级指南

### 架构设计详解

news-report 的模块化架构遵循**单一职责**与**接口隔离**原则：

1. **Skill 编排层**：负责解析用户意图、选择合适的信息源模块、协调跨模块检索（如未来支持多源聚合）。
2. **模块适配层**：每个信息源模块实现统一的检索接口，将源特定的 API / 协议转换为 Skill 内部可用的数据模型。
3. **MCP 传输层**：对于通过 MCP 服务器接入的信息源（如模块 01），Skill 依赖宿主（如 Claude Desktop、opencode）的 MCP 客户端进行通信。

这种分层设计使得：
- **可插拔**：新增信息源只需实现模块适配层，无需改动 Skill 核心。
- **可替换**：同一类信息源（如 RSS）可以有不同实现（Miniflux、直接 HTTP 抓取、第三方聚合 API）。
- **可扩展**：未来可轻松添加数据转换、去重、排序等中间件。

### 模块开发指南

为 news-report 新增信息源模块需遵循以下步骤：

1. **在注册表登记**：于「信息源模块化架构」节的注册表中添加一行，明确 module id、数据访问方式、可用检索能力、配置项（环境变量命名规则 `<MODULE>_*`）与状态（规划中→可用）。
2. **编写模块章节**：在 SKILL.md 中新增独立章节，结构参照「模块 01：Miniflux」。必须包含：
   - 前置条件（依赖的软件/服务版本）
   - 配置方式（MCP 服务器配置、直接 HTTP 集成等）
   - 环境变量表（必填/可选，示例占位 `${VAR}`）
   - 可用工具表（每个工具的签名、参数说明、返回格式）
   - 常用工作流示例
   - 模块专属的排障条目
3. **提供可执行示例**：所有终端命令必须注明平台（Linux/macOS 与 Windows PowerShell），确保用户可直接复制执行。
4. **遵守只读边界**：当前版本模块不得包含创建、修改、删除数据源的操作；如确有需要，须在 AGENTS.md 中明确记录例外并同步 CHANGELOG。
5. **同步 CHANGELOG**：模块从规划中变为可用时，在 CHANGELOG.md 添加 `feat(module):` 条目。

### 测试与验证

在部署或贡献模块前，建议进行以下验证：

- **环境变量检查**：确保 `MINIFLUX_BASE_URL` 等变量已正确设置，且值不含尾随斜杠。
- **MCP 服务器连通性**：在终端执行 `npx -y miniflux-mcp`（方案 A）或 `node /path/to/server.js`（方案 B），观察无报错启动。
- **工具调用测试**：通过宿主（如 opencode）的 MCP 调试工具或编写简单脚本调用 `listCategories`、`searchEntries` 等，确认返回预期数据。
- **错误处理测试**：故意提供错误凭据或 URL，检查返回的错误信息是否清晰可读。
- **跨平台验证**：若模块涉及平台特定命令（如 PowerShell 与 Bash），需在目标平台上实际执行确认。

### 部署与维护

- **版本锁定**：对于通过 npm 安装的 MCP 服务器（如 miniflux-mcp），建议在 `command` 中固定版本号（如 `miniflux-mcp@0.0.12`）以避免意外升级导致的不兼容。
- **配置备份**：opencode 的 `opencode.json` 中 MCP 服务器配置应纳入版本控制（敏感值替换为 `${VAR}` 占位）。
- **监控**：关注 MCP 服务器的日志输出，尤其注意认证失败、速率限制、连接超时等异常。
- **升级流程**：
  1. 阅读上游 Changelog，确认无破坏性变更。
  2. 在测试环境更新版本，运行全套验证步骤。
  3. 若为方案 B，重新应用 Basic Auth 补丁（如仍需）。
  4. 更新 SKILL.md 中的版本说明与 CHANGELOG。

### 安全最佳实践

1. **凭据隔离**：API Token、密码等**绝不硬编码**在配置文件、脚本或文档中；一律通过环境变量传递，示例中用 `${VAR}` 占位。
2. **最小权限**：Miniflux API Token 应仅授予**只读**权限（Miniflux 设置 → API Keys → 创建时勾选「Read-only」）。
3. **网络隔离**：若 Miniflux 实例部署在内网，确保 MCP 服务器运行在同一网络环境，避免 token 在公网传输。
4. **定期轮换**：定期更新 API Token，并在更新后立即注销旧 token。
5. **审计日志**：启用 Miniflux 的审计日志功能，监控异常访问模式。

### 性能优化建议

- **分页查询**：使用 `searchEntries` 的 `limit` / `offset` 参数分批获取文章，避免单次响应过大。
- **缓存策略**：MCP 协议本身不缓存工具响应，重复调用会真实请求 Miniflux；如需避免重复抓取，可在应用层对短期内的相同查询做结果缓存（或利用 Miniflux 服务端缓存）。
- **并行请求**：当需要从多个分类或订阅源聚合数据时，可一次发起多个 `searchEntries` 调用（MCP 工具调用由 AI 编排执行，批量发起可减少对话往返轮次）。
- **字段过滤**：Miniflux API 允许通过 `?fields=` 参数限制返回字段，但 miniflux-mcp 目前未暴露此参数；若未来支持，可减少网络传输量。

### 故障排查进阶

> 基础排障（凭据错误、404、依赖缺失、服务器无法启动）见「模块 01」排障表，此处仅列进阶场景。

| 现象 | 可能原因 | 排查步骤 |
|------|----------|----------|
| 工具调用返回 `access unauthorized` 且凭据近期更换过 | API Token 已过期或被撤销 | 在 Miniflux 设置 → API Keys 重新生成 Token，并更新环境变量 |
| 工具调用返回 `access unauthorized` 且同时配置了 Token 与用户名/密码 | 认证参数冲突，Token 优先级高于 Basic Auth | 确认 `MINIFLUX_TOKEN` 有效；若改用 Basic Auth，需移除 Token 环境变量 |
| searchEntries 结果感觉不全 | 未显式指定状态或分页限制 | 不传 `status` 时返回全部状态（依据 miniflux-mcp v0.0.12 源码：不传时不追加该参数）；如需特定状态显式传 `status: "read,unread"`；大结果集用 `limit` / `offset` 或 `before_entry_id` / `after_entry_id` 翻页 |
| 中文关键词搜索无结果 | Miniflux 全文搜索基于 PostgreSQL 默认配置，对中文分词支持有限 | 将关键词调整为短语、用 `category_id` / `feed_id` 限定范围，或先用英文标题词搜索再在结果中筛选 |
| 服务器日志出现 `ECONNRESET` | 网络不稳定或 Miniflux 实例负载过高 | 检查网络连通性；如需增加超时，需修改 miniflux-mcp 源码 |

### 模块 02：Zhihu Search（知乎开放平台 CLI + MCP）

通过 [zhihu-search](https://github.com/klarkxy/zhihu-search) 接入知乎开放平台，支持知乎社区搜索、全网搜索、AI 直答、热榜、问题推荐、回答摘要、知识库、PDF / PPT 生成、OAuth。CLI + MCP 双形态，Apache 2.0 开源。

> **重要**：本项目已从旧的 `zhihu-cli`（PyPI 1.2.0，2020 年停止维护，Python 3.10+ 无法构建其锁死的 `lxml==4.3.4`）迁移到 `zhihu-search`（v2.x，2026 年维护中）。`src/collect_zhihu.py` 已重写为调用 `zhihu-search` 命令，旧 `ZHIHU_CLI_PATH` 环境变量仍被兼容识别（作为路径查找 fallback）。
>
> 完整文档：[zhihu-search README](https://github.com/klarkxy/zhihu-search)、[zhihu-search PyPI](https://pypi.org/project/zhihu-search/)。

#### 前置条件

- Python 3.10+ 和 [uv](https://docs.astral.sh/uv/)
- 知乎开放平台 Access Secret（[https://developer.zhihu.com/profile](https://developer.zhihu.com/profile) 登录生成）

#### 安装

```bash
# 一行安装（推荐）
uv tool install zhihu-search

# 或使用 pipx
pipx install zhihu-search
```

安装后配置 Access Secret（二选一）：

```bash
# 方式 A：写入本地凭证文件（推荐）
zhihu-search --save-token <YOUR_ACCESS_SECRET>

# 方式 B：设置环境变量（.env 里）
export ZHIHU_ACCESS_SECRET="<YOUR_ACCESS_SECRET>"
```

验证：

```bash
zhihu-search --check-token       # 检查凭证来源
zhihu-search --probe             # 端到端验证（消耗 1 次 hot_list 额度）
```

#### 环境变量

| 变量 | 说明 |
|------|------|
| `ZHIHU_SEARCH_CLI_PATH` | zhihu-search 二进制路径（自动检测时可不设，canonical name） |
| `ZHIHU_CLI_PATH` | 兼容旧环境变量的别名（自动查找时会尝试） |
| `ZHIHU_ACCESS_SECRET` | Access Secret（也可通过 `--save-token` 写入凭证文件） |

#### 可用能力

| 命令 | 说明 | 示例 |
|------|------|------|
| `search --scope zhihu` | 搜索知乎社区内容（回答、文章、经验），上限 10 条 | `<CLI> search "AI工具" --scope zhihu --count 10 --format json` |
| `search --scope web` | 搜索全网来源（知乎之外），上限 20 条 | `<CLI> search "AI趋势" --scope web --count 10 --format json` |
| `trending` | 获取知乎热榜，上限 30 条 | `<CLI> trending --limit 20 --format json` |
| `ask` | 调用知乎 AI 直答 | `<CLI> ask "问题" --format json` |
| `question-recommendations` | 发现待回答问题 | `<CLI> question-recommendations` |
| `question-answers` | 查看问题回答摘要 | `<CLI> question-answers <url>` |
| `quota` | 查看 API 剩余额度 | `<CLI> quota` |
| `serve` | 启动 stdio MCP 服务器（默认行为） | `<CLI> serve --tools compact` |

> **JSON 输出**：所有数据命令支持 `--format json` 或 `--format markdown`。`src/collect_zhihu.py` 统一使用 JSON 输出。
>
> **Search 输出结构**：`{"success": true, "kind": "search", "data": {"Items": [{Title, Url, AuthorName, ContentText, EditTime, VoteUpCount, CommentCount, ...}]}}`
>
> **Trending 输出结构**：`{"success": true, "kind": "trending", "data": {"Total": int, "Items": [{Title, Url, Summary, ThumbnailUrl}]}}`

#### 在 news-report 中的使用

脚本路径通过 `src/collect_zhihu.py` 集成，支持：
- 知乎社区搜索（`search --scope zhihu`）
- 全网搜索（`search --scope web`）
- 热榜采集（`trending`）

无鉴权时优雅跳过，不影响其他采集模块。

#### 排障

| 问题 | 原因 | 解决 |
|------|------|------|
| `Not authenticated` | 未配置 Access Secret | 在 developer.zhihu.com/profile 生成并配置（`zhihu-search --save-token`） |
| `CLI not found` | 未安装 zhihu-search | 运行 `uv tool install zhihu-search` |
| `AUTH_REQUIRED` / API 401 | Access Secret 失效 | 去 developer.zhihu.com 重新生成 |
| `rate_limit` | 请求过于频繁 | 降低并发，增加延迟（脚本默认 `time.sleep(1)`） |
| `unrecognized arguments` | 参数与旧版 zhihu-cli 不兼容 | 使用新版语法：`search <query> --scope zhihu|web --count N --format json` |

#### 与旧版 zhihu-cli 的差异

| 维度 | 旧 `zhihu-cli` (v1.2.0) | 新 `zhihu-search` (v2.x) |
|------|------------------------|--------------------------|
| 维护状态 | 2020 停止维护 | 2026 维护中 |
| Python 支持 | 仅 ≤3.8（lxml 4.3.4 锁死） | 3.10+ |
| 命令语法 | `zhihu-cli search zhihu --query "x"` | `zhihu-search search "x" --scope zhihu` |
| 输出格式 | JSON（`--format` 参数无） | JSON / Markdown（`--format`） |
| 认证 | `zhihu-cli auth set` | `zhihu-search --save-token` |
| MCP 支持 | 无 | `zhihu-search serve`（stdio MCP） |

### 模块 03：Twitter/X CLI

通过 [twitter-cli](https://github.com/jackwener/twitter-cli) 接入 Twitter/X 平台，支持推文搜索、时间线、书签、用户资料与话题标签。Apache 2.0 开源，Python 实现。

> 完整文档见 [SKILL.md](https://raw.githubusercontent.com/jackwener/twitter-cli/main/SKILL.md)（v0.8.0）。

#### 前置条件

- twitter-cli（`uv tool install twitter-cli` 或 `pipx install twitter-cli`）
- 浏览器登录 x.com（自动提取 Cookie）或设置环境变量 `TWITTER_AUTH_TOKEN` / `TWITTER_CT0`

#### 安装

```bash
# macOS / Linux
uv tool install twitter-cli

# 或使用 pipx
pipx install twitter-cli
```

#### 认证

```bash
# 检查状态
twitter status

# 检查当前用户
twitter whoami
```

无鉴权时大部分读取命令仍可用（搜索结果有限）。

#### 可用能力

| 命令 | 说明 | 示例 |
|------|------|------|
| `search` | 搜索推文 | `twitter search "AI agent" --max 20 --json` |
| `feed` | 时间线（For You / Following） | `twitter feed -t following --max 50 --json` |
| `bookmarks` | 书签列表 | `twitter bookmarks --max 30 --json` |
| `user-posts` | 用户推文 | `twitter user-posts elonmusk --max 20 --json` |
| `tweet` | 推文详情 | `twitter tweet 1234567890 --json` |
| `user` | 用户资料 | `twitter user elonmusk --json` |

#### 在 news-report 中的使用

脚本路径通过 `src/collect_twitter.py` 集成，支持：
- 推文搜索（`search`）
- 时间线采集（`feed`）

无鉴权时优雅跳过，不影响其他采集模块。

#### 排障

| 问题 | 原因 | 解决 |
|------|------|------|
| `No Twitter cookies found` | 未登录 | 在浏览器登录 x.com，或设置 `TWITTER_AUTH_TOKEN` |
| HTTP 226 | 自动检测 | 使用浏览器 Cookie 提取（非 env vars） |
| HTTP 401/403 | Cookie 过期 | 重新登录 x.com |
| HTTP 429 | 请求过快 | 等待 15 分钟后重试 |

### 模块 04：Bilibili CLI

通过 [bilibili-cli](https://github.com/jackwener/bilibili-cli) 接入 B 站平台，支持视频搜索、热门榜、排行榜、用户资料与动态。Apache 2.0 开源，Python 实现。

> 完整文档见 [SKILL.md](https://raw.githubusercontent.com/jackwener/bilibili-cli/main/SKILL.md)。

#### 前置条件

- bilibili-cli（`uv tool install bilibili-cli` 或 `pipx install bilibili-cli`）
- 大部分命令无需登录；动态/收藏/互动需认证

#### 安装

```bash
# macOS / Linux
uv tool install bilibili-cli

# 或使用 pipx
pipx install bilibili-cli
```

#### 认证

```bash
# 检查状态
bili status

# 扫码登录（可选）
bili login
```

大部分命令无需登录即可使用（搜索、热门、排行榜）。

#### 可用能力

| 命令 | 说明 | 示例 |
|------|------|------|
| `search` | 搜索视频/用户 | `bili search "AI" --type video --max 10 --json` |
| `hot` | 热门视频 | `bili hot --max 20 --json` |
| `rank` | 全站排行榜 | `bili rank --day 3 --max 20 --json` |
| `feed` | 动态时间线 | `bili feed --json` |
| `video` | 视频详情 | `bili video BV1ABcsztEcY --json` |
| `user` | UP 主资料 | `bili user 946974 --json` |

#### 在 news-report 中的使用

脚本路径通过 `src/collect_bilibili.py` 集成，支持：
- 视频搜索（`search`）
- 热门榜采集（`hot`）
- 排行榜采集（`rank`）

无鉴权时部分功能受限，但搜索/热门/排行榜仍可用。

#### 排障

| 问题 | 原因 | 解决 |
|------|------|------|
| `HTTP 412` | 反爬触发 | 稍等后重试，或减小 `--max` |
| `需要登录` | 未认证 | 运行 `bili login` 扫码 |
| `NetworkError` | 网络问题 | 检查网络连接 |

### 模块 05：Xiaohongshu (小红书) CLI

通过 [xiaohongshu-cli](https://github.com/jackwener/xiaohongshu-cli) 接入小红书平台，支持笔记搜索、热门榜、推荐 Feed、用户资料与话题。Apache 2.0 开源，Python 实现。

> 完整文档见 [SKILL.md](https://raw.githubusercontent.com/jackwener/xiaohongshu-cli/main/SKILL.md)。

#### 前置条件

- xiaohongshu-cli（`uv tool install xiaohongshu-cli` 或 `pipx install xiaohongshu-cli`）
- 浏览器登录 xiaohongshu.com（自动提取 Cookie）或二维码扫码登录

#### 安装

```bash
# macOS / Linux
uv tool install xiaohongshu-cli

# 或使用 pipx
pipx install xiaohongshu-cli
```

#### 认证

```bash
# 检查状态
xhs status

# 从浏览器提取 Cookie（推荐）
xhs login

# 二维码扫码登录
xhs login --qrcode
```

Cookie 有效期 7 天，过期后自动尝试从浏览器刷新。

#### 可用能力

| 命令 | 说明 | 示例 |
|------|------|------|
| `search` | 搜索笔记 | `xhs search "美食" --max 20 --json` |
| `hot` | 热门笔记（按分类） | `xhs hot -c fashion --max 20 --json` |
| `feed` | 推荐 Feed | `xhs feed --max 20 --json` |
| `topics` | 话题搜索 | `xhs topics "美食" --json` |
| `search-user` | 用户搜索 | `xhs search-user "用户名" --json` |
| `user` | 用户资料 | `xhs user <user_id> --json` |
| `read` | 笔记详情 | `xhs read <note_id> --json` |

**热门分类**：fashion, food, cosmetics, movie, career, love, home, gaming, travel, fitness

#### 在 news-report 中的使用

脚本路径通过 `src/collect_xhs.py` 集成，支持：
- 笔记搜索（`search`）
- 热门榜采集（`hot`，支持多分类）
- 推荐 Feed（`feed`）

无鉴权时优雅跳过，不影响其他采集模块。

#### 排障

| 问题 | 原因 | 解决 |
|------|------|------|
| `NoCookieError` | 未登录 | 在浏览器登录 xiaohongshu.com，然后运行 `xhs login` |
| `NeedVerifyError` | 触发验证码 | 在浏览器完成验证后重试 |
| `IpBlockedError` | IP 被限制 | 切换网络（热点或 VPN） |
| `SessionExpiredError` | Cookie 过期 | 运行 `xhs login` 刷新 |
| 请求较慢 | 内置高斯抖动延迟 | 正常现象，避免触发风控 |

### 扩展模块示例（规划中模块参考）

以下为规划中模块的**假设性**设计，用于展示模块章节应包含的内容结构：

#### 模块 06 · `rss-http`（直接抓取 RSS/Atom 源）

**前置条件**：
- Node.js >= 18 或 Python >= 3.9（视实现语言而定）
- 可访问的 RSS/Atom 源 URL

**配置方式**：
- 通过独立的 MCP 服务器或直接集成到 news-report Skill 中（待设计）。

**环境变量**（假设命名，非规划确定值）：
- `RSS_HTTP_USER_AGENT`（可选）：HTTP User-Agent 字符串，避免被源站屏蔽。
- `RSS_HTTP_TIMEOUT`（可选）：请求超时（秒），默认 30。

**预期能力**（假设，未实现）：
- 抓取并解析指定 URL 的 RSS/Atom 源，返回标准化条目列表（参数示意，均为假设命名：`url`、`limit?`）。
- 通过 HTML `<link>` 标签发现站点提供的 feed URL（参数示意，均为假设命名：`site_url`）。

> **勿将上述参数名当作可用工具调用**：本示例仅展示未来模块章节的结构，模块 06 当前不存在任何工具。

**常用工作流**（示意，非可执行）：
```
# 示意：抓取某博客的最新 10 篇文章
fetch feed from "https://example.com/feed.xml" with limit 10
```

**排障**：
- `Invalid feed format`：确认 URL 返回的是有效的 RSS/Atom XML。
- `HTTP 429 Too Many Requests`：添加延迟、轮换 User-Agent 或使用缓存。

> **注意**：以上内容仅为示例，**非当前实现**。实际开发时需基于 RSS 解析最佳实践（处理编码、`content:encoded` 提取、限速等）完成。

## 每条新闻的元数据字段（强制，Agent 生成简报时必须完整标注）

> **v0.7.0 新增。** 每一条进入简报的新闻必须带以下 5 个字段，用于让读者快速判断价值与真伪，同时支撑冷却去重与信源质量过滤。

### 1. Significance（重要性 1-5）

| 分数 | 含义 | 示例 |
|---|---|---|
| 5 | 颠覆性 / 行业变革 | GPT-6 正式发布、iPhone 新发布、Apple 收购、CEO 更换 |
| 4 | 重要产品 / 功能发布，重大公司动作 | 新模型发布、大额融资、行业政策变化 |
| 3 | 值得关注的次要新闻 | 一般产品迭代、中型公司动态 |
| 2 | 常规资讯 | 版本更新、次要功能 |
| 1 | 边缘信息（默认剔除） | 极冷僻条目 |

**筛选规则**：Significance < 3 的新闻一律不进入简报（除非信源稀缺需要补充上下文）。

### 2. Development Status（发展状态标签，10 种）

- `🚀 已发布` —— 产品/功能已正式发布，用户可用
- `📢 预告` —— 官方预告/宣布即将发布，但未发布
- `🔧 进行中` —— 开发/测试/内测阶段
- `✅ 已完成` —— 事件已落幕，是回顾/总结
- `📋 讨论中` —— 社区/媒体正在讨论、无最终结论
- `⚠️ 事故/危机` —— 服务中断、安全事故、负面事件
- `📉 裁员/衰退` —— 公司裁员、业务收缩
- `🤝 合作/收购` —— 合作、并购、结盟
- `📈 融资/估值` —— 融资、上市、估值变化
- `🏛️ 政策/监管` —— 监管、立法、政策变化

### 3. Key Entities（关键实体，1-3 个）

- **公司 / 组织**：Apple、OpenAI、Blender Foundation
- **产品 / 服务**：GPT-6 Astra、Blender 5.2、OpenCode Go
- **人物**：Tim Cook、Sam Altman（只提取直接相关的关键人物）

格式：`[Apple] [iPhone Duo]`（用方括号包裹，加空格分隔）。

### 4. Sentiment（情感倾向）

- `[+]` 正面 · `[~]` 中性 · `[-]` 负面 · `[?]` 未知（信息不足，宁标 [?] 也不瞎猜）

### 5. Data Quality（数据质量 1-10）

| 分数 | 信源类型 | 示例 |
|---|---|---|
| 9-10 | 官方公告 / 一手权威媒体 | 官方博客、press release、Reuters/AP |
| 7-8 | 二线权威媒体 / 专业分析 | 36Kr、The Verge、TechCrunch |
| 5-6 | 一般新闻 / 社区讨论 | 少数派、知乎、个人博客 |
| 3-4 | 聚合媒体 / 摘要 | 微信转载、AI 生成摘要 |
| 1-2 | 内容农场 / 明显标题党 | 自动搬运、无实质内容 |

**质量过滤规则**：Data Quality < 4 的新闻，除非是 🔴 紧急级独家信源，否则剔除。

## 打分细则（Agent 生成简报时对照）

### Significance 打分

```
5 = 全球行业头部公司 + 产品级发布；或首次开创性事件（首次 AI 大会）
4 = 公司主要新产品/新功能；或十亿以上融资；或影响行业标准的政策
3 = 产品迭代；中型公司动态；行业重要但不颠覆
2 = 常规更新、版本发布、次要功能
1 = 边缘信息，无实质内容
```

### Data Quality 打分

| 信源类型 | 默认分 |
|---|---|
| 公司官方博客 / press release | 10 |
| Reuters / AP / Bloomberg / 白宫 | 9 |
| The Verge / TechCrunch / MIT Tech Review / 36Kr 深度报道 | 8 |
| 爱范儿 / 少数派 / 虎嗅 / 知乎热榜 | 7 |
| 一般新闻 / 个人博客 / Hacker News | 6 |
| 微信转载 / AI 摘要 / 内容搬运 | 4 |
| 明显内容农场 / 无源报道 | 2 |

### Key Entities 提取优先级

1. 主要公司/组织（第一个实体必须是主角）
2. 相关产品/服务
3. 直接相关人物（只取最关键的）

最多 3 个，宁少不多。

## 状态存储与冷却机制（跨简报去重）

> **v0.7.0 新增。** 参考 news-aggregator 的 alert cooldown 和 news-pipeline-n8n 的事件签名机制。目的：同一事件在 24 小时内已推送，即使有新信源出现也不重复推送，避免早报刷屏。

### 目录结构

```
~/.hermes/skills/news-report/
├── SKILL.md                          # 本文件
├── scripts/
│   └── cooldown_check.py             # 冷却机制 CLI 工具
└── state/
    └── pushed_events.json            # 事件签名存储（运行时生成）
```

### pushed_events.json 格式

```json
{
  "2026-10-06": {
    "gpt-6-astra-launch": {
      "event_name": "gpt-6-astra-launch",
      "key_entity": "OpenAI",
      "event_type": "launch",
      "significance": 5,
      "summary_hash": "sha1(标题前80字)",
      "urls": ["https://openai.com/blog/..."],
      "first_pushed": "2026-10-06T07:32:00+08:00",
      "last_updated": "2026-10-06T07:32:00+08:00"
    }
  }
}
```

### 冷却规则

- 同一 `key_entity + event_type` 组合在 24 小时内已推，跳过
- 24 小时后允许再次推送，但需有实质新进展（新数据/新功能/新公告），否则仍跳过
- 每条日报最多保留 7 天历史，超过的日期自动清理（`cooldown_check.py prune`）

### cooldown_check.py 用法

```bash
# 检查某事件是否在冷却期
python3 scripts/cooldown_check.py check <key_entity> <event_type>

# 推送记录（简报发出后调用）
python3 scripts/cooldown_check.py push <event_name> <key_entity> <event_type> <significance> <summary_hash> <url1> [url2...]

# 列出当日活跃签名（Agent 生成简报前必读）
python3 scripts/cooldown_check.py list

# 清理超过 7 天的历史
python3 scripts/cooldown_check.py prune
```

### Agent 生成规则

1. **生成前**：读 `state/pushed_events.json`，构造当日已推事件签名集合
2. **筛选中**：候选事件与已推集合比对，24 小时内重复的一律跳过
3. **生成后**：对每条实际推送的事件调用 `cooldown_check.py push` 记录签名
4. **失败兜底**：如果 cooldown 脚本不可用，跳过冷却检查但记录 warning

## 输出模板

> **v0.3.0 正式定义。** Agent 直接路径按本节模板排版；脚本路径由 `src/report.py` 自动生成。模板设计原则：**信息密度最大化、阅读体验最优化、节奏从冲击到沉静的叙事弧**。
>
> **⚠️ v0.7.0 补充说明**：本节模板是**代码路径的自动化排版模板**（TOP SIGNAL / 优先级分区 / 影响分析 / 示例），由 `src/report.py` 消费。Agent **对话直跑模式**（老板要求生成日报/早报时）应使用运行时 skill `~/.hermes/skills/news-report/SKILL.md` 里的【输出模板】章节，其中每条新闻必须带本文档前几节定义的 5 个元数据字段（Significance / Development Status / Key Entities / Sentiment / Data Quality），并在结尾调用 `scripts/cooldown_check.py push` 记录事件签名。两条路径产出内容不同：本节的 TOP SIGNAL + 影响分析 + 职业风险矩阵适合长版深度分析，运行时模板适合 Telegram 友好的日常简报。

### 设计原则

| 原则 | 说明 |
|------|------|
| **信息密度** | 每条新闻一行核心信息 + 一行洞察 + 一行元数据，零冗余空白 |
| **阅读体验** | 视觉层级清晰（🎯→🔴→🟡→🟢→🔵），可扫描，关键洞察用 💡 高亮 |
| **节奏安排** | 叙事弧：TOP SIGNAL（钩子）→ 紧急（展开）→ 关注（深入）→ 常规（速览）→ 背景（速记）→ 影响分析（综合）→ 来源（收尾） |
| **可操作性** | 影响分析给出跨行业传导路径和职业风险矩阵，读者可直接行动 |

### 模板结构

```
📰 NEWS BRIEF · {YYYY-MM-DD HH:mm} GMT+8
═══════════════════════════════════════════════════════════════
{信源数} sources → {采集数} collected → {精选数} curated
🔴 {n} urgent  🟡 {n} important  🟢 {n} regular  🔵 {n} context

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 TOP SIGNAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
| {标题} |
| {一句话核心洞察，回答"so what?"} |
| [Read](url) · 📡 {来源} · {预估阅读时间} min |

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔴 紧急 ({n} items)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
① {标题}
   💡 {关键洞察}
   📡 {来源} · [link](url)

② {标题}
   💡 {关键洞察}
   📡 {来源} · [link](url)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🟡 关注 ({n} items)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
③ {标题}
   📡 {来源} · [link](url)

④ {标题}
   📡 {来源} · [link](url)

⑤ {标题}
   📡 {来源} · [link](url)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🟢 常规 ({n} items)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⑥  {标题} · 📡 {来源}
⑦  {标题} · 📡 {来源}
⑧  {标题} · 📡 {来源}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔵 背景 ({n} items)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⑨   {标题} · {来源}
⑩   {标题} · {来源}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 影响分析
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 跨行业传导
  {行业1} → {影响1} · {影响2}
  {行业2} → {影响3} · {影响4}
  {行业3} → {影响5}

⚠️ 职业风险矩阵
  🔴 {高危岗位} ({时间框架})
  🟡 {中危岗位} ({时间框架})
  🟢 {安全岗位}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 {日期} · RSS {n}/{total} · Search {n}/{total} · TG {n}/{total}
```

### 优先级分配规则

| 级别 | 标识 | 格式 | 条件 |
|------|------|------|------|
| **TOP SIGNAL** | 🎯 | 标题 + 洞察 + 链接 + 来源 + 阅读时间 | 当日最具格局重塑意义的单条新闻 |
| **紧急** | 🔴 P0 | 序号 + 标题 + 💡洞察 + 来源 + 链接 | 突发/重大/格局重塑级事件 |
| **关注** | 🟡 P1 | 序号 + 标题 + 来源 + 链接 | 重要发布/里程碑/行业拐点 |
| **常规** | 🟢 P2 | 序号 + 标题 + 来源（单行） | 有价值的日常信息 |
| **背景** | 🔵 P3 | 序号 + 标题 + 来源（单行，无链接） | 低优先级/参考信息 |

### 排版细则

1. **编号连续**：①②③ 跨优先级连续编号，全局唯一
2. **标题限长**：主标题 ≤100 字符，超出截断加 `…`
3. **洞察限长**：💡 洞察 ≤80 字符，回答"so what?"
4. **来源标识**：统一用 `📡 {来源名}` 格式
5. **链接处理**：标题本身可内嵌链接，元数据行独立链接
6. **空白控制**：P0/P1 条目间空一行；P2/P3 无空行；章节间一个空行
7. **分隔线**：章节标题用 `━━━` (em dash)，header/footer 用 `════` (double em dash)
8. **编码**：全文 UTF-8，中文标点，英文标点仅在代码/URL 中

### 影响分析指南

「影响分析」章节是模板的灵魂——将散落的新闻编织成叙事：

**跨行业传导**：
- 从技术突破 → 直接影响行业 → 次生影响行业
- 格式：`{行业} → {影响}`，每个行业 2-3 个影响点
- 优先覆盖：软件/技术、法律/金融、创意/设计、制造/物流

**职业风险矩阵**：
- 🔴 高危：1-2 年内显著受影响（初级开发者、3D 建模师等）
- 🟡 中危：2-3 年内受影响，需转型（内容创作者、翻译等）
- 🟢 安全：短期难被替代（架构师、研究员、医生等）
- 每条给出具体岗位 + 时间框架

### 示例

```
📰 NEWS BRIEF · 2026-09-18 14:30 GMT+8
═══════════════════════════════════════════════════════════════
27 sources → 208 collected → 20 curated
🔴 2 urgent  🟡 8 important  🟢 7 regular  🔵 3 context

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 TOP SIGNAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
| GPT-6 Astra 宣告 AGI 起点：数学突破经 Lean 形式化验证 |
| AI 首次推动数学研究进展（孪生素数 246→186），从"回答"到"操作"的范式转移 |
| [Read](https://...) · 📡 OpenAI · 5 min |

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔴 紧急 (2 items)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
① GPT-6 Astra: ARC-AGI-3 99.9%, 网络安全利用 100%
   💡 AI 不再"回答问题"而是"操作电脑"——Blender/Unity 直接建模
   📡 OpenAI · [link](url)

② GLM-5.3 发现潜伏 40 年 DNS 漏洞，开源模型开源第一
   💡 2404 漏洞中 1088 中高危，影响 1000 万+ 公网 DNS 服务
   📡 智谱 · [link](url)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🟡 关注 (8 items)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
③ Claude Opus 4.6: 1M 上下文 + 最强 agentic coding
   📡 Anthropic · [link](url)

④ 李开复×苏姿丰: 2026 年 AI 开始替代整个部门
   📡 网易 · [link](url)

⑤ AI 取代成本优化，成为公司裁员首要理由
   📡 CNBC · [link](url)

⑥ Gemini App 获得 agentic 能力，7×24 主动支持
   📡 Google · [link](url)

⑦ AI 威胁"可拆解"的工作——任务越可分解越易被替代
   📡 Computerworld · [link](url)

⑧ 上科大报告: 复合型闭环岗位成最大新增量
   📡 经济日报 · [link](url)

⑨ 三星 TrOPD: 将前沿智能塞进数亿终端
   📡 三星 · [link](url)

⑩ 中国 AI 登上 Science: 全球首个专家级通用影像 AI
   📡 网易 · [link](url)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🟢 常规 (7 items)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⑪  Anthropic: Claude 已主导其 26% 内部 AI 研发 · 📡 网易
⑫  以色列首届物理 AI 大会: 展示物理智能新成果 · 📡 新华社
⑬  高通钱堃: 智能体 AI 规模化带来产业协同机遇 · 📡 新华社
⑭  全球 AI 加速迈向自主智能和物理交互阶段 · 📡 财经
⑮  百年黎曼猜想被 Claude 破新纪录 · 📡 网易
⑯  具身智能 GPT-3 时刻: 3 秒人类演示→机器人学会 · 📡 网易
⑰  量子计算开源社区"量立方"上海揭牌 · 📡 DeepTech

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔵 背景 (3 items)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⑱   Claude Opus 4.6 系统卡: 安全评测全行业最佳 · Anthropic
⑲   Google 发布 Gemini 应用更新日志 · Google
⑳   OpenAI 产品发布记录 (Tamil) · OpenAI

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 影响分析
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 跨行业传导
  Software → 初级开发价值↓ · 3D 设计民主化 · 安全审计转向验证
  Legal → 合同审查自动化 · 金融分析重构
  Creative → 原型→生产管线变革 · 概念设计跳过建模阶段
  Manufacturing → 仓储自动化新阶段 · 机器人部署成本骤降

⚠️ 职业风险矩阵
  🔴 初级开发/前端/3D 设计/法律助理 (1-2 年)
  🟡 内容创作/翻译/数据分析/财务 (2-3 年)
  🟢 架构师/研究员/医生/产品经理/教育 (安全)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 2026-09-18 · RSS 19/27 · Search 6/6 · TG 0/0
```

## 版本信息

- **Skill 版本**：v0.6.1 —— 新增 Contract 表（输入/输出/失败行为/副作用/完成标准）、修正只读边界表述、修复 zhihu-cli 模块路径引用。
  - v0.6.0 —— 新增模块 05 · xiaohongshu-cli（小红书 CLI），接入笔记搜索、热门榜（多分类）、推荐 Feed 与话题。
  - v0.5.0 —— 新增模块 03 · twitter-cli（Twitter/X CLI）和模块 04 · bilibili-cli（Bilibili CLI），接入推文搜索、时间线、视频搜索、热门榜与排行榜。
  - v0.4.0 —— 新增模块 02 · zhihu-cli（知乎开放平台 CLI），接入知乎社区搜索、全网搜索、热榜、AI 直答。
  - v0.3.0 —— 正式定义输出模板（新增「输出模板」章节，含 TOP SIGNAL / 优先级分区 / 影响分析 / 完整示例）。
  - v0.2.2 新增专业开发流程（CI/CD、代码质量检查、自动化发布、仓库治理）。
  - v0.2.1 修复工具签名与参数表，新增高级指南章节。
  - v0.2.0 为仓库更名重定位（`miniflux-mcp-skill` → `news-report`，引入模块化架构与通用约定）；输出格式待下一阶段设计。
  - v0.1.0 为原 miniflux-mcp-skill 初始发布。
- **Skill 创建**：2026-08-01（原 miniflux-mcp-skill v0.1.0 发布时记录，保留）
- **MCP Server（模块 01）**：miniflux-mcp v0.0.12（方案 B 含 Basic Auth 补丁）

## 来源

- **MCP Server（模块 01）**：[github.com/tan-yong-sheng/miniflux-mcp](https://github.com/tan-yong-sheng/miniflux-mcp) · [npm: miniflux-mcp](https://www.npmjs.com/package/miniflux-mcp)
- **Miniflux API**：[miniflux.app/docs](https://miniflux.app/docs/)
- **License**: CC BY-NC-SA 4.0
