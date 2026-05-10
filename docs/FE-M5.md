# FE-M5：配置中心已完成（JAV / Raw 表单 + MediaPickerDialog）

本文档记录 [`FRONTEND_DESIGN.md` §10](./FRONTEND_DESIGN.md) 中 **M5：配置中心** 的完成状态，供后续开发者与 AI Agent 接手 M6+ 时参考。

- **状态**：已完成
- **范围**：`GET /api/system/info`、配置中心 Tab、JAV / Raw 配置表单、目录选择弹层、路径前缀校验、自动化测试
- **后端依赖**：B1 已实现
- **下一阶段**：M6（文件结果 Tab）

---

## 1. 已完成内容

M5 已把 `/config` 从占位页推进到可读写任务配置的配置中心：

| 交付物 | 完成情况 |
|--------|----------|
| 系统信息契约 | 新增 `GET /api/system/info`，返回版本、环境、base_dir、媒体根与 JAV / Raw 根目录 |
| 配置页结构 | `/config` 增加全局配置 / JAV / Raw 三段 Tab；全局配置先只读展示系统信息 |
| JAV 表单 | 支持编辑 `workspace_root`、`enabled`、`misc_file_delete_rules.max_size`、`video_small_delete_bytes`、`inbox_delete_rules` |
| Raw 表单 | 支持编辑 `workspace_root` 与 `enabled` |
| MediaPickerDialog | 复用 `GET /api/media/directories` 懒加载目录，选择后回填工作区 |
| 前端路径校验 | 保存前校验 JAV 工作区位于 `jav_media_root` 下、Raw 位于 `raw_media_root` 下 |
| API 类型 | 前端补齐 typed config、system info、`useSystemInfo()` |

M5 不包含 B2 `GET /api/system/file-type-defaults`、全局配置编辑、文件结果 Tab、日志 Tab 或删除 run。

---

## 2. 接口契约

### 2.1 系统信息

`GET /api/system/info`

```json
{
  "app_version": "dev",
  "env": "development",
  "base_dir": "/data",
  "media_root": "/media",
  "jav_media_root": "/media/jav_workspace",
  "raw_media_root": "/media/raw_workspace",
  "media_mounted": true
}
```

前端只把该接口作为只读元数据使用；路径合法性仍由后端配置 schema 最终兜底。

### 2.2 配置更新

沿用已有接口：

- `GET /api/file-task/config/jav-video-organizer`
- `PATCH /api/file-task/config/jav-video-organizer`
- `GET /api/file-task/config/raw-file-organizer`
- `PATCH /api/file-task/config/raw-file-organizer`

JAV 表单只提交当前允许编辑的字段，避免把后端会 strip 的 `extensions` / `keywords` 写回 YAML。

---

## 3. 当前文件结构

### 新增文件

| 文件 | 说明 |
|------|------|
| `docs/FE-M5.md` | M5 完成交接记录 |
| `src/j_file_kit/app/system/api.py` | 系统信息路由 |
| `src/j_file_kit/app/system/schemas.py` | 系统信息响应模型 |
| `tests/api/test_system_api.py` | B1 集成测试 |
| `frontend/src/api/system.ts` | `useSystemInfo()` |
| `frontend/src/components/config/MediaPickerDialog.tsx` | 媒体目录懒加载选择弹层 |
| `frontend/src/components/config/PathInput.tsx` | 路径输入 + 选择目录按钮 |
| `frontend/src/components/config/StemTagsInput.tsx` | comma separated stems 输入 |
| `frontend/src/components/config/TaskConfigPanel.tsx` | JAV / Raw 配置表单 |
| `frontend/src/lib/paths.ts` | 路径前缀校验工具 |

### 修改文件

| 文件 | 说明 |
|------|------|
| `src/j_file_kit/api/app.py` | 挂载 system router |
| `frontend/src/api/types.ts` | 增加 typed config 与 system info 类型 |
| `frontend/src/api/config.ts` | 配置 hook 按 task type 返回强类型 config |
| `frontend/src/api/media.ts` | `useMediaDirectories()` 支持按需启用 |
| `frontend/src/api/client.ts` | 兼容 FastAPI `{ detail: { code, message } }` 错误体 |
| `frontend/src/lib/errors.ts` | 增加配置与媒体错误码文案 |
| `frontend/src/pages/ConfigPage.tsx` | 从占位页替换为配置中心 |
| `frontend/src/test/server.ts` | 增加 system/media/config PATCH mocks |
| `frontend/src/App.test.tsx` | 覆盖配置页、保存、路径校验与目录选择 |
| `docs/FRONTEND_DESIGN.md` | 更新 M5 进度 |

---

## 4. 踩坑记录

- **B1 值要从后端给**：如果前端硬编码 `/media/jav_workspace` / `/media/raw_workspace`，测试和部署环境很容易与 monkeypatch 或未来配置漂移。M5 已用 `GET /api/system/info` 作为单一来源。
- **FastAPI 错误体形态不统一**：配置和媒体 API 当前会返回 `{ detail: { code, message } }`，而前端 `apiClient` 原先只识别根级 `{ code, message }`。M5 已兼容两种形态，否则 `INVALID_CONFIG` 会显示成未知错误。
- **目录树不能一次性展开**：`useMediaDirectories()` 增加 `enabled` 参数，`MediaPickerDialog` 只在节点展开时请求该节点，避免打开弹层就抓取所有子树。
- **JAV PATCH 只做浅合并**：服务端 `merge_jav_video_organizer_config()` 是顶层合并，因此前端提交 `inbox_delete_rules` 时必须带完整子对象；只提交其中一个子字段会覆盖掉另一个字段。
- **shadcn 尚未落地**：仓库目前没有 `components/ui` 生成物。M5 沿用现有原生控件 + Tailwind 风格，避免引入半套 UI 基建。

---

## 5. 测试与验证

已执行并通过：

```bash
uv run pytest tests/api/test_config_api.py tests/api/test_system_api.py tests/app/media_browser/test_media_browser_api.py
uv run ruff check src/j_file_kit/app/system tests/api/test_system_api.py src/j_file_kit/api/app.py
just fe-check
just fe-test
just fe-build
```

---

## 6. 给下一阶段 Agent 的建议

下一阶段是 **M6：文件结果 Tab**。建议优先实现：

- `GET /api/tasks/{run_id}/results?decision_type=&success=&q=&page=&page_size=`。
- SQLite `file_results` 的分页、筛选与计数。
- `TaskDetailPage` 中「文件结果」Tab 的真实表格、筛选栏和分页。

M6 可复用 M4 的分页/筛选 URL 参数思路，以及 M3 的任务详情轮询策略。M5 的配置中心与 M6 依赖较少，不需要改动配置页即可继续推进。
