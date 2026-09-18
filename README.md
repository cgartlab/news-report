# news-report

多源新闻采集与结构化报告 skill。从 RSS、网页搜索、Telegram 社区等模块化信源聚合信息，通过优先级评估，按严格模板输出新闻报告。

## 两条执行路径

### 1. Agent 直连（主路径）

用户触发 → Agent 读取 `SKILL.md` → 使用 `web_search` / `web_fetch` 等工具直接采集 → 按【输出模板】生成报告。

- **无需任何配置**，Agent 自带工具即可运行
- 格式权威标准 = `SKILL.md` →【输出模板】章节
- 触发词：新闻报告、日报、news report、简报、新闻汇总

### 2. Python 脚本 pipeline（离线兜底）

适合离线/批量场景，需先配置环境变量：

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env，填入至少一个 LLM API Key（MINIMAX / SILICONFLOW / DEEPSEEK）

# 2. 运行完整 pipeline
python src/main.py --full

# 3. 仅采集（不调 LLM 评估）
python src/main.py --collect-only

# 4. 仅评估（跳过 LLM，纯规则模式）
python src/main.py --full --skip-llm
```

输出：`output/latest.md`（最新报告）+ `output/YYYY-MM-DD-HHMM.md`（带时间戳归档）

## 配置

配置文件位于 `config/` 目录：

| 文件 | 说明 |
|---|---|
| `config/rss-sources.json` | RSS 源列表（24 个真实源） |
| `config/search-keywords.json` | 搜索关键词列表 |
| `config/telegram-channels.json` | Telegram 频道配置（需替换 `{CHANNEL_ID}` 占位） |
| `config/config.json` | 通用参数（每页条数、去重阈值等） |

## 目录结构

```
news-report/
├── SKILL.md              # 执行规范 + 输出模板（权威标准）
├── src/                  # Python 脚本链路（离线兜底）
│   ├── main.py           # 入口：collect → evaluate → dedup → report
│   ├── collect_rss.py    # RSS/Atom feed 采集
│   ├── collect_search.py # SearXNG 搜索采集
│   ├── collect_telegram.py # Telegram 频道消息采集
│   ├── evaluator.py      # 规则评分 + LLM 语义评估
│   ├── deduplicator.py   # Jaccard 语义去重
│   └── report.py         # 报告生成（SKILL.md 格式）
├── config/               # 配置文件
├── archive/prompts/      # 已归档的旧 prompt（仅供历史参考）
├── data/                 # 运行产物（items.jsonl，已 .gitignore）
├── output/               # 报告输出（已 .gitignore）
├── .env.example          # 环境变量模板
└── .gitignore
```

## 依赖

- Python 3.10+
- 无外部 Python 依赖（仅标准库）
- 可选：SearXNG 实例（搜索采集）
- 可选：telegram-history skill（Telegram 采集）

## 安全

- 源码不含任何硬编码 API Key
- 密钥通过环境变量注入（`.env` 文件，已 `.gitignore`）
- `.env` 文件不会被提交到版本控制
