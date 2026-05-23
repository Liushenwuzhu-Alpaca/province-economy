# 省域经济综合竞争力评价

基于熵权法 + PCA + K-Means 的中国省域经济综合竞争力评价系统。
支持静态图表输出（适配 PPT / 报告）和交互式 Web 仪表盘。

覆盖 2019–2024 年 31 个省/自治区/直辖市，15 个经济指标。

## 快速开始

### 安装

```bash
uv sync
```

### 运行分析

```bash
# 分析 2024 年数据（默认）
uv run python main.py

# 指定年份
uv run python main.py --year 2023

# 强制重新计算（跳过缓存）
uv run python main.py --year 2024 --recompute

# 不使用 PCA 降维
uv run python main.py --year 2024 --no-pca
```

### 生成静态图表（PNG + HTML，用于 PPT / 报告）

```bash
# 单年图表 → output/ 目录
uv run python main.py --viz --year 2024

# 所有年份 + 跨年趋势图
uv run python main.py --all-years --viz
```

### 启动交互式仪表盘

```bash
uv run python -m src.server.main
```

浏览器访问 **http://localhost:8765**。

仪表盘 API 端点：`/api/data?year=2024`、`/api/years`、`/api/trend`。

## Docker 部署

使用 Docker Compose 一键部署三容器架构：

- **nginx**：前端静态资源 + 反向代理（端口 80）
- **backend**：FastAPI 分析服务（内部 8765）
- **chromadb**：向量数据库（内部 8000），用于 RAG 智能问答

```bash
# 启动全部服务
docker compose up -d

# 查看日志
docker compose logs -f

# 停止并清理
docker compose down
```

启动后访问 **http://localhost:80**，nginx 会将 `/` 路由到仪表盘前端，
`/api/*` 反向代理到 FastAPI 后端。

### 演示

```bash
curl -fsSL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared
chmod +x cloudflared
```

下载并运行 Cloudflare Tunnel，将本地 80 端口暴露到公网：
```bash
./cloudflared tunnel --url http://localhost:80
```

然后访问生成的临时公网IP即可

## 项目结构

```
├── main.py                  # CLI 入口
├── pyproject.toml           # 项目配置与依赖
├── Dockerfile               # 后端容器镜像
├── docker-compose.yml       # 三容器编排
├── .dockerignore            # Docker 构建忽略文件
├── nginx/
│   └── default.conf         # nginx 反向代理配置
├── src/
│   ├── config.py            # 省份列表、指标定义、路径常量
│   ├── data/                # 数据读取、清洗、缓存
│   ├── models/              # 熵权法 + PCA + K-Means 分析模型
│   ├── visualization/       # Matplotlib 静态图表（PNG + HTML）
│   ├── server/              # FastAPI + ECharts 交互式仪表盘
│   └── agent/               # AI 智能助手模块
│       ├── agent.py         #   核心调度：双 API 后端 + Tool Calling + SSE 流式
│       ├── tools.py         #   7 个数据查询工具
│       ├── rag.py           #   ChromaDB 向量检索（bge-small-zh-v1.5 中文模型）
│       ├── token_counter.py #   tiktoken Token 管理
│       ├── logger.py        #   JSON 结构化日志
│       └── knowledge/       #   8 篇知识文档（RAG 数据源）
├── data/
│   ├── raw/                 # NBS 官方 CSV 原始数据
│   └── results/             # 分析结果缓存
├── data_cache/              # 清洗后的指标 CSV + GeoJSON
└── output/                  # 生成的图表（PNG + HTML）
```

## AI 智能助手

仪表盘下方的对话框接入了 AI Agent，支持自然语言提问。Agent 通过 Tool Calling 调用 7 个数据工具查询精确数据，通过 RAG 检索知识库补充背景解释，并能自动切换仪表盘上方图表配合展示。

详细说明见 [src/agent/README.md](src/agent/README.md)。

### 功能

- **Tool Calling**：AI 自动调用排名查询、省份详情、梯队分类等 7 个工具获取精确数据
- **RAG 知识增强**：ChromaDB 向量检索 8 篇知识文档，注入 system prompt 补充背景
- **图表联动**：AI 回答时自动切换仪表盘图表（排名、热力图、雷达图等），聚焦到用户关心的省份
- **SSE 流式输出**：回答实时逐字生成，支持 Markdown 渲染
- **双 API 后端**：Anthropic SDK / OpenAI SDK，通过 `.env` 切换
- **Token 管理**：tiktoken 计数 + 滑动窗口裁剪，防止超上下文

### 首次使用

1. 运行数据分析生成 CSV 缓存：`uv run python main.py --year 2024`
2. 构建 RAG 向量索引：`uv run python -c "from src.agent.rag import build_index; build_index()"`
3. 配置 API Key：`cp .env.example .env`，填入密钥（推荐 DeepSeek V4 Flash）
4. 启动服务：`uv run python -m src.server.main`

### 配置

复制 `.env.example` 为 `.env`，填入 API 密钥：

```bash
cp .env.example .env
```

支持两种 API 后端（通过 `API_TYPE` 切换）：

| API_TYPE          | 说明                                   | 配置项                                              |
| ----------------- | -------------------------------------- | --------------------------------------------------- |
| `anthropic`（默认） | Anthropic 协议（DeepSeek、智谱等兼容） | `ANTHROPIC_API_KEY`, `ANTHROPIC_BASE_URL`, `ANTHROPIC_MODEL` |
| `openai`          | OpenAI 协议（智谱GLM、GPT等）         | `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`        |

**推荐**：DeepSeek V4 Flash，便宜（约 ¥1/百万 token），Tool Calling 稳定，中文能力强。

### 示例问题

- "广东排名第几？" → AI 调用 `get_ranking` 查数据，切换到排名图并滚动到广东
- "2024年北京和上海谁更强？" → AI 调用 `get_province_detail` 对比，切换到雷达图
- "第一梯队有哪些省？" → AI 调用 `get_cluster_members` 查梯队，切换到梯队地图
- "吉林省排名有什么变化？" → AI 调用 `compare_years` 查跨年趋势，切换到趋势折线图
- "熵权法是怎么计算权重的？" → AI 通过 RAG 检索知识库回答方法论

## 技术栈

| 模块         | 技术                                         |
| ------------ | -------------------------------------------- |
| 数据分析     | NumPy, Pandas, Scikit-learn                  |
| 静态可视化   | Matplotlib                                   |
| 交互式仪表盘 | FastAPI, Uvicorn, ECharts                    |
| AI 智能助手  | Tool Calling, RAG, SSE 流式, 双 API 后端     |
| 向量数据库   | ChromaDB + BAAI/bge-small-zh-v1.5 中文嵌入   |
| Token 管理   | tiktoken                                     |
| 容器化部署   | Docker, Docker Compose, nginx                |
| 包管理       | uv                                           |

## 数据说明

原始数据来自国家统计局公开数据，覆盖 2019–2024 年。清洗后的指标缓存位于
`data_cache/indicators_{year}.csv`，含 31 省 × 15 个经济指标列。

详细的数据说明和指标定义见 `data/README.md` 和 `src/config.py`。
