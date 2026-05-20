## Docker 使用

### 快速开始

构建镜像:

```bash
docker build -t province-economy:latest .
```

运行分析（默认年份 2024）:

```bash
docker run --rm \
  -v $(pwd)/data/results:/app/data/results \
  province-economy:latest
```

### 命令行参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `--year 2024` | 指定分析年份（2023 或 2024） | `docker run ... --year 2023` |
| `--recompute` | 跳过缓存，强制重新计算 | `docker run ... --recompute` |
| `--no-pca` | 跳过 PCA 降维，直接聚类 | `docker run ... --no-pca` |

完整示例:

```bash
# 分析 2023 年数据，跳过缓存，不启用 PCA
docker run --rm \
  -v $(pwd)/data/results:/app/data/results \
  province-economy:latest python main.py --year 2023 --recompute --no-pca
```

### Docker Compose

使用 docker-compose 一键启动:

```bash
docker compose up --build
```

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

启动后访问 **http://localhost**，nginx 会将 `/` 路由到仪表盘前端，
`/api/*` 反向代理到 FastAPI 后端。

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
