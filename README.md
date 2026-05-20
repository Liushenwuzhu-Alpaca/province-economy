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
│   └── server/              # FastAPI + ECharts 交互式仪表盘
├── data/
│   ├── raw/                 # NBS 官方 CSV 原始数据
│   └── results/             # 分析结果缓存
├── data_cache/              # 清洗后的指标 CSV + GeoJSON
└── output/                  # 生成的图表（PNG + HTML）
```

## 开发中

| 功能             | 说明                                                       |
| ---------------- | ---------------------------------------------------------- |
| Agent 智能对话   | 基于 RAG 的省域经济数据问答助手，接入仪表盘对话框             |

## 技术栈

| 模块           | 技术                               |
| -------------- | ---------------------------------- |
| 数据分析       | NumPy, Pandas, Scikit-learn        |
| 静态可视化     | Matplotlib                         |
| 交互式仪表盘   | FastAPI, Uvicorn, ECharts          |
| 容器化部署     | Docker, Docker Compose, nginx      |
| 向量数据库     | ChromaDB                           |
| 包管理         | uv                                 |

## 数据说明

原始数据来自国家统计局公开数据，覆盖 2019–2024 年。清洗后的指标缓存位于
`data_cache/indicators_{year}.csv`，含 31 省 × 15 个经济指标列。

详细的数据说明和指标定义见 `data/README.md` 和 `src/config.py`。
