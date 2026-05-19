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

当前仅 backend（分析引擎）可用，frontend 和 chromadb 为预留占位。

### 数据说明

- `data_cache/` — 预处理后的指标数据已内置于镜像中，无需额外挂载
- `data/results/` — 分析结果通过 volume 挂载输出到宿主机，持久化保存

### 镜像信息

- 基础镜像: `python:3.11-slim-bookworm`
- 包管理器: uv
- 镜像大小: 约 300MB（已剥离 OpenCV/RapidOCR 等 OCR 依赖）
- 运行用户: 非 root（appuser）
