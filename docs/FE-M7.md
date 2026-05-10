# FE-M7：日志 Tab + 删除已完成

本文档记录 [`FRONTEND_DESIGN.md` §10](./FRONTEND_DESIGN.md) 中 **M7：日志 Tab + 删除** 的完成状态，供后续开发者与 AI Agent 接手 M8+ 时参考。

- **状态**：已完成
- **范围**：`GET /api/tasks/{run_id}/logs`、`DELETE /api/tasks/{run_id}`、任务详情「日志」Tab、列表/详情终态删除、自动化测试
- **后端依赖**：A5、A4 已实现
- **下一阶段**：M8（全局配置只读 + 系统信息）

---

## 1. 已完成内容

M7 已把 `/tasks/:runId` 的「日志」Tab 从占位推进到可查看真实任务日志，并补齐终态 run 删除能力：

| 交付物 | 完成情况 |
|--------|----------|
| 日志分页接口 | 新增 `GET /api/tasks/{run_id}/logs?offset=&limit=` |
| 日志解析 | 解析 loguru JSON Lines 的 `record.time` / `record.level.name` / `record.message` / `record.extra` |
| 终态删除接口 | 新增 `DELETE /api/tasks/{run_id}`，仅允许 `completed` / `failed` / `cancelled` |
| 删除清理 | 删除 run 记录、关联 `file_results`、对应 JSONL 日志文件 |
| 前端 API | 增加 typed logs/delete response、`useTaskRunLogs()` 与 `useDeleteTaskRun()` |
| 详情页 Tab | 「日志」Tab 渲染日志表、offset 分页、加载/错误/空状态 |
| 删除入口 | 任务列表行操作与详情页操作区显示终态删除按钮，并有二次确认 |
| 测试覆盖 | 后端 API / SQLite 仓储 / 前端日志与删除行为均已覆盖 |

M7 不包含 SSE 实时流、日志全文筛选、日志虚拟列表、结果导出或 M8 的全局配置只读页。

---

## 2. 接口契约

### 2.1 `GET /api/tasks/{run_id}/logs?offset=&limit=`

请求参数：

- `offset`：默认 `0`，最小 `0`
- `limit`：默认 `100`，范围 `1..500`

响应包：

```json
{
  "total_lines": 2,
  "offset": 0,
  "limit": 100,
  "lines": [
    {
      "line_no": 1,
      "ts": "2026-05-10 01:01:01.000000+00:00",
      "level": "INFO",
      "msg": "Task started",
      "fields": { "run_id": 123 }
    }
  ]
}
```

接口会先校验 run 是否存在；不存在时沿用 `TASK_NOT_FOUND`。日志文件不存在时返回空分页，因为新建或快速失败的 run 可能还没写出日志文件。

### 2.2 `DELETE /api/tasks/{run_id}`

删除约束：

- 仅允许终态：`completed` / `failed` / `cancelled`
- `pending` / `running` 返回 `TASK_NOT_TERMINAL`
- 删除成功后会清理 `file_results` 与 `{run_name}_{run_id}.jsonl`

响应包：

```json
{
  "run_id": 123,
  "message": "任务已删除"
}
```

---

## 3. 当前文件结构

### 新增文件

| 文件 | 说明 |
|------|------|
| `docs/FE-M7.md` | M7 完成交接记录 |
| `frontend/src/components/task/LogViewer.tsx` | 日志表格 |
| `frontend/src/components/task/LogPagination.tsx` | offset/limit 日志分页 |

### 修改文件

| 文件 | 说明 |
|------|------|
| `src/j_file_kit/app/file_task/application/schemas.py` | 增加日志与删除响应模型 |
| `src/j_file_kit/app/file_task/domain/ports.py` | 扩展 run/results 删除协议 |
| `src/j_file_kit/infrastructure/persistence/sqlite/file_task/file_task_run_repository.py` | 实现 run 删除 |
| `src/j_file_kit/infrastructure/persistence/sqlite/file_task/file_result_repository.py` | 实现结果删除 |
| `src/j_file_kit/app/file_task/api.py` | 新增 A5 日志路由与 A4 删除路由 |
| `frontend/src/api/types.ts` | 增加日志与删除相关类型 |
| `frontend/src/api/tasks.ts` | 增加 `useTaskRunLogs()` 与 `useDeleteTaskRun()` |
| `frontend/src/pages/TaskDetailPage.tsx` | 接入真实「日志」Tab |
| `frontend/src/components/task/RunActions.tsx` | 详情页终态删除 |
| `frontend/src/components/task/RunRowActions.tsx` | 列表页终态删除 |
| `frontend/src/lib/errors.ts` | 增加 `TASK_NOT_TERMINAL` 文案 |
| `frontend/src/test/server.ts` | 增加日志与删除 MSW mock |
| `frontend/src/App.test.tsx` | 覆盖日志 Tab、日志分页、删除行为 |
| `tests/api/test_file_task_api.py` | 覆盖 A5 / A4 API |
| `tests/infrastructure/persistence/sqlite/file_task/test_file_result_repository.py` | 覆盖结果删除 |
| `docs/FRONTEND_DESIGN.md` | 更新 M7 进度 |

---

## 4. 踩坑记录

- **日志文件不存在不是错误**：run 存在但日志文件还没创建时返回空分页，前端显示“暂无任务日志”。
- **loguru JSONL 需要容错解析**：解析失败或结构不是对象时保留原始行作为 `msg`，避免单行脏数据导致整页失败。
- **日志分页不要复用结果分页参数**：前端使用 `logs_offset` / `logs_limit`，避免和 M6 的 `results_*` 状态互相污染。
- **删除必须先判定终态**：不能删除 `pending/running`，否则会破坏全局互斥和后台线程状态。
- **删除清理顺序要明确**：先删 `file_results`，再删 run，最后幂等删除日志文件；日志文件删除失败应暴露异常，不静默吞掉权限问题。

---

## 5. 测试与验证

已执行并通过：

```bash
uv run pytest tests/api/test_file_task_api.py tests/infrastructure/persistence/sqlite/file_task/test_file_result_repository.py
uv run ruff check src/j_file_kit/app/file_task src/j_file_kit/infrastructure/persistence/sqlite/file_task tests/api/test_file_task_api.py
just fe-check
just fe-test
just fe-build
```

---

## 6. 给下一阶段 Agent 的建议

下一阶段是 **M8：全局配置只读 + 系统信息**。建议优先实现配置中心第一个 Tab 的只读展示，再把 Dashboard 页脚补成真实系统信息。

- B1 `GET /api/system/info` 已在前端和 mock 中被使用，可先核对真实后端字段是否完全覆盖 Dashboard 页脚需要。
- B2 `GET /api/system/file-type-defaults` 仍是可选项；如果短期只做只读展示，可以先复用后端常量导出的接口，不要在前端复制第二份复杂规则。
- M7 的删除会让详情页 run 不再存在，M8 若新增最近任务或系统摘要，不要缓存已删除 run 的派生信息。
