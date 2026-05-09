# FE-M3：任务详情 MVP 已完成（概览 + 统计 + Raw 阶段 + 操作）

本文档记录 [`FRONTEND_DESIGN.md` §10](./FRONTEND_DESIGN.md) 中 **M3：任务详情 MVP** 的完成状态，供后续开发者与 AI Agent 接手 M4+ 时参考。

- **状态**：已完成
- **范围**：扩展 `GET /api/tasks/{run_id}`、任务详情概览 Tab、Raw 阶段统计、取消与重跑、自动化测试
- **后端依赖**：A2 已实现
- **下一阶段**：M4（任务列表 MVP）

---

## 1. 已完成内容

M3 已把 `/tasks/:runId` 从占位页推进到可排查单次 run 的详情页：

| 交付物 | 完成情况 |
|--------|----------|
| 单 run 详情契约 | `GET /api/tasks/{run_id}` 已返回 `task_type`、`trigger_type`、`dry_run`、`duration_ms`、完整 `statistics` |
| dry_run 持久化 | `file_task_runs` 新增 `dry_run` 列，并在 schema 初始化时为旧库补列 |
| 统计快照读取 | `FileTaskRun` 会解析 `statistics` JSON；旧数据或运行中数据会回退到 `file_results` 聚合 |
| 详情概览 | `TaskDetailPage` 已渲染 `RunHeader`、`RunActions`、`RunTimeline`、`StatsSummaryGrid` |
| Raw 阶段统计 | Raw 任务显示 `RawPhaseStats`，按阶段 1/2/3 展示 `phase*` 字段 |
| 操作 | 详情页支持 active run 取消；重跑沿用当前 `task_type` 与 `dry_run`，并遵守全局互斥 |
| 后续 Tab | 文件结果与日志 Tab 保留占位，分别留给 M6 / M7 |

M3 不包含任务列表筛选/分页、文件结果表、日志读取、删除、配置中心和系统信息。

---

## 2. 当前文件结构

### 新增文件

| 文件 | 说明 |
|------|------|
| `docs/FE-M3.md` | M3 完成交接记录 |
| `frontend/src/components/task/RunHeader.tsx` | 详情页头部 |
| `frontend/src/components/task/RunActions.tsx` | 取消 / 重跑操作 |
| `frontend/src/components/task/RunTimeline.tsx` | 时间线与错误信息 |
| `frontend/src/components/task/StatsSummaryGrid.tsx` | 通用统计卡片 |
| `frontend/src/components/task/RawPhaseStats.tsx` | Raw 三阶段统计卡片 |

### 修改文件

| 文件 | 说明 |
|------|------|
| `src/j_file_kit/app/file_task/domain/task_run.py` | `FileTaskRun` 增加 `dry_run` 与 `statistics` |
| `src/j_file_kit/app/file_task/domain/ports.py` | `create_run()` 增加 `dry_run` 参数 |
| `src/j_file_kit/infrastructure/persistence/sqlite/schema.py` | `file_task_runs` 新增 `dry_run` 列与旧库迁移 |
| `src/j_file_kit/infrastructure/persistence/sqlite/file_task/file_task_run_repository.py` | 写入/读取 `dry_run`，解析 `statistics` |
| `src/j_file_kit/infrastructure/file_task/file_task_run_manager.py` | 启动 run 时持久化 dry_run |
| `src/j_file_kit/app/file_task/application/schemas.py` | 扩展 start/detail 响应模型 |
| `src/j_file_kit/app/file_task/api.py` | 扩展 `GET /api/tasks/{run_id}` 详情响应 |
| `frontend/src/api/types.ts` | 增加完整详情与统计类型 |
| `frontend/src/api/tasks.ts` | 增加 `useTaskRunDetail()` |
| `frontend/src/pages/TaskDetailPage.tsx` | 从占位页改为真实概览页 |
| `frontend/src/lib/time.ts` | 增加毫秒耗时格式化 |
| `frontend/src/test/server.ts` | 增加详情接口 MSW mock |
| `frontend/src/App.test.tsx` | 覆盖详情概览、占位 Tab、取消与重跑 |

---

## 3. 后端接口现状

### 3.1 扩展后的详情接口

`GET /api/tasks/{run_id}` 返回完整详情：

```json
{
  "run_id": 1,
  "run_name": "raw_file_organizer-manual-20260510010101000",
  "task_type": "raw_file_organizer",
  "trigger_type": "manual",
  "dry_run": true,
  "status": "completed",
  "start_time": "2026-05-10T01:01:01",
  "end_time": "2026-05-10T01:01:03",
  "error_message": null,
  "duration_ms": 2000,
  "statistics": {
    "total_items": 12,
    "success_items": 9,
    "error_items": 1,
    "skipped_items": 2,
    "warning_items": 0,
    "total_duration_ms": 1234
  }
}
```

`statistics` 实际包含 `FileTaskRunStatistics` 的所有字段，包括 Raw `phase*` 字段；上例只展示通用字段。

### 3.2 dry_run 说明

新 run 会把 `dry_run` 写入 `file_task_runs`。旧 SQLite 启动时会自动补 `dry_run INTEGER NOT NULL DEFAULT 0`，因此旧 run 会显示为非 Dry Run；这是因为历史数据此前没有持久化该信息。

---

## 4. 前端详情页现状

`/tasks/:runId` 当前由 `TaskDetailPage` 组合：

1. `RunHeader`
2. Tab 切换（概览 / 文件结果 / 日志）
3. `RunActions`
4. `RunTimeline`
5. `StatsSummaryGrid`
6. `RawPhaseStats`（仅 Raw 任务）

`useTaskRunDetail(runId)` 在 `pending/running` 时每 2 秒轮询，进入终态后停止。重跑使用 `useStartTask(run.task_type)`，请求体固定 `{ dry_run: run.dry_run, trigger_type: "manual" }`，成功后跳转到新 run 详情。

---

## 5. 测试与验证

已新增或扩展测试覆盖：

1. SQLite run 仓储持久化 `dry_run` 与 `statistics`。
2. schema 初始化为旧 `file_task_runs` 表补 `dry_run` 列。
3. manager 启动 run 时传递 `dry_run`。
4. `GET /api/tasks/{run_id}` 返回完整详情字段。
5. 详情页概览渲染 badges、统计与 Raw phase。
6. 文件结果 / 日志 Tab 保持占位。
7. 详情页取消 active run。
8. 详情页重跑沿用 dry_run 并跳转新 run。

验证命令：

```bash
uv run pytest tests/api/test_file_task_api.py tests/infrastructure/persistence/sqlite/file_task/test_file_task_run_repository.py tests/infrastructure/file_task/test_file_task_run_manager.py
just fe-check
just fe-test
just fe-build
```

---

## 6. 给下一阶段 Agent 的交接说明

下一阶段是 **M4：任务列表 MVP**。建议优先处理：

- `GET /api/tasks?task_type=&status=&page=&page_size=` 的筛选与分页。
- 列表项补 `task_type`、`trigger_type`、`dry_run`、`statistics_summary`。
- `/tasks` 页面从占位替换为筛选栏、表格与分页。

M4 可复用 M3 的 `StatusBadge`、`TaskTypeBadge`、`DryRunBadge`、统计类型和时间格式化工具。
