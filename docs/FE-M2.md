# FE-M2：Dashboard MVP 已完成（全局任务条 + 启动面板 + 最近任务）

本文档记录 [`FRONTEND_DESIGN.md` §10](./FRONTEND_DESIGN.md) 中 **M2：Dashboard MVP** 的完成状态，供后续开发者与 AI Agent 接手 M3+ 时参考。

- **状态**：已完成
- **范围**：`GET /api/tasks/active`、`GlobalRunBanner`、Dashboard 启动任务面板、快捷入口、最近任务列表、自动化测试
- **后端依赖**：A6 已实现；A1 简报字段未实现，M2 按设计先留空
- **下一阶段**：M3（任务详情 MVP）

---

## 1. 已完成内容

M2 已把 Dashboard 从 M1 占位页推进到可启动任务、可感知互斥、可浏览最近 run 的 MVP：

| 交付物 | 完成情况 |
|--------|----------|
| 后端 active run 契约 | 已新增 `GET /api/tasks/active`，返回 `null` 或当前 `pending/running` run 摘要 |
| 互斥语义修正 | `FileTaskRunManager.start_run()` 已从只检查 `running` 改为检查 `pending/running` active run |
| 全局任务条 | `GlobalRunBanner` 已接入 `useActiveTaskRun()`，展示 run 名、task type、状态、已运行时长、详情链接与取消按钮 |
| Dashboard 启动面板 | `NewTaskPanel` 已提供 JAV / Raw 双卡，展示 `workspace_root`、`enabled`，Dry Run 默认开启 |
| 启动行为 | 启动成功后失效任务相关 query，并跳转到 `/tasks/{run_id}` |
| 启动禁用规则 | 已按优先级处理 active run、配置加载、配置失败、`enabled=false`、mutation pending |
| 最近任务列表 | `RecentRunsList` 使用现有 `GET /api/tasks`，前端截取最近 10 条并展示状态、时间、耗时、详情链接 |
| 快捷入口 | Dashboard 已包含配置、媒体、任务列表、文档提示 4 个入口区块 |
| 测试覆盖 | 已加入后端 active run 测试与前端 MSW 行为测试 |

M2 仍刻意不做任务列表筛选/分页、任务详情统计、配置表单、文件结果、日志、删除。这些仍按原里程碑进入 M3+。

---

## 2. 当前文件结构

### 新增文件

| 文件 | 说明 |
|------|------|
| `docs/FE-M2.md` | M2 完成交接记录 |
| `frontend/src/components/task/StatusBadge.tsx` | 任务状态徽标 |
| `frontend/src/components/task/TaskTypeBadge.tsx` | JAV / Raw 任务类型徽标与文案映射 |
| `frontend/src/components/task/DryRunBadge.tsx` | Dry Run 徽标 |
| `frontend/src/components/task/StartTaskCard.tsx` | 单个 task type 的启动卡 |
| `frontend/src/components/task/NewTaskPanel.tsx` | Dashboard 双任务启动面板 |
| `frontend/src/components/task/RecentRunsList.tsx` | Dashboard 最近任务列表 |
| `frontend/src/components/task/QuickLinks.tsx` | Dashboard 快捷入口 |
| `frontend/src/lib/time.ts` | 时间与耗时格式化工具 |
| `frontend/src/lib/task-config.ts` | 从任务配置中安全读取 `workspace_root` |
| `frontend/src/test/server.ts` | MSW 测试 server 与默认 API mock |

### 修改文件

| 文件 | 说明 |
|------|------|
| `src/j_file_kit/app/file_task/application/schemas.py` | 新增 `ActiveFileTaskRunResponse` |
| `src/j_file_kit/app/file_task/domain/ports.py` | `FileTaskRunRepository` 端口新增 `get_active_run()` |
| `src/j_file_kit/infrastructure/persistence/sqlite/file_task/file_task_run_repository.py` | 实现 `get_active_run()`，查询 `pending/running` |
| `src/j_file_kit/infrastructure/file_task/file_task_run_manager.py` | 启动互斥检查改用 active run；新增 `get_active_run()` |
| `src/j_file_kit/app/file_task/api.py` | 新增 `GET /api/tasks/active` |
| `frontend/src/api/types.ts` | 新增 `FileTaskType`、`ActiveFileTaskRun`、`ActiveFileTaskRunResponse` |
| `frontend/src/api/tasks.ts` | 新增 `useActiveTaskRun()`、`useRecentTaskRuns()`；start/cancel 成功后失效 active query |
| `frontend/src/components/layout/GlobalRunBanner.tsx` | 从占位改为真实活跃任务条 |
| `frontend/src/pages/DashboardPage.tsx` | 从 M1 占位改为真实 Dashboard MVP |
| `frontend/src/App.tsx` | `QueryClient` 改为每个 App 实例创建，避免测试间缓存串扰 |
| `frontend/src/App.test.tsx` | 扩展 Dashboard、banner、启动、取消行为测试 |
| `frontend/src/test/setup.ts` | 接入 MSW 生命周期 |

---

## 3. 后端接口现状

### 3.1 新增 active run 接口

`GET /api/tasks/active`

返回：

```json
null
```

或：

```json
{
  "run_id": 1,
  "run_name": "raw_file_organizer-manual-20260510010101000",
  "task_type": "raw_file_organizer",
  "trigger_type": "manual",
  "status": "running",
  "start_time": "2026-05-10T01:01:01",
  "end_time": null,
  "error_message": null
}
```

active 的定义是 `pending` 或 `running`。前端所有互斥入口都应以 `useActiveTaskRun()` 为准，不要用 `GET /api/tasks` 的第一行推断。

### 3.2 保持不变的接口

M2 没有扩展 `GET /api/tasks` 的返回字段。它仍只返回：

- `run_id`
- `run_name`
- `status`
- `start_time`
- `end_time`

因此 Dashboard 的最近任务列表不显示 `task_type`、`dry_run` 和统计摘要。等 M4/A1 扩展列表接口后再补。

---

## 4. Dashboard 现状

`/` 当前由 `DashboardPage` 组合以下模块：

1. `NewTaskPanel`
2. `QuickLinks`
3. `RecentRunsList`
4. 系统信息占位（仍属 M8）

### 4.1 `NewTaskPanel`

- 两张启动卡：`TASK_TYPES.JAV` 与 `TASK_TYPES.RAW`。
- 每张卡读取 `useTaskConfig(taskType)`，展示 `workspace_root` 与 `enabled`。
- Dry Run toggle 默认 ON。
- 启动请求固定发送 `trigger_type: "manual"`。
- 启动成功后跳转 `/tasks/{run_id}`。
- 若已有 active run，两张启动卡都会禁用。

### 4.2 `GlobalRunBanner`

- 放在 `AppShell` 中 `TopNav` 下方，结构未改。
- `useActiveTaskRun()` 常驻 3s 轮询。
- active run 存在时显示状态条，不存在时返回 `null`。
- 取消按钮调用 `useCancelTaskRun(run_id)`。
- 已运行时长每秒本地刷新，不写入 server state。

### 4.3 `RecentRunsList`

- 使用 `useRecentTaskRuns()`。
- 内部仍请求 `GET /api/tasks`，前端 `slice(0, 10)`。
- 当前只展示已有字段，避免从 `run_name` 推断 task type。

---

## 5. 测试与验证

已新增或扩展测试覆盖：

1. `GET /api/tasks/active` 空结果、active run、终态 run 忽略。
2. SQLite `get_active_run()` 同时识别 `pending/running`。
3. manager 在已有 `pending` run 时拒绝新启动。
4. Dashboard 渲染真实 M2 区块。
5. active run 出现时展示 `GlobalRunBanner` 并禁用启动按钮。
6. 启动任务默认带 `dry_run: true` 并跳转详情页。
7. 全局任务条取消按钮会调用取消接口。

已执行并通过：

```bash
uv run pytest tests/api/test_file_task_api.py tests/infrastructure/persistence/sqlite/file_task/test_file_task_run_repository.py tests/infrastructure/file_task/test_file_task_run_manager.py
bun run check
bun run test
bun run build
```

其中 `bun run test` 当前结果为 1 个测试文件、7 个测试通过。

---

## 6. 给下一阶段 Agent 的交接说明

### 6.1 M3 应从哪里开始

下一阶段是 **M3：任务详情 MVP**。建议优先参考 [`FRONTEND_DESIGN.md`](./FRONTEND_DESIGN.md) 的这些章节：

- §5 页面：任务详情
- §7.A2 `GET /api/tasks/{run_id}` 扩展
- §8 数据获取与轮询策略
- §9 共享组件清单
- §10 落地里程碑

M3 的主要目标：

1. 扩展 `GET /api/tasks/{run_id}`，返回 `task_type`、`trigger_type`、`dry_run`、完整 `statistics`、派生 `duration_ms`。
2. 将 `TaskDetailPage` 的“概览”占位替换为真实 `RunHeader`、`RunTimeline`、`RunActions`、`StatsSummaryGrid`。
3. Raw 任务显示 `RawPhaseStats`，按 Raw 三阶段分组展示 `phase*` 字段。
4. 保留文件结果 Tab、日志 Tab 的占位；它们分别属于 M6、M7。

### 6.2 M3 可复用的 M2 组件

| 组件/工具 | M3 用途 |
|-----------|---------|
| `StatusBadge` | 详情页 run 状态展示 |
| `TaskTypeBadge` | 详情页任务类型展示 |
| `DryRunBadge` | 详情页 dry_run 标记 |
| `formatDateTime` / `formatDuration` | timeline 与耗时展示 |
| `useActiveTaskRun()` | 判断重跑按钮是否因全局互斥而禁用 |
| `useCancelTaskRun()` | 详情页 active run 的取消操作 |
| `getErrorMessage()` | 详情页错误态展示 |

### 6.3 M3 预计要改的现有文件

| 文件 | M3 可能改动 |
|------|-------------|
| `src/j_file_kit/app/file_task/application/schemas.py` | 扩展单 run 详情响应模型 |
| `src/j_file_kit/app/file_task/api.py` | 扩展 `GET /api/tasks/{run_id}` |
| `src/j_file_kit/infrastructure/persistence/sqlite/file_task/file_task_run_repository.py` | 如需读取持久化 statistics，需要解析 `statistics` JSON |
| `frontend/src/api/types.ts` | 增加完整 run detail / statistics 类型 |
| `frontend/src/api/tasks.ts` | 调整或新增 `useTaskRunDetail(runId)` |
| `frontend/src/pages/TaskDetailPage.tsx` | 替换概览 Tab 占位 |

M3 可能新增：

| 目录/文件 | 用途 |
|-----------|------|
| `frontend/src/components/task/RunHeader.tsx` | 详情页头部 |
| `frontend/src/components/task/RunTimeline.tsx` | 创建/开始/结束/耗时/error timeline |
| `frontend/src/components/task/RunActions.tsx` | 取消 / 重跑操作 |
| `frontend/src/components/task/StatsSummaryGrid.tsx` | 通用统计卡片 |
| `frontend/src/components/task/RawPhaseStats.tsx` | Raw 阶段统计卡片 |

### 6.4 保持不变的 M2 约束

- 不要用 `GET /api/tasks` 推断 active run；继续使用 `useActiveTaskRun()`。
- 不要在页面组件里直接 `fetch`；新增端点先加 `api/*.ts` hook。
- `dry_run` 必须醒目标记，详情页尤其不要隐藏。
- active run 的轮询应在终态停止；详情页可参考现有 `useTaskRunStatus()` 的 `refetchInterval` 写法。
- Dashboard 的系统信息仍是 M8 占位，M3 不需要顺手实现。

---

## 7. 后续里程碑提示

| 占位位置 | 后续阶段 |
|----------|----------|
| Dashboard：系统信息 | M8 |
| 任务详情：概览 Tab | M3 |
| 任务列表：筛选栏 / 表格 / 分页 | M4 |
| 配置页真实表单 | M5 |
| 任务详情：文件结果 Tab | M6 |
| 任务详情：日志 Tab | M7 |

下一步建议从 M3 开始；M3 的硬依赖是 **A2 `GET /api/tasks/{run_id}` 扩展**。
