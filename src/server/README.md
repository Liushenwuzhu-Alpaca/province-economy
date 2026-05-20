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

所有端点均返回 JSON（除 `/` 返回 HTML 页面）。服务默认监听 `http://localhost:8765`。

### GET / — 仪表盘页面

返回交互式仪表盘 HTML 页面，浏览器打开即可使用。

---

### GET /api/data?year={year}

返回指定年份的完整仪表盘数据集。

**参数**:
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| year | int  | 2024   | 分析年份 |

**行为**:
- 如果 `data/results/{year}_pca/scores.csv` 存在 → 直接返回缓存数据（毫秒级）
- 如果该年份数据不存在 → **自动运行 `main.py --year {year}` 生成数据**，等待分析完成后返回（首次 10–30 秒，后续秒出）

**请求示例**:
```bash
# 查询 2024 年数据
curl 'http://localhost:8765/api/data?year=2024'

# 查询 2023 年数据（首次自动跑分析）
curl 'http://localhost:8765/api/data?year=2023'
```

**返回结构**:
```json
{
  "scores": {
    "provinces": ["广东","江苏",...],    // 31 省短名
    "scores": [100.0, 80.94, ...],       // 综合得分 (0–100)
    "ranks": [1, 2, ...]                 // 排名
  },
  "clusters": {
    "provinces": [...],                  // 31 省短名
    "labels": [0,1,2,3,...],             // 聚类标签 (0=第一梯队)
    "tier_names": ["第一梯队(发达型)",...]  // 中文梯队名
  },
  "radar": {
    "provinces": [...],                  // 31 省短名
    "indicators": ["GDP总量","GDP增速",...], // 10 个指标中文名
    "values": [[0.87,0.62,...], ...]     // 31×10 归一化值 [0,1]
  },
  "ranking": {
    "rankings": [
      {"province": "广东", "score": 100.0, "rank": 1},
      ...
    ]
  },
  "geojson": { /* GeoJSON FeatureCollection — 34 个省份边界 */ }
}
```

---

### GET /api/years

返回所有可用分析年份列表。

**请求示例**:
```bash
curl http://localhost:8765/api/years
```

**返回示例**:
```json
{"years": [2023, 2024]}
```

年份按升序排列，由服务端扫描 `data/results/*_pca/` 目录自动发现。

---

### GET /static/* — 静态资源

前端 JS/CSS 文件，挂载在 `/static` 路径下。

| 文件 | URL |
|------|-----|
| ECharts 仪表盘脚本 | `/static/app.js` |
| 样式表 | `/static/style.css` |

---

## Agent / RAG 开发者调用指南

如果你在开发 Agent 或 RAG 模块，通过调用仪表盘接口获取省域经济数据：

```python
import requests

BASE = "http://localhost:8765"

# 1. 获取可用年份
years = requests.get(f"{BASE}/api/years").json()["years"]
# → [2023, 2024]

# 2. 获取某年完整数据
data = requests.get(f"{BASE}/api/data", params={"year": 2024}).json()

# 3. 提取关键字段
top5 = sorted(data["ranking"]["rankings"], key=lambda x: x["rank"])[:5]
# → [{"province":"广东","score":100.0,"rank":1}, ...]

# 4. 查询某省所有指标
province_idx = data["radar"]["provinces"].index("广东")
guangdong_radar = dict(zip(data["radar"]["indicators"], data["radar"]["values"][province_idx]))
# → {"GDP总量": 0.95, "GDP增速": 0.72, ...}
```

**注意**: 首次查询新年份时，服务会自动触发分析流水线（`main.py --year`），请求会阻塞 10–30 秒直到数据生成完毕。后续查询该年份为毫秒级响应。

---

## 数据依赖

服务运行时依赖以下数据文件：

| 数据 | 路径 |
|------|------|
| PCA 综合得分 | `data/results/{year}_pca/scores.csv` |
| 聚类结果 | `data/results/{year}_pca/clusters.csv` |
| 原始指标 | `data_cache/indicators_{year}.csv` |
| 省界 GeoJSON | `data_cache/china_provinces.geojson` |

**不需要手动预生成数据**: `/api/data` 端点会自动检测数据文件是否存在，缺失则自动运行 `uv run python main.py --year {year}` 生成。GeoJSON 文件仍需确保存在于 `data_cache/` 目录中。
