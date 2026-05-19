# Agent - 前端 - 双语言后端交互改造计划

## TL;DR

> **Quick Summary**: 为 Python/FastAPI server 和 Go 标准库 server 同时新增 `/api/agent/query` 端点，前端增加聊天 UI 和 action 执行器，实现"自然语言 → Agent 解析 → 结构化动作 → 前端执行"的交互闭环。
>
> **Deliverables**:
> - Python: `src/server/agent.py`（规则引擎 + LLM Adapter 接口）
> - Python: `src/server/main.py` 新增 `POST /api/agent/query`
> - Go: `src/server-go/agent.go`（规则引擎 + LLM Adapter 接口）
> - Go: `src/server-go/main.go` 新增 `POST /api/agent/query` + CORS
> - 前端: `static/index.html` 聊天消息区域
> - 前端: `static/app.js` action 执行器 + Agent API 调用
> - 前端: `static/style.css` 聊天样式
>
> **Estimated Effort**: Medium
> **Parallel Execution**: YES - 3 waves
> **Critical Path**: Task 1 → Task 4/5 → Task 7/8 → Task 10

---

## Context

### Original Request
用户要求为 Go 和 Python 两个 server 版本同时实现 Agent - 前端 - 后端交互能力：
- 前端发送自然语言对话给 Agent
- Agent 解析后返回结构化动作（set_year, set_view, refresh_data, focus_province）
- 前端执行动作，切换年份和展示类型

### Interview Summary
**Key Discussions**:
- Agent v1: 规则解析版，预留 LLM Adapter 接口，不接真实 LLM
- 实现范围: Go server 和 Python server 都实现 `/api/agent/query`
- 展示类型: scoreMap / tierMap / radar / ranking / trend（使用前端内部名）
- set_view 行为: 每次只显示一种图表，隐藏其他图表
- 默认视图: scoreMap（热力图）
- 测试策略: 实现后补测试 + 浏览器 QA
- README: 不更新
- 年份自动生成: Go server 不实现，返回错误；Python server 保持现有逻辑

### Metis Review
**Identified Gaps** (addressed):
- 图表类型命名: 使用前端内部名 `scoreMap`/`tierMap` 而非 `heatmap`/`cluster`
- 静态文件同步: 两个 server 的 static 文件完全相同，需同步修改
- Go server 自动生成: 不实现，缺失年份返回错误信息
- focus_province 行为: v1 仅在地图视图高亮省份边框，排名视图滚动到该省
- CORS: Go server 需为 POST /api/agent/query 添加 CORS 头
- XSS 防护: 前端必须对用户输入和 Agent 回复做 HTML 转义
- 多 action 排序: set_year 必须在 set_view 之前执行
- Python server `_RESULTS_DIR` bug: 已知问题，不在本次计划范围内

---

## Work Objectives

### Core Objective
为两个 server 版本新增统一的 Agent 交互能力，前端通过自然语言控制年份切换和图表类型切换。

### Concrete Deliverables
- `src/server/agent.py` - Python Agent 规则引擎 + LLM Adapter 接口
- `src/server/main.py` - 新增 POST /api/agent/query 端点
- `src/server-go/agent.go` - Go Agent 规则引擎 + LLM Adapter 接口
- `src/server-go/main.go` - 新增 POST /api/agent/query 端点 + CORS
- `src/server/static/index.html` - 聊天消息区域
- `src/server/static/app.js` - action 执行器 + Agent API 调用
- `src/server/static/style.css` - 聊天样式
- `src/server-go/static/*` - 与 Python 版同步

### Definition of Done
- [ ] `curl -X POST :8765/api/agent/query -d '{"query":"看2023年数据"}'` 返回 `set_year(2023)` action
- [ ] `curl -X POST :8766/api/agent/query -d '{"query":"切换到雷达图"}'` 返回 `set_view(radar)` action
- [ ] 浏览器打开页面，输入"看2023年数据"，年份切换为 2023，图表更新
- [ ] 浏览器输入"切换到雷达图"，只显示雷达图，其他图表隐藏
- [ ] 浏览器输入无效指令，Agent 返回提示文本，不执行 action
- [ ] Go server POST 端点支持 CORS 预检

### Must Have
- Python 和 Go 的 Agent 规则引擎解析逻辑一致
- 前端 action 执行器支持 set_year / set_view / refresh_data / focus_province
- 前端聊天消息历史显示区域
- 用户输入和 Agent 回复的 HTML 转义（防 XSS）
- Go server POST 端点 CORS 支持

### Must NOT Have (Guardrails)
- 不修改现有 API 端点（/api/data, /api/years, /api/trend）的请求/响应格式
- 不修改现有图表渲染函数内部逻辑
- 不引入 LLM 调用或向量数据库
- 不更新任何 README 文件
- 不为 Go server 实现年份自动生成
- 不引入 Go 外部依赖（仅标准库）
- 不引入 Python 新运行时依赖
- 不做打字机效果/流式输出
- 不做消息持久化/本地存储
- 不做多轮对话上下文

---

## Verification Strategy

### Test Decision
- **Infrastructure exists**: NO
- **Automated tests**: None
- **Framework**: N/A
- **Agent-Executed QA**: MANDATORY for all tasks

### QA Policy
Every task MUST include agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **API/Backend**: Use Bash (curl) - Send requests, assert status + response fields
- **Frontend/UI**: Use Playwright - Navigate, interact, assert DOM, screenshot

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately - backend foundation, MAX PARALLEL):
├── Task 1: Define Agent JSON schema + shared contract [quick]
├── Task 2: Python Agent rule engine (src/server/agent.py) [quick]
├── Task 3: Go Agent rule engine (src/server-go/agent.go) [quick]
├── Task 4: Python /api/agent/query endpoint [quick]
└── Task 5: Go /api/agent/query endpoint + CORS [quick]

Wave 2 (After Wave 1 - frontend, MAX PARALLEL):
├── Task 6: Frontend chat UI (HTML + CSS) [visual-engineering]
├── Task 7: Frontend action executor (app.js) [visual-engineering]
└── Task 8: Frontend Agent API integration [visual-engineering]

Wave 3 (After Wave 2 - sync + verify):
├── Task 9: Sync static files between servers [quick]
└── Task 10: End-to-end verification [unspecified-high]

Critical Path: Task 1 → Task 4/5 → Task 7/8 → Task 10
Parallel Speedup: ~60% faster than sequential
Max Concurrent: 5 (Wave 1)
```

### Dependency Matrix

| Task | Blocked By | Blocks | Wave |
|------|-----------|--------|------|
| 1    | -         | 2,3,4,5 | 1    |
| 2    | 1         | 4       | 1    |
| 3    | 1         | 5       | 1    |
| 4    | 1,2       | 7,8     | 1    |
| 5    | 1,3       | 7,8     | 1    |
| 6    | -         | 9       | 2    |
| 7    | 4,5       | 9,10    | 2    |
| 8    | 4,5       | 9,10    | 2    |
| 9    | 6,7,8     | 10      | 3    |
| 10   | 9         | -       | 3    |

### Agent Dispatch Summary

- **Wave 1**: **5** - T1-T5 → `quick`
- **Wave 2**: **3** - T6-T8 → `visual-engineering`
- **Wave 3**: **2** - T9 → `quick`, T10 → `unspecified-high`

---

## TODOs

---

## Final Verification Wave

- [ ] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists. For each "Must NOT Have": search codebase for forbidden patterns. Check evidence files exist in .sisyphus/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [ ] F2. **Code Quality Review** — `unspecified-high`
  Run `python -c "import src.server.agent"` + `cd src/server-go && go build -o server .`. Review all changed files for: AI slop patterns, unused imports, hardcoded magic strings, missing error handling.
  Output: `Build [PASS/FAIL] | Python [OK/FAIL] | Go [OK/FAIL] | VERDICT`

- [ ] F3. **Real Manual QA** — `unspecified-high` (+ `playwright` skill)
  Start both servers. Execute EVERY QA scenario from EVERY task. Test cross-task integration. Test edge cases: empty input, XSS, invalid year, unknown command.
  Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [ ] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff. Verify 1:1. Check "Must NOT do" compliance. Detect cross-task contamination.
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

- **Wave 1**: `feat(server): add Agent rule engine and /api/agent/query endpoint` - agent.py, agent.go, main.py, main.go
- **Wave 2**: `feat(frontend): add chat UI and Agent action executor` - index.html, app.js, style.css
- **Wave 3**: `chore: sync static files and verify Agent integration` - static/*

---

## Success Criteria

### Verification Commands
```bash
# Python Agent API
curl -X POST http://localhost:8765/api/agent/query \
  -H "Content-Type: application/json" \
  -d '{"query":"看2023年数据"}' | python3 -m json.tool

# Go Agent API
curl -X POST http://localhost:8766/api/agent/query \
  -H "Content-Type: application/json" \
  -d '{"query":"切换到雷达图"}' | python3 -m json.tool

# Go CORS preflight
curl -X OPTIONS http://localhost:8766/api/agent/query \
  -H "Origin: http://localhost:8766" \
  -H "Access-Control-Request-Method: POST" -v 2>&1 | grep -i "access-control"
```

### Final Checklist
- [ ] Python /api/agent/query 返回正确 action
- [ ] Go /api/agent/query 返回正确 action
- [ ] 两个 server 对相同查询返回语义一致的结果
- [ ] 前端聊天 UI 可用
- [ ] 前端 action 执行器正确执行所有 4 种 action
- [ ] XSS 防护生效
- [ ] Go CORS 预检通过
- [ ] 所有 "Must NOT Have" 未被违反