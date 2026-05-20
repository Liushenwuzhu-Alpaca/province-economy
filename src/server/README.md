# src/server — 省域经济交互式仪表盘服务

基于 **FastAPI** + **ECharts** 的 Web 服务，提供省域经济综合得分的交互式可视化仪表盘。

## 目录结构

```
src/server/
├── __init__.py        # 包声明
├── main.py            # FastAPI 应用、路由、启动入口
├── data_api.py        # 数据加载与 JSON 序列化层
├── static/            # 前端静态资源（ECharts 仪表盘）
│   ├── index.html
│   ├── app.js
│   └── style.css
└── README.md
```

## 启动方式

```bash
# 在项目根目录下运行
uv run python -m src.server.main
```

浏览器访问 **http://localhost:8765** 即可打开仪表盘。

> 端口默认为 `8765`，在 `main.py` 底部可调整。

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 仪表盘 HTML 页面 |
| GET | `/api/data?year=2024` | 返回完整 JSON 数据集 |
| GET | `/static/*` | 前端静态资源 |

### `/api/data` 返回结构

```json
{
  "scores":   {"provinces": [...], "scores": [...], "ranks": [...]},
  "clusters": {"provinces": [...], "labels": [...], "tier_names": [...]},
  "radar":    {"provinces": [...], "indicators": [...], "values": [[...]]},
  "ranking":  {"rankings": [{"province": "...", "score": ..., "rank": ...}]},
  "geojson":  { /* GeoJSON FeatureCollection — 31 个省份 */ }
}
```

`year` 参数默认为 `2024`，控制聚类、得分和雷达数据的数据年份。

## 数据依赖

服务启动和 `/api/data` 调用需要以下数据文件存在：

| 数据 | 路径 |
|------|------|
| PCA 综合得分 | `data/results/{year}_pca/scores.csv` |
| 聚类结果 | `data/results/{year}_pca/clusters.csv` |
| 原始指标 | `data_cache/indicators_{year}.csv` |
| 省界 GeoJSON | `data_cache/china_provinces.geojson` |

如果文件缺失，API 会抛出 `FileNotFoundError`。确保在启动服务前已运行过分析流水线。
