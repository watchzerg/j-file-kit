# FE-M6：文件结果 Tab 已完成

本文档记录 [`FRONTEND_DESIGN.md` §10](./FRONTEND_DESIGN.md) 中 **M6：文件结果 Tab** 的完成状态，供后续开发者与 AI Agent 接手 M7+ 时参考。

- **状态**：已完成
- **范围**：`GET /api/tasks/{run_id}/results`、SQLite `file_results` 分页筛选查询、任务详情「文件结果」Tab、自动化测试
- **后端依赖**：A3 已实现
- **下一阶段**：M7（日志 Tab + 删除）

---

## 1. 已完成内容

M6 已把 `/tasks/:runId` 的「文件结果」Tab 从占位推进到可查询真实落库结果：

| 交付物 | 完成情况 |
|--------|----------|
| 结果查询接口 | 新增 `GET /api/tasks/{run_id}/results?decision_type=&success=&q=&page=&page_size=` |
| 仓储查询 | `file_results` 支持按 run、决策、成功状态、关键字分页查询与计数 |
| 前端 API | 增加 typed results response、`TaskRunResultsParams` 与 `useTaskRunResults()` |
| 详情页 Tab | 「文件结果」Tab 渲染筛选栏、结果表、分页、加载/错误/空状态 |
| URL 状态 | 结果筛选与分页使用 `results_*` search params，避免和详情页其他 Tab 冲突 |
| 测试覆盖 | 后端 API / SQLite 仓储 / 前端结果 Tab 行为均已覆盖 |

M6 不包含日志读取、SSE、终态 run 删除或结果导出。

---

## 2. 接口契约

`GET /api/tasks/{run_id}/results?decision_type=&success=&q=&page=&page_size=`

请求参数：

- `decision_type`：可选，`move` / `delete` / `skip`
- `success`：可选，`true` / `false`
- `q`：可选，按 `file_stem` 或 `serial_id` 模糊搜索
- `page`：默认 `1`，最小 `1`
- `page_size`：默认 `20`，范围 `1..100`

响应包：

```json
{
  "results": [
    {
      "id": 1,
      "source_path": "/media/raw_workspace/inbox/ABC-123.mp4",
      "file_stem": "ABC-123",
      "file_type": "video",
      "serial_id": "ABC-123",
      "decision_type": "move",
      "target_path": "/media/raw_workspace/files_video/ABC-123.mp4",
      "success": true,
      "error_message": null,
      "duration_ms": 10.5,
      "created_at": "2026-05-10T01:01:02"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

接口会先校验 run 是否存在；不存在时沿用现有 `TASK_NOT_FOUND` 错误语义。

---

## 3. 当前文件结构

### 新增文件

| 文件 | 说明 |
|------|------|
| `docs/FE-M6.md` | M6 完成交接记录 |
| `frontend/src/components/task/ResultFilterBar.tsx` | 文件结果筛选栏 |
| `frontend/src/components/task/ResultTable.tsx` | 文件结果表格 |

### 修改文件

| 文件 | 说明 |
|------|------|
| `src/j_file_kit/app/file_task/application/schemas.py` | 增加结果明细与分页响应模型 |
| `src/j_file_kit/app/file_task/domain/ports.py` | 扩展 `FileResultRepository` 查询协议 |
| `src/j_file_kit/infrastructure/persistence/sqlite/file_task/file_result_repository.py` | 实现结果分页、筛选与计数 |
| `src/j_file_kit/infrastructure/persistence/sqlite/schema.py` | 增加 `run_id + success` 结果查询索引 |
| `src/j_file_kit/app/file_task/api.py` | 新增 A3 结果查询路由 |
| `frontend/src/api/types.ts` | 增加文件结果相关类型 |
| `frontend/src/api/tasks.ts` | 增加 `useTaskRunResults()` |
| `frontend/src/pages/TaskDetailPage.tsx` | 接入真实「文件结果」Tab |
| `frontend/src/test/server.ts` | 增加结果查询 MSW mock |
| `frontend/src/App.test.tsx` | 覆盖结果 Tab、筛选 URL、分页 |
| `tests/api/test_file_task_api.py` | 覆盖 A3 API |
| `tests/infrastructure/persistence/sqlite/file_task/test_file_result_repository.py` | 覆盖结果仓储查询 |
| `docs/FRONTEND_DESIGN.md` | 更新 M6 进度 |

---

## 4. 踩坑记录

- **结果查询要先校验 run 存在**：否则不存在 run 与空结果 run 都会返回空列表，前端无法区分真实空状态和错误 ID。M6 在 API 层先调用 `file_task_run_manager.get_run()`。
- **`q` 只覆盖当前必要字段**：当前按 `file_stem` / `serial_id` 做 `LIKE`，没有上全文索引或路径搜索，避免把 v1 查询做重。
- **详情页 search params 需要加前缀**：M6 使用 `results_decision`、`results_success`、`results_q`、`results_page`、`results_page_size`，避免未来日志 Tab 或详情页级状态复用 `page` 时互相污染。
- **结果表会和筛选控件出现同名文本**：测试里断言「移动」这类文本要考虑 `<option>` 与表格单元格同时存在。

---

## 5. 测试与验证

已执行并通过：

```bash
uv run pytest tests/api/test_file_task_api.py tests/infrastructure/persistence/sqlite/file_task/test_file_result_repository.py
uv run ruff check src/j_file_kit/app/file_task tests/api/test_file_task_api.py tests/infrastructure/persistence/sqlite/file_task/test_file_result_repository.py
just fe-check
just fe-test
just fe-build
```

---

## 6. 给下一阶段 Agent 的建议

下一阶段是 **M7：日志 Tab + 删除**。建议优先实现：

- `GET /api/tasks/{run_id}/logs?offset=&limit=`，并在详情页「日志」Tab 替换占位。
- `DELETE /api/tasks/{run_id}`，仅允许终态删除，并同步处理 `file_results` 与日志文件。
- 列表页和详情页的删除按钮可以复用现有 `RunRowActions` / `RunActions` 思路，但要保留二次确认。

M7 与 M6 的直接交集是详情页 Tab 和 run 生命周期状态；日志读取和删除不要复用结果查询的筛选参数，避免 URL 状态互相耦合。
