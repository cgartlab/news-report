---
name: news-report
description: >-
  Modular news-gathering skill that retrieves news and articles across pluggable
  information sources (Miniflux RSS via the miniflux-mcp MCP server is module 01),
  so you can read RSS feeds, check subscriptions, search articles and prepare
  material for a news briefing directly from conversation; trigger when the user
  asks to read RSS / check feeds / search articles / gather news-briefing material,
  or mentions "Miniflux", "RSS", "feeds", "订阅", "新闻", "简报".
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

> **输出格式：下一阶段设计。** 本版聚焦信息检索与整理，不定义新闻简报 / 报告的输出模板。若用户要求排版成稿，请说明当前仅提供结构化检索结果，最终输出格式留待下一阶段。

**边界**：news-report 当前**只读**——仅从各信息源检索数据，不创建或修改订阅源、不标记文章、不写任何内容（详见「通用约定」）。

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
| 模块 01 · `miniflux`（Miniflux RSS，经 miniflux-mcp MCP） | MCP 服务器 | 分类 / 订阅源浏览、全文搜索、未读 / 星标、分页排序（详见下节） | `MINIFLUX_BASE_URL`、`MINIFLUX_TOKEN`、`MINIFLUX_USERNAME`、`MINIFLUX_PASSWORD` | ✅ 可用 |
| 模块 02 · `rss-http`（直接抓取 RSS / Atom 源，示例占位） | HTTP | 待下阶段定义 | 待下阶段定义 | ⏳ 规划中 |
| 模块 03 · `news-api`（NewsAPI / NewsData.io 等聚合 API，示例占位） | HTTP API | 待下阶段定义 | 待下阶段定义 | ⏳ 规划中 |

> 模块 02 / 03 **仅为架构示例占位**：当前不存在对应的工具、命令或脚本，检索能力与配置项一律待下阶段设计；本版不得向用户声称可调用它们，也不得在回复中伪造其工具名。

### 扩展方式

后续新增信息源时：① 在注册表登记一行并标注状态；② 在 SKILL.md 增加对应模块章节（结构对齐模块 01）；③ 新增脚本 / 配置须给出可复制的命令并注明平台；④ 同步更新 CHANGELOG。规划中模块只占位、不预写实现细节。

## 通用约定

1. **密钥策略**：API key / token 一律存放在本地环境变量（shell profile、agent 运行时 env 或本地密钥管理器），示例统一用 `${VAR}` 占位，**绝不硬编码真实密钥**，也不得把密钥写入任何输出文件、配置样本或提交历史。配置文件中的 `env` 段引用本地环境变量（见模块 01 的 MCP 配置示例）。
2. **终端示例约定**：凡需在终端执行的操作，均给出**可直接复制执行**的命令 / 脚本，并注明所需平台（Linux / macOS，或 Windows PowerShell）；平台差异处分别给出写法。
3. **只读边界（当前版本）**：news-report 只做信息采集与检索，不修改任何信息源的数据（不创建 / 修改订阅、不标记已读 / 星标、不发布内容），也不生成业务输出文件。

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

- 本仓库由 `miniflux-mcp-skill` 于 v0.2.0 更名重定位为 `news-report`（当前版本 v0.2.1）；后续新增 / 修改模块请遵守「信息源模块化架构」与「通用约定」，并同步 CHANGELOG。
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

### 扩展模块示例（规划中模块参考）

以下为规划中模块的**假设性**设计，用于展示模块章节应包含的内容结构：

#### 模块 02 · `rss-http`（直接抓取 RSS/Atom 源）

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

> **勿将上述参数名当作可用工具调用**：本示例仅展示未来模块章节的结构，模块 02 当前不存在任何工具。

**常用工作流**（示意，非可执行）：
```
# 示意：抓取某博客的最新 10 篇文章
fetch feed from "https://example.com/feed.xml" with limit 10
```

**排障**：
- `Invalid feed format`：确认 URL 返回的是有效的 RSS/Atom XML。
- `HTTP 429 Too Many Requests`：添加延迟、轮换 User-Agent 或使用缓存。

> **注意**：以上内容仅为示例，**非当前实现**。实际开发时需基于 RSS 解析最佳实践（处理编码、`content:encoded` 提取、限速等）完成。

## 版本信息

- **Skill 版本**：v0.2.1 —— 修复工具签名与参数表（补全 `changed_before` / `changed_after`、`before_entry_id` / `after_entry_id`、`status` 取值），新增「高级指南」章节（架构/模块开发/测试/部署/安全/性能/排障/扩展示例）。
  - v0.2.0 为仓库更名重定位（`miniflux-mcp-skill` → `news-report`，引入模块化架构与通用约定）；输出格式待下一阶段设计。
- **Skill 创建**：2026-08-01（原 miniflux-mcp-skill v0.1.0 发布时记录，保留）
- **MCP Server（模块 01）**：miniflux-mcp v0.0.12（方案 B 含 Basic Auth 补丁）

## 来源

- **MCP Server（模块 01）**：[github.com/tan-yong-sheng/miniflux-mcp](https://github.com/tan-yong-sheng/miniflux-mcp) · [npm: miniflux-mcp](https://www.npmjs.com/package/miniflux-mcp)
- **Miniflux API**：[docs.miniflux.app](https://docs.miniflux.app)
- **License**: CC BY-NC-SA 4.0
