# FE-M4：任务列表 MVP 已完成（筛选 + 分页 + 行操作）

本文档记录 [`FRONTEND_DESIGN.md` §10](./FRONTEND_DESIGN.md) 中 **M4：任务列表 MVP** 的完成状态，供后续开发者与 AI Agent 接手 M5+ 时参考。

- **状态**：已完成
- **范围**：扩展 `GET /api/tasks`、任务列表筛选与分页、列表行详情/取消、Dashboard 最近任务摘要、自动化测试
- **后端依赖**：A1 已实现
- **下一阶段**：M5（配置中心）或 M6（文件结果 Tab）

---

## 1. 已完成内容

M4 已把 `/tasks` 从占位页推进到可浏览历史 run 的任务列表：

| 交付物 | 完成情况 |
|--------|----------|
| 列表契约 | `GET /api/tasks` 支持 `task_type` / `status` 筛选与 `page` / `page_size` 分页 |
| 列表字段 | 列表项返回 `task_type`、`trigger_type`、`dry_run`、`duration_ms`、`statistics_summary` |
| SQLite 查询 | `file_task_runs` 仓储支持筛选、分页、计数与排序 |
| 任务列表页 | `/tasks` 渲染筛选栏、任务表格、分页、加载/错误/空状态 |
| 行操作 | 终态 run 可查看详情；`pending/running` run 可在行内取消 |
| Dashboard 联动 | 最近任务显示类型、Dry Run 与统计简报 |

M4 不包含删除、日期范围筛选、文件结果表和日志读取。

---

## 2. 接口契约

`GET /api/tasks?task_type=&status=&page=&page_size=`

请求参数：

- `task_type`：可选，`jav_video_organizer` / `raw_file_organizer`
- `status`：可选，`pending` / `running` / `completed` / `failed` / `cancelled`
- `page`：默认 `1`，最小 `1`
- `page_size`：默认 `20`，范围 `1..100`

响应包：

```json
{
  "runs": [
    {
      "run_id": 1,
      "run_name": "raw_file_organizer-manual-20260510010101000",
      "task_type": "raw_file_organizer",
      "trigger_type": "manual",
      "dry_run": true,
      "status": "completed",
      "start_time": "2026-05-10T01:01:01",
      "end_time": "2026-05-10T01:01:03",
      "duration_ms": 2000,
      "statistics_summary": {
        "total_items": 12,
        "success_items": 9,
        "error_items": 1,
        "skipped_items": 2,
        "warning_items": 0,
        "total_duration_ms": 1234
      }
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

---

## 3. 当前文件结构

### 新增文件

| 文件 | 说明 |
|------|------|
| `docs/FE-M4.md` | M4 完成交接记录 |
| `frontend/src/components/task/RunFilterBar.tsx` | 任务列表筛选栏 |
| `frontend/src/components/task/RunTable.tsx` | 任务列表表格 |
| `frontend/src/components/task/RunPagination.tsx` | 任务列表分页 |
| `frontend/src/components/task/RunRowActions.tsx` | 详情 / 取消行操作 |

### 修改文件

| 文件 | 说明 |
|------|------|
| `src/j_file_kit/app/file_task/application/schemas.py` | 扩展列表响应模型与统计摘要模型 |
| `src/j_file_kit/app/file_task/api.py` | 扩展 `GET /api/tasks` 查询参数与分页响应 |
| `src/j_file_kit/app/file_task/domain/ports.py` | 扩展 run 仓储协议 |
| `src/j_file_kit/infrastructure/file_task/file_task_run_manager.py` | 透传分页筛选与计数 |
| `src/j_file_kit/infrastructure/persistence/sqlite/file_task/file_task_run_repository.py` | 实现筛选、分页、计数 |
| `src/j_file_kit/infrastructure/persistence/sqlite/schema.py` | 增加列表查询索引 |
| `frontend/src/api/types.ts` | 扩展列表项、分页响应与查询参数类型 |
| `frontend/src/api/tasks.ts` | `useTaskRunList(params)` 与最近任务分页查询 |
| `frontend/src/pages/TasksListPage.tsx` | 从占位页改为真实列表页 |
| `frontend/src/components/task/RecentRunsList.tsx` | 展示 M4 摘要字段 |
| `frontend/src/test/server.ts` | 扩展 MSW 列表接口 mock |
| `frontend/src/App.test.tsx` | 覆盖任务列表筛选、分页与取消 |
| `tests/api/test_file_task_api.py` | 覆盖列表接口 A1 |
| `tests/infrastructure/persistence/sqlite/file_task/test_file_task_run_repository.py` | 覆盖仓储筛选分页 |

---

## 4. 测试与验证

建议验证命令：

```bash
uv run pytest tests/api/test_file_task_api.py tests/infrastructure/persistence/sqlite/file_task/test_file_task_run_repository.py
just fe-check
just fe-test
just fe-build
```

---

## 5. 后续事项

- **M5：配置中心**：JAV / Raw 表单与 MediaPickerDialog。
- **M6：文件结果 Tab**：实现 `GET /api/tasks/{run_id}/results` 与结果表。
- **M7：日志 Tab + 删除**：实现日志分页读取与终态 run 删除。
