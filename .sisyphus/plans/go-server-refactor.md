# Go 标准库重构仪表盘后端

## TL;DR
> 用 Go `net/http` 标准库重写 `src/server/`，零第三方依赖。复刻全部 4 个 API 端点 + 雷达归一化逻辑。

## Context
- 当前 Python/FastAPI 后端 ~380 行，逻辑简单（读 CSV → JSON）
- 用户要求用 Go 标准库，保持前端不变
- 算法分析部分（`main.py` / `src/models/`）不动

## Work Objectives

### Core
- Go HTTP 服务替代 FastAPI，功能完全等价
- 雷达数据预处理（CPI 转换 + Min-Max + 负向翻转）用 Go 复刻
- 前端 `static/` 直接复用

### Must Have
- `GET /` 返回 index.html
- `GET /api/data?year=2024` 返回完整 JSON
- `GET /api/years` 返回可用年份
- `GET /api/trend` 返回跨年趋势
- `GET /static/*` 静态资源
- CORS `*`
- 端口 8766（避免冲突）

### Must NOT Have
- 不改前端文件
- 不改 Python 分析代码
- 不引入第三方 Go 模块
- 不删除 `src/server/`

## Execution Strategy

```
Wave 1 (Go 后端):
├── Task 1: 项目骨架 + 静态文件 + 路由 [quick]
├── Task 2: CSV 读取 + JSON 序列化 [quick]
└── Task 3: 雷达归一化逻辑复刻 [quick]

Wave 2 (验证):
└── Task F1: curl 全端点验证 [quick]
```

## TODOs

- [x] 1. 创建 Go 项目骨架 + 路由 + 静态文件
  **文件**: `src/server-go/main.go`
  **内容**: HTTP 服务器，注册 5 个路由，挂载 `static/`，启用 CORS
  **验证**: `go run .` → `http://localhost:8766/` 返回 200

- [x] 2. CSV 读取 + JSON 数据端点
  **文件**: `src/server-go/data.go`
  **内容**: 实现 `loadScores` / `loadClusters` / `loadRanking` / `loadGeojson` / `loadTrend` / `loadAll`
  **验证**: `curl http://localhost:8766/api/data?year=2024` → 31 省

- [x] 3. 雷达归一化逻辑
  **文件**: `src/server-go/radar.go`
  **内容**: CPI 转换 |CPI-100|、负向指标翻转、Min-Max 归一化
  **验证**: radar 数据值与 Python 版本一致（误差 < 0.01）

- [x] F1. 全端点验证
  curl: /api/data /api/years /api/trend /static/style.css /
