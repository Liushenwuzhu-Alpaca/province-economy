# 仪表盘年份切换

## TL;DR
> **目标**: 仪表盘支持切换不同年份数据。前端加年份下拉框，后端加 `/api/years` 端点自动发现可用年份，`/api/data` 端点对缺失年份自动运行分析。

## Context
- 用户要求："前四项设置为可以切换不同年份显示"
- 当前仅 2024 有 `data/results/2024_pca/` 缓存
- `main.py --year 2023` 可生成新年份数据到 `data/results/2023_pca/`
- 仅 `scoreMap` / `tierMap` / `radar` / `ranking` 四个图表受年份影响；`trend` 跨年份不变

## Work Objectives

### Core
- 前端可切换年份，后端自动发现可用年份，缺失年份自动跑分析

### Must Have
- `GET /api/years` 返回已分析年份列表
- `GET /api/data?year=YYYY` 对缺失年份自动调用 `main.py --year YYYY`
- 侧边栏年份下拉框，默认显示当前选中年份
- 切换年份后自动重新加载数据并刷新当前图表

### Must NOT Have
- 不修改 `main.py` CLI 逻辑
- 不修改 `data_api.py`
- 不修改图表渲染逻辑（仅数据源切换）
- 不添加异步任务队列（同步执行即可）

## Execution Strategy

```
Wave 1 (后端):
├── Task 1: 添加 /api/years 端点 [quick]
└── Task 2: /api/data 自动分析缺失年份 [quick]

Wave 2 (前端):
├── Task 3: HTML 年份下拉框 [visual-engineering]
└── Task 4: JS 年份切换与数据重载 [visual-engineering]

Wave FINAL:
├── F1: curl 验证 API [quick]
└── F2: 浏览器验证年份切换 [visual-engineering]
```

## TODOs

- [x] 1. 添加 `GET /api/years` 端点
  **文件**: `src/server/main.py`
  **逻辑**: 扫描 `data/results/` 目录，匹配 `*_pca` 子目录，提取年份数字，返回 `{"years": [2024, ...]}` 排序列表
  **验证**: `curl http://localhost:8765/api/years` → `{"years":[2024]}`

- [x] 2. `/api/data` 自动分析缺失年份
  **文件**: `src/server/main.py`
  **逻辑**: 在 `api_data()` 中，调用 `load_all_data(year)` 前检查 `data/results/{year}_pca/scores.csv` 是否存在；若不存在则 `subprocess.run(["uv", "run", "python", "main.py", "--year", str(year)], check=True, cwd=...)`，等待完成后再加载
  **验证**: 删除 `data/results/2024_pca/scores.csv`，请求 `/api/data?year=2024` → 自动重新生成并返回 31 省数据

- [x] 3. HTML 年份下拉框
  **文件**: `src/server/static/index.html`
  **位置**: 侧边栏顶部，导航按钮上方
  **内容**: `<select id="year-select"></select>` ，默认由 JS 动态填充
  **验证**: 页面加载后下拉框出现且包含选项

- [x] 4. JS 年份切换与数据重载
  **文件**: `src/server/static/app.js`
  **逻辑**:
  - 页面加载时先 fetch `/api/years` 填充下拉框，默认选中最新年份
  - `fetchData(year)` 接受年份参数
  - 下拉框 `onchange` → `fetchData(newYear)` → `switchChart(currentType)`
  - `renderRadarChart` 的 top-5 选取应根据新数据重新计算（已修复，只需确认数据重载后重新渲染）
  **验证**: 切换年份后，热力图/梯队/雷达/排名数据更新

- [x] F1. API 验证
  ```bash
  curl http://localhost:8765/api/years  # {"years":[2024]}
  curl 'http://localhost:8765/api/data?year=2024'  # 31 provinces
  ```

- [ ] F2. 浏览器验证
  启动 server，浏览器打开 http://localhost:8765，切换年份验证数据刷新

## Commit Strategy
单一 commit: `feat(dashboard): add year switching with auto-analysis`
