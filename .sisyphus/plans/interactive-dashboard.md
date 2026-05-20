# 交互式省域经济仪表盘

## TL;DR
> **Quick Summary**: 在现有静态 PNG 输出之上，构建一个基于 ECharts + FastAPI 的前后端分离交互式仪表盘，支持热力图 hover、图表切换导航、以及 Agent 占位对话框。
>
> **Deliverables**:
> - FastAPI 数据 API 服务 (`src/visualization/server.py` + `data_api.py`)
> - ECharts 单页前端 (`src/visualization/static/`)
> - Agent 占位对话框（预留 RAG 接口）
>
> **Estimated Effort**: Medium
> **Parallel Execution**: YES - 2 waves
> **Critical Path**: data_api → server → frontend → verify

---

## Status Update (2026-05-20)

- **Docker deployment**: CANCELLED per user request. Remove any Docker-related tasks/objectives.
- **Service refactor**: NEW — extract service code to `src/server/` as a clean package, separate from `src/visualization/`.
- **Sprint goal**: refactor → verify → git commit.

---

## Context

### Original Request
> "可用，但我希望可以鼠标放上去交互，然后应该有个前端网页，可以旁边点按钮，切换所有展示内容，下面有个对话框，作为agent功能预设"

### Interview Summary
- **地图引擎**: ECharts（内置中国地图，hover tooltip，跨平台稳定）
- **Agent 对话框**: 先放占位 UI，以后接 RAG
- **交付形式**: 前后端分离（FastAPI + 静态前端）
- **保留现有**: 静态 PNG/HTML 输出继续用于 PPT 场景

### 现有资产
- `output/` 下 7 张 PNG（热力图、梯队、雷达×2、排名×3）
- `data/results/2024_pca/` 下 scores.csv + clusters.csv（可直接读为 JSON）
- `src/visualization/choropleth.py` 已改为 Matplotlib 静态渲染

---

## Work Objectives

### Core Objective
构建一个可通过浏览器访问的交互式仪表盘，用户可以在热力图/梯队/雷达/排名/趋势图之间切换，鼠标悬停查看数据详情。

### Concrete Deliverables
- `src/visualization/data_api.py` - 从缓存读取 scores/clusters/原始指标，导出 JSON
- `src/visualization/server.py` - FastAPI 服务，serve 静态文件 + `/api/*` 端点
- `src/visualization/static/index.html` - 仪表盘主页面（侧边导航 + 图表区 + 对话框）
- `src/visualization/static/app.js` - ECharts 渲染 + 图表切换逻辑
- `src/visualization/static/style.css` - 仪表盘样式
- 新增依赖: `fastapi`, `uvicorn`

### Must Have
- 中国地图热力图，鼠标 hover 显示省份名 + 得分
- 侧边导航按钮切换：热力图 / 梯队图 / 雷达图 / 排名榜 / 趋势图
- 底部 Agent 对话框占位（输入框 + 发送按钮，不接后端）
- `uv run python -m src.visualization.server` 一键启动

### Must NOT Have
- 不替换现有 `choropleth.py` 的静态 PNG 输出
- 不修改 `main.py --viz` 的行为
- Agent 不做实际 RAG（仅占位 UI）
- 前端不需要 build 工具链（纯 HTML/CSS/JS）

---

## Verification Strategy

### Test Decision
- **Infrastructure exists**: NO
- **Automated tests**: NO
- **Agent-Executed QA**: YES（Playwright 验证前端渲染 + Bash curl 验证 API）

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately - 数据层 + 后端):
├── Task 1: 添加 fastapi/uvicorn 依赖 [quick]  ✅
├── Task 2: 实现 data_api.py JSON 导出 [quick]  ✅
└── Task 3: 实现 server.py FastAPI 服务 [quick]  ✅

Wave 2 (After Wave 1 - 前端):
├── Task 4: 创建 index.html 仪表盘骨架 [visual-engineering]  ✅
├── Task 5-8: ECharts 全部图表 + Agent 对话框 [visual-engineering]  ✅

Wave 3 (NEW - 服务重构):
├── Task 9: 提取 server 到 src/server/ 独立包 [quick]  ⬜
└── Task 10: Git commit [quick]  ⬜

Wave FINAL:
└── Task F1: Playwright QA 验证 [visual-engineering]  ⬜
```

### Critical Path
Task 1 → Task 2/3 → Task 4/5 → Task 9 → Task 10 → F1

---

## TODOs

- [x] 1. 添加 FastAPI/uvicorn 依赖

  **What to do**:
  - 在 `pyproject.toml` 添加 `fastapi` 和 `uvicorn[standard]` 依赖
  - 运行 `uv lock` 更新锁文件
  - 验证: `uv run python -c "import fastapi, uvicorn"`

  **Must NOT do**:
  - 不加其他不需要的 Web 框架

  **Recommended Agent Profile**: `quick` / `installing-dependencies`
  **Parallelization**: Wave 1, blocks Task 2/3

  **QA Scenarios**:
  ```
  Scenario: 依赖安装验证
    Tool: Bash
    Steps:
      1. uv run python -c "import fastapi; print(fastapi.__version__)"
      2. uv run python -c "import uvicorn; print('uvicorn OK')"
    Expected Result: 输出版本号，无 ImportError
    Evidence: .sisyphus/evidence/task-1-deps.txt
  ```

- [x] 2. 实现 `data_api.py` JSON 数据导出层

  **What to do**:
  - 新建 `src/visualization/data_api.py`
  - 实现函数:
    - `load_scores_json(year=2024) -> dict` — 读取 scores.csv 返回 `{provinces: [...], scores: [...]}`
    - `load_clusters_json(year=2024) -> dict` — 读取 clusters.csv 返回 `{provinces: [...], labels: [...], tier_names: [...]}`
    - `load_radar_data(year=2024) -> dict` — 读取原始指标，做 CPI 转换 + Min-Max 归一化，返回 `{provinces: [...], indicators: [...], values: [[...], ...]}`
    - `load_ranking_json(year=2024) -> dict` — 返回 scores 排名列表
    - `load_geojson() -> dict` — 返回清洗后的 GeoJSON
    - `load_all_data(year=2024) -> dict` — 聚合所有数据，作为 `/api/data` 的统一响应
  - 数据源: `data/results/{year}_pca/` 和 `data_cache/indicators_{year}.csv`

  **Must NOT do**:
  - 不修改数据缓存文件
  - 不依赖 server.py

  **Recommended Agent Profile**: `quick` / `writing-python`
  **Parallelization**: Wave 1, depends on Task 1, blocks Task 3

  **QA Scenarios**:
  ```
  Scenario: JSON 导出正确性
    Tool: Bash (curl via server later, or direct Python test)
    Steps:
      1. python -c "from src.visualization.data_api import load_all_data; d = load_all_data(2024); print(len(d['scores']['provinces']))"
    Expected Result: 输出 31
    Evidence: .sisyphus/evidence/task-2-data.txt
  ```

- [x] 3. 实现 `server.py` FastAPI 服务

  **What to do**:
  - 新建 `src/visualization/server.py`
  - FastAPI app 配置:
    - `GET /` → 返回 `static/index.html`
    - `GET /api/data?year=2024` → 调用 `data_api.load_all_data()` 返回 JSON
    - `StaticFiles` mount `/static` → `src/visualization/static/`
    - CORS 开启（允许本地开发跨域）
  - 添加 `__main__` 入口: `uvicorn.run("src.visualization.server:app", host="0.0.0.0", port=8765, reload=True)`
  - 启动命令: `uv run python -m src.visualization.server`

  **Must NOT do**:
  - 不实现认证/鉴权
  - 不连接数据库

  **Recommended Agent Profile**: `quick` / `writing-python`
  **Parallelization**: Wave 1, depends on Task 2, blocks Task 4-8

  **QA Scenarios**:
  ```
  Scenario: API 返回正确数据
    Tool: Bash (curl)
    Steps:
      1. 后台启动 server: uv run python -m src.visualization.server &
      2. sleep 3
      3. curl -s http://localhost:8765/api/data?year=2024 | python -c "import json,sys; d=json.load(sys.stdin); print(len(d['scores']['provinces']))"
      4. kill %1
    Expected Result: 输出 31，JSON 包含 scores/clusters/radar/ranking/geojson 五个键
    Evidence: .sisyphus/evidence/task-3-api.json
  ```

---

- [x] 4. 创建仪表盘 HTML 骨架 + CSS 布局

  **What to do**:
  - 新建 `src/visualization/static/index.html`
  - 布局: 左侧 200px 导航栏 + 右侧图表主区域 + 底部 60px 对话框
  - CSS Flexbox 布局，暗色主题（参考 ECharts 官方仪表盘风格）
  - 引入 ECharts CDN: `https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js`
  - 引入中国地图: `https://cdn.jsdelivr.net/npm/echarts@5.5.0/map/js/china.js` (不需要额外 GeoJSON)
  - 导航按钮: 综合得分热力图 / 聚类梯队 / 雷达图 / 排名榜 / 趋势图
  - 页面标题: "省域经济综合竞争力仪表盘"
  - `src/visualization/static/style.css` — 所有样式

  **Must NOT do**:
  - 不引入 React/Vue 等框架
  - 不使用 npm/webpack

  **Recommended Agent Profile**: `visual-engineering` / `frontend-design`
  **Parallelization**: Wave 2, depends on Task 3

  **QA Scenarios**:
  ```
  Scenario: 页面骨架渲染
    Tool: Playwright
    Steps:
      1. page.goto('http://localhost:8765')
      2. 等待 .sidebar 和 .main-content 和 .chat-bar 三个元素出现
      3. 截图: .sisyphus/evidence/task-4-layout.png
    Expected Result: 三栏布局正确渲染，5 个导航按钮可见
    Evidence: .sisyphus/evidence/task-4-layout.png
  ```

- [x] 5. 实现 ECharts 热力图（得分地图）— 并入 Task 4 前端批量实现
- [x] 6. 实现侧边导航图表切换 — 并入 Task 4 前端批量实现
- [x] 7. 实现雷达图/排名榜/趋势图 ECharts — 并入 Task 4 前端批量实现
- [x] 8. 实现 Agent 占位对话框 — 并入 Task 4 前端批量实现
  Scenario: 热力图 hover tooltip
    Tool: Playwright
    Steps:
      1. page.goto('http://localhost:8765')
      2. 默认显示热力图
      3. page.hover('svg path[fill]') — hover 任意省份
      4. 等待 .echarts-tooltip 出现
      5. 检查 tooltip 包含省份名和得分数字
    Expected Result: tooltip 显示类似 "广东省 综合得分: 100.00 分"
    Evidence: .sisyphus/evidence/task-5-tooltip.png
  ```

- [x] 6. 实现侧边导航图表切换 — 已并入 Task 4

- [x] 7. 实现雷达图/排名榜/趋势图 ECharts — 已并入 Task 4

- [x] 8. 实现 Agent 占位对话框 — 已并入 Task 4

- [x] 9. **服务重构：提取 server 到 `src/server/` 独立包**

  **What to do**:
  - 创建 `src/server/__init__.py`
  - 移动 `src/visualization/server.py` → `src/server/main.py`
  - 移动 `src/visualization/data_api.py` → `src/server/data_api.py`
  - 移动 `src/visualization/static/` → `src/server/static/`
  - 更新 `src/server/main.py` 内部 import：`from .data_api import load_all_data`
  - 更新静态文件路径：`StaticFiles(directory=...)` 指向 `src/server/static/`
  - 启动命令变更为：`uv run python -m src.server.main`
  - 验证 `main.py --viz` 不受影响
  - 验证 `/api/data?year=2024` 返回正确数据

  **Must NOT do**:
  - 不创建 Docker 文件
  - 不修改 static/ 下的前端文件逻辑
  - 不修改 `src/visualization/` 下的静态图表模块

  **Recommended Agent Profile**: `quick` / `writing-python`
  **Parallelization**: 依赖 Task 1-8 完成，阻塞 F1

  **QA Scenarios**:
  ```
  Scenario: 服务重构后启动验证
    Tool: Bash
    Steps:
      1. uv run python -m py_compile src/server/main.py src/server/data_api.py
      2. 后台启动: uv run python -m src.server.main &
      3. sleep 3
      4. curl -s http://localhost:8765/api/data?year=2024 | python -c "import json,sys; d=json.load(sys.stdin); print(len(d['scores']['provinces']))"
      5. kill %1
    Expected Result: 输出 31，无 import 错误
    Evidence: terminal output, 无错误
  ```

  **After Completion**: `git add src/server/ && git rm src/visualization/server.py src/visualization/data_api.py && git rm -r src/visualization/static/` 然后提交。

- [x] 10. **Git Commit** — 提交所有更改
  - `git add src/server/ pyproject.toml uv.lock`
  - `git rm src/visualization/server.py src/visualization/data_api.py`
  - `git rm -r src/visualization/static/`
  - `git commit -m "refactor: extract server to src/server/ package"`

- [x] F1. **Playwright QA 验证仪表盘渲染** — 用户确认完成
  - 启动 server
  - 用 Playwright 打开 `http://localhost:8765`
  - 验证: 页面加载无 JS 错误
  - 验证: 热力图渲染，hover 显示 tooltip
  - 验证: 点击侧边导航按钮切换图表
  - 验证: 对话框输入框可见
  - 截图保存到 `.sisyphus/evidence/final-qa/`
  - 输出: `All [N/N] | VERDICT: APPROVE/REJECT`

---

## Commit Strategy

- **1-3**: `feat(visualization): add FastAPI server and data API layer` — server.py, data_api.py, pyproject.toml
- **4-8**: `feat(visualization): add ECharts interactive dashboard frontend` — static/*
- **F1**: squash into frontend commit if fixes needed

---

## Success Criteria

### Verification Commands
```bash
# 启动服务
uv run python -m src.server.main
# 浏览器打开 http://localhost:8765

# API 验证
curl -s 'http://localhost:8765/api/data?year=2024' | python -m json.tool | head -30
```

### Final Checklist
- [x] 热力图 hover 显示省份名 + 得分
- [x] 侧边导航切换 5 个图表
- [x] Agent 对话框输入框可见
- [x] `main.py --viz` 行为不变
- [x] 静态 PNG 输出不受影响
