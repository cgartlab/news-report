---
name: miniflux-mcp-skill
description: >-
  Integrate the Miniflux RSS reader into your AI agent via the miniflux-mcp MCP
  server — browse feeds and categories, search entries, and read unread or
  starred articles directly from conversations. Use when the user asks to read
  RSS feeds, check subscriptions, search articles, fetch unread or starred
  items, or mentions "Miniflux", "RSS", "feeds", "订阅" with the Miniflux MCP
  server available.
---

# Miniflux MCP Skill

## 概述

此 Skill 将 [Miniflux](https://miniflux.app) RSS 阅读器接入 AI Agent：通过 [miniflux-mcp](https://github.com/tan-yong-sheng/miniflux-mcp) MCP 服务器，在对话中直接浏览分类与订阅源、搜索文章、查看未读与星标，无需切换到浏览器。

**核心能力**：

- 列出分类与订阅源，查看未读 / 文章计数
- 按分类、订阅源或关键词搜索文章（全文搜索）
- 浏览未读、星标文章，支持分页与排序
- 模糊解析名称 / 数字 ID 到 `category_id` / `feed_id`

**边界**：此 Skill **只读**——仅检索 Miniflux 数据，不创建或修改订阅源、不标记文章、不写任何内容。

## 前置条件

- 一个可访问的 Miniflux 实例（自托管或托管），且已登录
- Node.js **>= 18.17**（miniflux-mcp 依赖全局 `fetch`）
- 在 opencode 中注册 miniflux-mcp MCP 服务器（见下）

## 配置 MCP 服务器

### 方案 A：npx 直接运行（推荐）

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
        "MINIFLUX_TOKEN": "你的 API Token"
      }
    }
  }
}
```

> 说明：`command` 必须是字符串数组；`type` 必填（此处为 `local`）。`npx` 每次启动会自动获取 npm 最新版；如需固定版本，改用 `["npx", "-y", "miniflux-mcp@0.0.12"]`。

### 方案 B：本地安装 + Basic Auth 补丁（可选）

部分 Miniflux 实例或用户偏好使用用户名 / 密码（Basic Auth）而非 API Token。上游包不支持 Basic Auth，需要对本地安装的 `dist/server.js` 打补丁。

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

随后把 MCP `command` 指向补丁后的文件：

```json
{
  "mcp": {
    "miniflux-mcp": {
      "type": "local",
      "command": ["node", "C:\\Users\\YOUR_USER\\.config\\opencode\\miniflux-mcp-server\\node_modules\\miniflux-mcp\\dist\\server.js"],
      "enabled": true,
      "env": {
        "MINIFLUX_BASE_URL": "https://miniflux.example.com",
        "MINIFLUX_USERNAME": "your_username",
        "MINIFLUX_PASSWORD": "your_password"
      }
    }
  }
}
```

Linux / macOS 使用：`"command": ["node", "/home/YOUR_USER/.config/opencode/miniflux-mcp-server/node_modules/miniflux-mcp/dist/server.js"]`

## 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `MINIFLUX_BASE_URL` | ✅ | Miniflux 实例地址，**不含** `/v1`（服务器内部追加）。示例：`https://miniflux.example.com` |
| `MINIFLUX_TOKEN` | ⚠️ | API Token（Miniflux 设置 → API Keys 生成）。方案 A 必须 |
| `MINIFLUX_USERNAME` | ⚠️ | Basic Auth 用户名（方案 B，与 TOKEN 二选一） |
| `MINIFLUX_PASSWORD` | ⚠️ | Basic Auth 密码（与 USERNAME 搭配使用） |

> 认证优先级：`MINIFLUX_TOKEN` > `MINIFLUX_USERNAME` + `MINIFLUX_PASSWORD`。两者都配置时，Token 优先。

## 可用工具

| 工具 | 说明 |
|------|------|
| `listCategories(counts?)` | 列出所有分类。`counts: true` 附带未读 / 文章计数（需 Miniflux 2.0.46+） |
| `listFeeds()` | 列出全部订阅源（含所属分类） |
| `searchFeedsByCategory(category_id, query?)` | 在指定分类内按标题 / 站点 URL / 订阅 URL 过滤订阅源（不区分大小写） |
| `resolveId(query, limit?)` | 按名称或数字 ID 模糊匹配分类与订阅源 |
| `searchEntries(...)` | 全局全文搜索，或按 `category_id` / `feed_id` 限定范围 |

### searchEntries 参数

| 参数 | 说明 |
|------|------|
| `search` | 全文关键词 / 短语。**不支持** `AND` / `OR` 等布尔运算符 |
| `category_id` / `feed_id` | 限定搜索范围（可选） |
| `status` | 状态过滤，逗号分隔多值，如 `"read,unread"` |
| `starred` | 仅星标文章（布尔） |
| `limit` / `offset` | 分页 |
| `order` | 排序字段：`id`、`status`、`published_at`、`category_title`、`category_id` |
| `direction` | `asc` / `desc` |
| `before` / `after` | 创建时间过滤（Unix 秒或 `YYYY-MM-DD` / ISO 日期） |
| `published_before` / `published_after` | 发布时间过滤（同上） |

## 常用工作流

### 按分类查看未读文章

```
listCategories({ counts: true })
→ searchEntries({ category_id: 14, status: "unread", limit: 10 })
```

### 找到某个订阅源并浏览文章

```
resolveId({ query: "Hacker News" })
→ searchEntries({ feed_id: 42, limit: 5 })
```

### 按主题搜索文章

```
searchEntries({ search: "Rust programming", status: "unread", limit: 10 })
```

### 浏览星标文章

```
searchEntries({ starred: true, limit: 10 })
```

## 排障

| 问题 | 解决 |
|------|------|
| `access unauthorized` | 检查凭据。Token 认证失败时可改用方案 B 的 Basic Auth |
| `404 page not found` | 确认 `MINIFLUX_BASE_URL` **不含** `/v1`，服务器会自行追加 |
| `Cannot find package '@modelcontextprotocol/sdk'` | 在服务器目录执行 `npm install` 补装依赖 |
| 服务器无法启动 | 确认 Node.js >= 18.17，并检查 `command` 路径是否正确 |
| 方案 B 升级后 Basic Auth 失效 | `npm update` 会覆盖补丁，需重新执行打补丁步骤 |

## 维护提示

- 方案 B 的 Basic Auth 补丁是本地改动，**不随 npm 包分发**；升级 `miniflux-mcp` 后必须重新打补丁。
- 上游 miniflux-mcp 为只读服务器，且只支持 API Token；如上游后续原生支持 Basic Auth，可放弃方案 B。
- 若不确定搜索意图（`search` 是关键词还是某个订阅源名称），先向用户澄清，避免误判。

## 版本信息

- **MCP Server**: miniflux-mcp v0.0.12（方案 B 含 Basic Auth 补丁）
- **Skill 创建**: 2026-08-01

## 来源

- **MCP Server**: [github.com/tan-yong-sheng/miniflux-mcp](https://github.com/tan-yong-sheng/miniflux-mcp) · [npm: miniflux-mcp](https://www.npmjs.com/package/miniflux-mcp)
- **Miniflux API**: [docs.miniflux.app](https://docs.miniflux.app)
- **License**: CC BY-NC-SA 4.0
