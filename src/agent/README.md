# Agent 模块 — AI 智能助手

## 概述

本模块是省域经济综合竞争力评价系统的 AI 对话助手，支持用户用自然语言查询 31 个省份的经济排名、指标数据、梯队分类等信息，并能自动切换仪表盘图表配合展示。

## 功能清单

| 功能       | 说明                                                         |
|------------|--------------------------------------------------------------|
| 自然语言问答 | 用户直接提问，AI 调用工具查询数据后生成回答                    |
| 7 个数据工具 | 排名查询、省份详情、梯队分类、指标权重、跨年对比、知识检索、图表切换 |
| RAG 知识增强 | ChromaDB 向量检索 8 篇知识文档，注入 system prompt 补充背景     |
| 双 API 后端 | Anthropic SDK / OpenAI SDK，通过 `.env` 切换                   |
| SSE 流式输出 | 实时逐字返回回答，支持工具调用事件推送                          |
| 图表联动    | AI 自动调用 `show_chart` 切换仪表盘上方图表，支持省份聚焦        |
| Token 管理  | tiktoken 计数 + 滑动窗口裁剪，防止超上下文                     |
| 生产级韧性  | 指数退避重试、JSON 结构化日志、输入校验、SSE 心跳重连            |

---

## 原理说明

### 整体架构

```
用户提问
  │
  ▼
┌──────────────────────────────────┐
│  agent.py  (调度层)               │
│  ┌───────────┐   ┌─────────────┐ │
│  │ Anthropic │   │   OpenAI    │ │
│  │  Backend  │   │  Backend    │ │
│  └─────┬─────┘   └──────┬──────┘ │
│        └────────┬───────┘        │
│                 ▼                 │
│          Tool Calling 循环        │
│    (最多 8 轮，每轮可调用多工具)   │
└───────┬────────┬─────────────────┘
        │        │
   ┌────▼───┐  ┌─▼────────┐  ┌──────────────┐
   │tools.py│  │ rag.py   │  │token_counter │
   │ CSV数据 │  │ 向量检索  │  │  token 裁剪   │
   │ 查询   │  │          │  │              │
   └────────┘  └──────────┘  └──────────────┘
```

### 核心原理：Tool Calling（工具调用）

LLM 本身只擅长生成文本，不擅长精确计算和查数据。Tool Calling 让模型可以"调用函数"：

1. 我们在 API 请求中告诉模型："你有 7 个工具可以用"（名称、参数、描述）
2. 模型判断用户问题需要数据时，返回一个工具调用请求（如 `get_ranking(year=2024)`）
3. 我们的代码执行这个工具，拿到真实数据，把结果发回给模型
4. 模型拿到数据后，生成包含精确数字的自然语言回答

这个循环最多跑 8 轮（`MAX_TURNS`），每轮可以同时调用多个工具。

### 核心原理：RAG（检索增强生成）

LLM 的知识有截止日期，也不知道我们项目的具体数据。RAG 的思路是：**先检索相关知识，再让模型参考这些知识回答**。

```
用户问题 "广东为什么排名下降？"
        │
        ▼
   文本向量化（bge-small-zh-v1.5）
        │
        ▼
   ChromaDB 余弦相似度检索 top-3
        │
        ▼
   匹配到知识片段：
   - [yearly_context.md] "2022年疫情对广东外贸冲击..."
   - [cross_year_analysis.md] "广东2022→2023排名从第1降至第2..."
        │
        ▼
   拼入 system prompt 作为背景知识
        │
        ▼
   模型参考这些片段生成回答
```

**为什么用 RAG 而不是把知识直接写进 prompt？** 知识文档总共约 2 万字，全塞进 prompt 会浪费 token 且效果差。RAG 只检索最相关的 3 段，精准且省钱。

### 核心原理：SSE 流式传输

传统 HTTP 是请求-响应模式，用户要等模型全部生成完才能看到结果。SSE（Server-Sent Events）让服务器可以持续推送：

```
浏览器 ←── SSE 连接 ──→ FastAPI 服务器
        ← event: token  {"text": "根据"}
        ← event: token  {"text": "2024年"}
        ← event: token  {"text": "数据..."}
        ← event: tool   {"name": "show_chart", ...}
        ← event: done   {}
```

前端用 `EventSource` API 监听这些事件，逐字渲染回答，遇到 `tool` 事件则切换图表。

### 核心原理：双 API 后端

不同大模型厂商的 API 格式不同。本模块通过 `API_TYPE` 环境变量实现双后端：

- **anthropic 后端**：使用 Anthropic Python SDK，兼容 DeepSeek、智谱等 Anthropic 协议端点
- **openai 后端**：使用 OpenAI Python SDK，兼容智谱 GLM、GPT 等 OpenAI 协议端点

两个后端的 Tool Calling 格式不同（Anthropic 用 `content blocks`，OpenAI 用 `function`），但对外暴露统一的 `chat()` / `chat_stream()` 接口。

---

## RAG 知识库详解

### 知识文档

`knowledge/` 目录下 8 篇 Markdown 文档，由我根据以下来源整理编写：

- **项目自身数据**：`data/results/` 下的排名、权重、聚类结果，用于编写实验分析和跨年对比
- **国家统计局公开数据**：各省统计年鉴、年度经济公报中的 GDP、产业、财政等指标
- **网络公开资料**：各省经济年报解读、产业政策分析、疫情影响报道等

整理后以 Markdown 格式撰写，确保内容与项目计算结果一致。这些文档是纯文本，不依赖任何外部服务，已直接提交到代码仓库中。

| 文件                                                   | 内容                           |
|--------------------------------------------------------|--------------------------------|
| `methodology.md`                                       | 熵权法与 PCA/K-Means 方法论说明 |
| `provinces_profile.md`                                 | 各省经济概况                   |
| `experiment_results.md`                                | 实验结果分析                   |
| `yearly_context.md`                                    | 2019-2024 年度经济背景         |
| `cross_year_analysis.md`                               | 跨年对比分析                   |
| `guangdong_analysis.md`                                | 广东省案例深度分析             |
| `events_2022_pandemic.md`                              | 2022 疫情影响分析             |
| `中国各省经济产业财政常识清单_2019-2024_知识整理版.md`  | 常识参考                       |

### 向量化流程

1. **分块**：每篇文档按 500 字符切分，相邻块重叠 100 字符（防止关键信息被截断），在换行符处断句
2. **嵌入**：使用 `BAAI/bge-small-zh-v1.5` 中文嵌入模型（512 维向量），将每个文本块转为一串数字
3. **存储**：存入 ChromaDB 向量数据库（本地持久化，存在 `chroma_db/` 目录）
4. **检索**：用户提问时，同样将问题转为向量，用余弦相似度找最接近的文本块

**嵌入模型选择**：`BAAI/bge-small-zh-v1.5` 是北京智源研究院开源的中文专用嵌入模型，在 MTEB 中文排行榜前列。相比 ChromaDB 默认的英文模型 `all-MiniLM-L6-v2`，中文语义匹配效果好很多。

---

## 首次运行指南

拿到项目后，Agent 模块需要以下前置步骤才能正常工作：

### 1. 安装依赖

```bash
uv sync
```

这会安装所有依赖，包括 `chromadb`、`sentence-transformers`、`tiktoken` 等。

### 2. 准备数据分析结果（前置条件）

Agent 的工具函数读取的是 `data/results/` 和 `data_cache/` 下的 CSV 文件。这些文件**不是 Agent 模块生成的**，而是由数据处理模块（`src/data/` + `src/models/`）生成的。

如果这些目录为空，需要先运行主流程：

```bash
# 生成所有年份的分析结果（scores.csv, clusters.csv, weights.csv 等）
uv run python main.py --year 2024
```

运行后确认以下文件存在：

```
data/results/2024_pca/scores.csv
data/results/2024_pca/clusters.csv
data/results/2024_pca/weights.csv
data_cache/indicators_2024.csv
```

### 3. 构建 RAG 向量索引

知识文档（`knowledge/*.md`）已包含在代码仓库中，但向量索引（`chroma_db/`）是 gitignore 的，需要本地构建：

```bash
uv run python -c "from src.agent.rag import build_index; build_index()"
```

首次运行会自动下载嵌入模型（约 90MB），**需要网络能访问 HuggingFace**（开梯子或直连均可）。模型下载后会缓存到本地，之后运行不需要联网。如果已构建过索引则跳过此步。

### 4. 配置 API Key

复制 `.env.example` 为 `.env`，填入 API 配置：

```bash
cp .env.example .env
```

```bash
# .env 内容
API_TYPE=anthropic
ANTHROPIC_API_KEY=sk-your-key
ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
ANTHROPIC_MODEL=deepseek-v4-flash
```

**推荐 DeepSeek V4 Flash**：便宜（约 ¥1/百万 token），Tool Calling 稳定，中文能力强。注册地址：https://platform.deepseek.com

备选方案：

| 厂商     | BASE_URL                              | 模型           | 备注         |
|----------|---------------------------------------|----------------|--------------|
| DeepSeek | `https://api.deepseek.com/anthropic`  | `deepseek-v4-flash` | 推荐，便宜好用（特别骚） |
| 智谱 GLM | `https://open.bigmodel.cn/api/anthropic` | 需查文档       | 需要 Anthropic 兼容端点 |
| OpenAI   | —                                     | `gpt-4o`       | 设置 `API_TYPE=openai` |

### 5. 启动服务

```bash
uv run python -m src.server.main
```

打开浏览器访问 `http://localhost:8765`，在下方对话框中提问即可。

### 常见问题

**Q: 提示"当前大模型 API 未配置"**
A: 检查 `.env` 文件是否存在且 `ANTHROPIC_API_KEY` 已填写。

**Q: 提示"API 调用失败: 401"**
A: API Key 无效或过期。如果系统环境变量中有同名变量会覆盖 `.env`，确认 `.env` 中有 `override` 生效（代码已处理）。

**Q: 工具返回"不支持该年份"**
A: 该年份的数据分析结果未生成，先运行 `uv run python main.py --year 对应年份`。

---

## 对外接口

### 1. Python API

```python
from src.agent.agent import chat, chat_stream

# 非流式调用
response: str = chat("2024年广东排名第几？", history=[...])

# 流式调用 (SSE)
for event in chat_stream("对比广东和江苏", history=[...]):
    print(event)  # "event: token\ndata: {...}\n\n"
```

- `chat(message, history=None) -> str` — 同步对话，返回完整文本
- `chat_stream(message, history=None) -> Generator[str]` — 流式对话，yield SSE 格式字符串

`history` 为 `list[dict]`，每条 `{"role": "user" | "assistant", "content": "..."}`

### 2. HTTP 接口（由 `src/server/main.py` 暴露）

```text
POST /api/chat
Content-Type: application/json

{
  "message": "2024年广东排名第几？",
  "history": [{"role": "user", "content": "..."}, ...]
}
```

响应为 SSE 流，事件类型：

| 事件     | 数据                               | 说明               |
|----------|------------------------------------|--------------------|
| `token`  | `{"text": "..."}`                  | 文本片段，逐字推送 |
| `tool`   | `{"name": "...", "input": {...}}`  | 工具调用事件       |
| `done`   | `{}`                               | 流结束             |
| `error`  | `{"text": "..."}`                  | 错误信息           |

### 3. 工具列表

| 工具名                | 参数                                | 数据来源                  | 说明             |
|-----------------------|-------------------------------------|---------------------------|------------------|
| `get_ranking`         | `year`, `top_n`                     | `scores.csv`              | 查询排名         |
| `get_province_detail` | `province`, `year`                  | `indicators_{year}.csv`   | 省份详细指标     |
| `get_cluster_members` | `year`, `label`                     | `clusters.csv`            | 梯队成员         |
| `get_weights`         | `year`                              | `weights.csv`             | 熵权法指标权重   |
| `compare_years`       | `province`                          | 全部 `scores.csv`         | 跨年排名对比     |
| `search_knowledge`    | `query`                             | ChromaDB                  | 语义检索知识库   |
| `show_chart`          | `chart_type`, `year`, `provinces`   | UI 控制                   | 切换仪表盘图表   |

### 4. show_chart 与前端联动

前端 `app.js` 监听 SSE `tool` 事件，当工具名为 `show_chart` 时调用 `switchChart()` 切换图表。

支持的 `chart_type`：`ranking`（排名柱状图）、`scoreMap`（热力地图）、`tierMap`（梯队地图）、`radar`（雷达图）、`trend`（趋势折线图）。

`provinces` 参数控制图表聚焦：排名图滚动到指定省份，雷达图/趋势图默认只显示指定省份的图例。

---

## 文件结构

```text
src/agent/
├── __init__.py          # 模块入口，导出 chat / chat_stream
├── agent.py             # 核心调度：双后端、Tool Loop、SSE 流式
├── tools.py             # 7 个工具函数定义 + Anthropic Schema
├── rag.py               # ChromaDB 索引构建 + 语义检索
├── token_counter.py     # tiktoken 计数 + 历史裁剪
├── logger.py            # JSON 结构化日志（控制台 + 文件）
├── knowledge/           # 8 篇知识文档（RAG 数据源）
└── chroma_db/           # 向量索引（gitignored，需 build_index 构建）
```

## 测试

测试前需确保：
1. 已运行 `uv run python main.py --year 2024` 生成数据分析结果（`data/results/`）
2. 已构建 RAG 向量索引（首次需联网下载嵌入模型）：
   ```bash
   uv run python -c "from src.agent.rag import build_index; build_index()"
   ```

```bash
# 工具 + RAG 单元测试（不需要 API Key）
uv run pytest tests/test_tools.py tests/test_rag.py -v

# Agent 端到端测试（需要 .env 配置可用 API Key）
RUN_LIVE_TESTS=1 uv run pytest tests/test_agent_eval.py -v
```

## 依赖

本模块额外引入的依赖（已写入 `pyproject.toml`）：

| 包                      | 用途                                 |
|-------------------------|--------------------------------------|
| `chromadb`              | 向量数据库，存储和检索知识文档         |
| `sentence-transformers` | 加载嵌入模型（bge-small-zh-v1.5）    |
| `tiktoken`              | Token 计数，用于消息历史裁剪          |
| `python-dotenv`         | 读取 .env 配置文件                    |
| `pandas`                | 工具函数读取 CSV 数据                 |
