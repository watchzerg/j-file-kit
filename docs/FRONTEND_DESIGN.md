# 前端页面设计文档

本文档面向 **后续接手的开发者与 AI Agent**，从「业务页面 → 模块 → 后端接口」三个维度描述前端的功能现状与设计决策。

- 技术栈、目录结构、构建集成请参考 [`ARCHITECTURE.md` §12 前端架构](./ARCHITECTURE.md)，本文不再重复。
- 业务规则（JAV 分析 / Raw 三阶段）请分别参考 [`JAV_VIDEO_PROCESSING_PIPELINE.md`](./JAV_VIDEO_PROCESSING_PIPELINE.md) 与 [`RAW_FILE_PROCESSING_PIPELINE.md`](./RAW_FILE_PROCESSING_PIPELINE.md)。

---

## 1. 设计原则

1. **后端互斥 → 前端可见**：`FileTaskRunManager` 全局只允许一个 run 处于 `pending/running`（见 [`file_task_run_manager.py`](../src/j_file_kit/infrastructure/file_task/file_task_run_manager.py)）。前端通过 **顶部全局任务条** 与 **启动按钮的禁用态** 把约束直接呈现给用户，而非让后端兜底报 `FileTaskAlreadyRunningError`。
2. **薄页面 + 厚 hooks**：`pages/` 只组合布局与组件；所有数据获取、轮询、Mutation 全部走 `api/*.ts` 中的 TanStack Query hook（见 [`api/tasks.ts`](../frontend/src/api/tasks.ts)、[`api/config.ts`](../frontend/src/api/config.ts)、[`api/media.ts`](../frontend/src/api/media.ts)）。
3. **以"任务 run"为核心实体**：所有页面入口都能跳转到 **任务详情**，详情页是数据最完整、刷新策略最复杂的页面。
4. **dry_run 是一等公民**：JAV / Raw 都支持 dry_run 预览。新建任务、任务卡、详情页都有明显的 dry_run 标记（颜色或徽标），避免用户误以为已实际改动磁盘。dry_run 默认开启，用户必须显式关掉 toggle 才会真删/真移。
5. **不堆砌可扩展性**：当前只有 2 个 task_type。task_type 用 `TASK_TYPES` 常量穷举（见 [`api/tasks.ts`](../frontend/src/api/tasks.ts)），不要在前端做泛化的"任务插件"框架。

---

## 2. 路由与全局布局

### 2.1 路由表

| 路径 | 页面 | 说明 |
|------|------|------|
| `/` | **Dashboard（主页）** | 入口面板：启动任务、各模块入口、最近 10 个 run |
| `/tasks` | **任务列表** | 全量 run，支持 task_type / status 筛选与翻页 |
| `/tasks/:runId` | **任务详情** | 单 run 状态、统计、文件结果、日志 |
| `/config` | **配置中心** | 全局配置只读 + 各 task_type 专属配置（Tab 切换） |
| `/media` | **媒体浏览器** | 对 `/media` 树做懒加载浏览（次要工具） |

所有路由通过 [`App.tsx`](../frontend/src/App.tsx) 使用 React Router v7 布局路由模式注册，共享 `AppShell` 外壳。

### 2.2 全局壳（AppShell）

所有页面共享 [`components/layout/AppShell.tsx`](../frontend/src/components/layout/AppShell.tsx)：

- **[TopNav](../frontend/src/components/layout/TopNav.tsx)**：左侧应用名称；右侧导航链接（Dashboard / 任务列表 / 配置 / 媒体）。活跃态通过 `NavLink` 计算，`/` 链接使用 `end` 避免误高亮。
- **[GlobalRunBanner](../frontend/src/components/layout/GlobalRunBanner.tsx)**：固定在 TopNav 下方，仅当存在 `pending/running` 的 run 时显示。内容：`run_name` · 状态徽标 · 已运行时长（本地每秒刷新）· "查看详情"链接 · "取消"按钮。数据源：`useActiveTaskRun()`（3s 常驻轮询）。
- **ContentArea**：路由出口（`<Outlet />`）。
- 子页面的最外层不要再用 `<main>`，`AppShell` 中 `<main className="flex-1">` 是唯一出现点。

---

## 3. 页面：Dashboard（`/`）

### 3.1 目标

让用户在 **一屏内** 完成两件事：(a) 决定是否启动新任务；(b) 概览最近的执行状况。不承担列表浏览、详情查看、配置编辑职责，这些都跳出。

### 3.2 模块组成

| 模块 | 能力 | 数据源 |
|------|------|--------|
| [`NewTaskPanel`](../frontend/src/components/task/NewTaskPanel.tsx) | 启动新任务的统一入口（详见 §3.3） | `useStartTask(taskType)` |
| [`QuickLinks`](../frontend/src/components/task/QuickLinks.tsx) | 4 张大卡片：配置中心、媒体浏览器、任务列表、文档/帮助 | 静态 |
| [`RecentRunsList`](../frontend/src/components/task/RecentRunsList.tsx) | 最近 10 个 run，每行：状态徽标 · run_name · task_type · dry_run 标记 · 耗时 · 概要统计 · 跳转 | `useTaskRunList()` 截前 10 条 |
| [`SystemInfoPanel`](../frontend/src/components/system/SystemInfoPanel.tsx)（compact 模式） | 版本号、`base_dir`、`workspace_root`（JAV/Raw）、媒体挂载状态 | `useSystemInfo()` |

### 3.3 `NewTaskPanel`（核心）

- 两张启动卡（[`StartTaskCard`](../frontend/src/components/task/StartTaskCard.tsx)），分别对应 `jav_video_organizer` 与 `raw_file_organizer`。
- 每张卡从 `useTaskConfig(taskType)` 读取并展示当前 `workspace_root` 与 `enabled` 状态。
- Dry Run toggle 默认 ON，用户必须显式关掉才会真实写磁盘。
- 触发类型固定 `manual`，前端不暴露选择。
- 启动按钮的禁用条件（任一即禁用，按优先级显示提示文案）：
  1. 当前已有 active run（互斥）
  2. 该 task_type 配置 `enabled=false`
  3. Mutation 处于 `isPending`
- 启动成功后：失效 `["tasks","runs"]` 与 `["tasks","active"]` 查询；路由跳转到新建 run 的详情页 `/tasks/{run_id}`。

---

## 4. 页面：任务列表（`/tasks`）

### 4.1 目标

按筛选条件浏览全部历史 run，作为进入详情的导航页。此页 **只读**，不直接做启动/配置。

### 4.2 模块组成

| 模块 | 说明 |
|------|------|
| [`RunFilterBar`](../frontend/src/components/task/RunFilterBar.tsx) | 三段筛选：`task_type`（all / jav / raw），`status`（all / running / completed / failed / cancelled / pending） |
| [`RunTable`](../frontend/src/components/task/RunTable.tsx) | 每行：状态徽标 · run_name · task_type · 触发类型 · dry_run 标记 · 开始/结束时间 · 总耗时 · 概要计数（total / success / error / skipped） · 操作（详情、取消、删除） |
| [`RunPagination`](../frontend/src/components/task/RunPagination.tsx) | 服务端分页：`page` + `page_size`；展示总数 |

### 4.3 设计要点

- **筛选与分页全部走 URL search params**（`?task_type=jav&status=failed&page=2`），便于刷新/分享/回退。
- "取消"按钮仅对 `running/pending` 显示；"删除"按钮仅对终态（`completed/failed/cancelled`）显示，且二次确认。
- 行操作由 [`RunRowActions`](../frontend/src/components/task/RunRowActions.tsx) 封装，按 run 状态控制按钮显隐。

---

## 5. 页面：任务详情（`/tasks/:runId`）

### 5.1 目标

完整呈现一个 run 的执行结果，是问题排查与归因的主要页面。状态机实时反映后端 `FileTaskRunStatus`。

### 5.2 模块组成（Tab 切分）

#### Tab A：概览（默认）

| 模块 | 说明 |
|------|------|
| [`RunHeader`](../frontend/src/components/task/RunHeader.tsx) | run_name、task_type 徽标、状态徽标（含轮询动画）、dry_run 标记、触发类型 |
| [`RunTimeline`](../frontend/src/components/task/RunTimeline.tsx) | 创建时间 / 开始时间 / 结束时间 / 已耗时（活跃中实时滚动）、`error_message`（FAILED 时高亮） |
| [`RunActions`](../frontend/src/components/task/RunActions.tsx) | 「取消」（仅 active）/「重跑」（沿用当前 `task_type` 与 `dry_run`，受全局互斥约束）/「删除」（仅终态，二次确认） |
| [`StatsSummaryGrid`](../frontend/src/components/task/StatsSummaryGrid.tsx) | 通用统计：total / success / error / skipped / total_duration_ms |
| [`RawPhaseStats`](../frontend/src/components/task/RawPhaseStats.tsx) | **仅 Raw 任务显示**：把 `phase1_*` / `phase2_*` / `phase3_*` 字段按阶段 1/2/3 分组卡片化展示。字段含义见 [`task_run.py`](../src/j_file_kit/app/file_task/domain/task_run.py) 与 [`RAW_FILE_PROCESSING_PIPELINE.md`](./RAW_FILE_PROCESSING_PIPELINE.md) |

#### Tab B：文件结果

| 模块 | 说明 |
|------|------|
| [`ResultFilterBar`](../frontend/src/components/task/ResultFilterBar.tsx) | 筛选：`decision_type`（move / delete / skip）、`success`（成功 / 失败）、关键字（按 `file_stem` / `serial_id`） |
| [`ResultTable`](../frontend/src/components/task/ResultTable.tsx) | 每行：source_path、stem、file_type、serial_id（JAV）、decision、target_path、success、error_message、duration_ms |
| [`RunPagination`](../frontend/src/components/task/RunPagination.tsx) | 服务端分页 |

结果筛选与分页使用 `results_*` search params（`results_decision`、`results_success`、`results_q`、`results_page`、`results_page_size`），避免与日志 Tab 参数互污。

#### Tab C：日志

- 使用 `GET /api/tasks/{run_id}/logs?offset=&limit=` 按行分页拉取结构化日志（loguru JSON Lines）。
- [`LogViewer`](../frontend/src/components/task/LogViewer.tsx) 渲染每行的时间戳、级别、消息与 extra 字段。
- [`LogPagination`](../frontend/src/components/task/LogPagination.tsx) 使用 `logs_offset` / `logs_limit` search params，避免与结果 Tab 参数互污。
- 日志文件不存在（如 run 快速失败尚未写文件）时返回空分页，前端展示"暂无任务日志"。

### 5.3 数据获取策略

- `useTaskRunDetail(runId)`：active 时 2s 轮询，进入终态后停止。
- `useTaskRunResults(runId, filter, page)`：active 时 5s 轮询，终态停止。
- `useTaskRunLogs(runId, offset, limit)`：active 时 3s 拉增量，终态停止。
- 切 Tab 不重置查询缓存，TanStack Query 自动按 key 复用。

---

## 6. 页面：配置中心（`/config`）

### 6.1 结构

页面顶部三段 Tab：

1. **全局配置**：系统信息只读展示
2. **JAV 视频整理**（`jav_video_organizer`）
3. **Raw 文件整理**（`raw_file_organizer`）

### 6.2 Tab 1：全局配置（只读）

展示两块只读面板：

| 面板 | 展示内容 | 数据来源 |
|------|---------|---------|
| [`SystemInfoPanel`](../frontend/src/components/system/SystemInfoPanel.tsx)（完整模式） | `app_version`、`env`、`base_dir`、`media_root`、`jav_media_root`、`raw_media_root`、`media_mounted` | `useSystemInfo()` → `GET /api/system/info` |
| [`SystemDefaultsPanel`](../frontend/src/components/system/SystemDefaultsPanel.tsx) | 视频/图片等扩展名集合、Raw 关键字集合、JAV 命名规则；长列表展示前 8 项 + 总数摘要 | `useSystemFileTypeDefaults()` → `GET /api/system/file-type-defaults` |

这些数据来自 `organizer_defaults.py` 等后端常量，前端只读展示，不在前端维护第二份副本。

### 6.3 Tab 2：JAV 视频整理配置

后端 schema 见 [`JavVideoOrganizeConfig`](../src/j_file_kit/app/file_task/application/jav_task_config.py)。表单由 [`TaskConfigPanel`](../frontend/src/components/config/TaskConfigPanel.tsx) 渲染，分组：

| 分组 | 字段 | 控件 |
|------|------|------|
| 工作区 | `workspace_root` | [`PathInput`](../frontend/src/components/config/PathInput.tsx)（路径输入 + 选择目录按钮，弹出 [`MediaPickerDialog`](../frontend/src/components/config/MediaPickerDialog.tsx)） |
| Misc 删除规则 | `misc_file_delete_rules.max_size` | 数字输入（字节） |
| 视频小文件 | `video_small_delete_bytes` | 数字输入；可清空（`null` 表示不启用） |
| 收件箱预删除 | `inbox_delete_rules.exact_stems`、`inbox_delete_rules.max_size_bytes` | [`StemTagsInput`](../frontend/src/components/config/StemTagsInput.tsx) + 数字输入 |
| 启用开关 | `enabled` | Switch |

提交：调用 `useUpdateTaskConfig("jav_video_organizer")` PATCH。  
**前端路径校验**：`workspace_root` 必须以 `jav_media_root` 为前缀（从 `useSystemInfo()` 取），校验失败不发请求，见 [`lib/paths.ts`](../frontend/src/lib/paths.ts)。  
**PATCH 浅合并**：服务端 `merge_jav_video_organizer_config()` 是顶层合并，`inbox_delete_rules` 必须提交完整子对象，只提交其中一个子字段会覆盖其他子字段。

### 6.4 Tab 3：Raw 文件整理配置

后端 schema 见 [`RawFileOrganizeConfig`](../src/j_file_kit/app/file_task/application/raw_task_config.py)。当前仅 `workspace_root` + `enabled` 两个字段，表单简单；预留扩展位，未来阶段规则若下放 YAML 会加在这里。

### 6.5 通用约束

- 所有 PATCH 操作成功后：toast + 失效相关 query。
- 修改 `workspace_root` 后用 banner 提示"已变更工作区，下一次任务启动将使用新路径"。
- 失败时把后端 `{code, message}` 直接展示（见 [`lib/errors.ts`](../frontend/src/lib/errors.ts)）。
- FastAPI 可能返回 `{ detail: { code, message } }` 或根级 `{ code, message }` 两种错误体形态，[`api/client.ts`](../frontend/src/api/client.ts) 已兼容两种。

---

## 7. 已实现的接口清单

> 接口实现集中在 [`app/file_task/api.py`](../src/j_file_kit/app/file_task/api.py) 和 [`app/system/api.py`](../src/j_file_kit/app/system/api.py)。

### 7.A 任务相关

| ID | 端点 | 请求参数 | 响应关键字段 |
|----|------|---------|------------|
| **A1** | `GET /api/tasks` | `task_type`（可选）、`status`（可选）、`page`（默认 1）、`page_size`（默认 20，上限 100） | `runs[]`（含 `task_type`、`trigger_type`、`dry_run`、`duration_ms`、`statistics_summary`）、`total`、`page`、`page_size` |
| **A2** | `GET /api/tasks/{run_id}` | — | `task_type`、`trigger_type`、`dry_run`、`status`、`duration_ms`、完整 `statistics`（含 Raw `phase*` 全字段） |
| **A3** | `GET /api/tasks/{run_id}/results` | `decision_type`（可选：move/delete/skip）、`success`（可选：true/false）、`q`（按 `file_stem`/`serial_id` 模糊搜索）、`page`、`page_size` | `results[]`（含 `source_path`、`file_stem`、`file_type`、`serial_id`、`decision_type`、`target_path`、`success`、`error_message`、`duration_ms`）、`total`、`page`、`page_size` |
| **A4** | `DELETE /api/tasks/{run_id}` | — | `run_id`、`message`；仅允许终态（`completed/failed/cancelled`），否则返回 `TASK_NOT_TERMINAL`；级联删 `file_results` 行 + 日志文件 |
| **A5** | `GET /api/tasks/{run_id}/logs` | `offset`（默认 0）、`limit`（默认 100，上限 500） | `total_lines`、`offset`、`limit`、`lines[]`（含 `line_no`、`ts`、`level`、`msg`、`fields`） |
| **A6** | `GET /api/tasks/active` | — | `null` 或当前 `pending/running` run 的摘要（`run_id`、`run_name`、`task_type`、`status`、`start_time` 等） |

### 7.B 系统/元数据

| ID | 端点 | 响应关键字段 |
|----|------|------------|
| **B1** | `GET /api/system/info` | `app_version`、`env`、`base_dir`、`media_root`、`jav_media_root`、`raw_media_root`、`media_mounted` |
| **B2** | `GET /api/system/file-type-defaults` | `extensions`（各文件类型扩展名集合，稳定排序）、`raw`（关键字集合，保留后端定义顺序）、`jav`（`vr_serial_prefixes`、`filename_strip_substrings` 等） |

### 7.C 其他已实现接口

| 端点 | 说明 |
|------|------|
| `POST /api/tasks/{task_type}/start` | 响应已包含 `dry_run` 回显 |
| `POST /api/tasks/{run_id}/cancel` | 取消 active run |
| `GET /api/file-task/config/{task_type_slug}` | 读取任务配置（`jav-video-organizer` / `raw-file-organizer`） |
| `PATCH /api/file-task/config/{task_type_slug}` | 部分更新任务配置 |
| `GET /api/media/directories` | 按路径懒加载目录列表，供 `MediaPickerDialog` 使用 |

---

## 8. 数据获取与轮询策略

所有 hook 定义见 [`api/tasks.ts`](../frontend/src/api/tasks.ts)、[`api/system.ts`](../frontend/src/api/system.ts)、[`api/config.ts`](../frontend/src/api/config.ts)、[`api/media.ts`](../frontend/src/api/media.ts)。

| Hook | 端点 | 轮询条件 | 备注 |
|------|------|---------|------|
| `useActiveTaskRun()` | A6 | **常驻 3s 轮询** | 全局 banner、启动按钮禁用态 |
| `useTaskRunList(params)` | A1 | 仅在列表页挂载时 | 服务端分页；Dashboard 截前 10 条 |
| `useTaskRunDetail(runId)` | A2 | active 时 2s；终态停止 | 参考 `refetchInterval` 回调写法 |
| `useTaskRunResults(runId, filter, page)` | A3 | active 时 5s；终态停止 | 详情 Tab B |
| `useTaskRunLogs(runId, offset, limit)` | A5 | active 时 3s 拉增量；终态停止 | 详情 Tab C |
| `useStartTask(taskType)` | `POST .../start` | Mutation | 成功后 invalidate active + runs |
| `useCancelTaskRun(runId)` | `POST .../cancel` | Mutation | — |
| `useDeleteTaskRun(runId)` | A4 | Mutation | 成功后跳回列表或 invalidate |
| `useTaskConfig(taskType)` | `GET .../config/...` | 不轮询 | — |
| `useUpdateTaskConfig(taskType)` | `PATCH .../config/...` | Mutation | 成功后 invalidate config |
| `useMediaDirectories(path)` | `GET /api/media/directories` | 不轮询；单层懒加载 | `MediaPickerDialog` 按节点展开时请求 |
| `useSystemInfo()` | B1 | 不轮询；`staleTime: Infinity` | 配置页路径校验、Dashboard 页脚 |
| `useSystemFileTypeDefaults()` | B2 | 不轮询；`staleTime: Infinity` | 全局配置 Tab 只读展示 |

`QueryClient` 的全局 `staleTime: 30_000` 保留，单 hook 可覆盖。

---

## 9. 前端模块清单

### 9.1 页面（`pages/`）

| 文件 | 路由 |
|------|------|
| [`DashboardPage.tsx`](../frontend/src/pages/DashboardPage.tsx) | `/` |
| [`TasksListPage.tsx`](../frontend/src/pages/TasksListPage.tsx) | `/tasks` |
| [`TaskDetailPage.tsx`](../frontend/src/pages/TaskDetailPage.tsx) | `/tasks/:runId` |
| [`ConfigPage.tsx`](../frontend/src/pages/ConfigPage.tsx) | `/config` |
| [`MediaPage.tsx`](../frontend/src/pages/MediaPage.tsx) | `/media` |

### 9.2 布局组件（`components/layout/`）

| 组件 | 用途 |
|------|------|
| [`AppShell`](../frontend/src/components/layout/AppShell.tsx) | TopNav + GlobalRunBanner + Outlet |
| [`TopNav`](../frontend/src/components/layout/TopNav.tsx) | 应用名称 + 路由导航 |
| [`GlobalRunBanner`](../frontend/src/components/layout/GlobalRunBanner.tsx) | 全局活跃 run 状态条 |

### 9.3 任务组件（`components/task/`）

| 组件 | 用途 |
|------|------|
| [`StatusBadge`](../frontend/src/components/task/StatusBadge.tsx) | 5 种状态的统一徽标 |
| [`TaskTypeBadge`](../frontend/src/components/task/TaskTypeBadge.tsx) | jav / raw 两色徽标 |
| [`DryRunBadge`](../frontend/src/components/task/DryRunBadge.tsx) | 醒目橙色徽标 |
| [`StartTaskCard`](../frontend/src/components/task/StartTaskCard.tsx) | Dashboard 单个 task_type 启动卡 |
| [`NewTaskPanel`](../frontend/src/components/task/NewTaskPanel.tsx) | Dashboard 双任务启动面板 |
| [`QuickLinks`](../frontend/src/components/task/QuickLinks.tsx) | Dashboard 快捷入口 |
| [`RecentRunsList`](../frontend/src/components/task/RecentRunsList.tsx) | Dashboard 最近任务列表 |
| [`RunHeader`](../frontend/src/components/task/RunHeader.tsx) | 详情页头部 |
| [`RunTimeline`](../frontend/src/components/task/RunTimeline.tsx) | 时间线与错误信息 |
| [`RunActions`](../frontend/src/components/task/RunActions.tsx) | 取消 / 重跑 / 删除操作 |
| [`StatsSummaryGrid`](../frontend/src/components/task/StatsSummaryGrid.tsx) | 通用 5 项统计卡片 |
| [`RawPhaseStats`](../frontend/src/components/task/RawPhaseStats.tsx) | Raw 三阶段统计卡片 |
| [`RunFilterBar`](../frontend/src/components/task/RunFilterBar.tsx) | 任务列表筛选栏 |
| [`RunTable`](../frontend/src/components/task/RunTable.tsx) | 任务列表表格 |
| [`RunPagination`](../frontend/src/components/task/RunPagination.tsx) | 任务列表分页 |
| [`RunRowActions`](../frontend/src/components/task/RunRowActions.tsx) | 行级取消 / 删除 / 详情按钮 |
| [`ResultFilterBar`](../frontend/src/components/task/ResultFilterBar.tsx) | 文件结果筛选栏 |
| [`ResultTable`](../frontend/src/components/task/ResultTable.tsx) | 文件结果表格 |
| [`LogViewer`](../frontend/src/components/task/LogViewer.tsx) | 日志行表格 |
| [`LogPagination`](../frontend/src/components/task/LogPagination.tsx) | offset/limit 日志分页 |

### 9.4 配置组件（`components/config/`）

| 组件 | 用途 |
|------|------|
| [`TaskConfigPanel`](../frontend/src/components/config/TaskConfigPanel.tsx) | JAV / Raw 配置表单 |
| [`MediaPickerDialog`](../frontend/src/components/config/MediaPickerDialog.tsx) | 媒体目录懒加载树选择弹层 |
| [`PathInput`](../frontend/src/components/config/PathInput.tsx) | 路径输入 + 选择目录按钮 |
| [`StemTagsInput`](../frontend/src/components/config/StemTagsInput.tsx) | `exact_stems` 多值标签输入 |

### 9.5 系统组件（`components/system/`）

| 组件 | 用途 |
|------|------|
| [`SystemInfoPanel`](../frontend/src/components/system/SystemInfoPanel.tsx) | 系统信息只读面板，支持 full / compact 两种显示模式 |
| [`SystemDefaultsPanel`](../frontend/src/components/system/SystemDefaultsPanel.tsx) | 后端默认字典只读摘要面板 |

### 9.6 工具库（`lib/`）

| 文件 | 用途 |
|------|------|
| [`lib/errors.ts`](../frontend/src/lib/errors.ts) | 后端错误码 → 用户友好文案映射 |
| [`lib/paths.ts`](../frontend/src/lib/paths.ts) | 路径前缀校验（配置页保存前校验） |
| [`lib/task-config.ts`](../frontend/src/lib/task-config.ts) | 从任务配置中安全读取 `workspace_root` |
| [`lib/task-labels.ts`](../frontend/src/lib/task-labels.ts) | task_type / status 等枚举的显示文案 |
| [`lib/time.ts`](../frontend/src/lib/time.ts) | 时间格式化与耗时格式化 |
| [`lib/utils.ts`](../frontend/src/lib/utils.ts) | shadcn `cn()` class 合并工具 |

---

## 10. 里程碑（已全部完成）

| 阶段 | 范围 | 后端依赖 |
|------|------|----------|
| **M1：骨架** | AppShell + 路由 + 5 个页面存根 | 无 |
| **M2：Dashboard MVP** | NewTaskPanel + RecentRunsList + GlobalRunBanner | A6 |
| **M3：任务详情 MVP** | 概览 Tab（含 Raw phase 卡片）+ 取消/重跑 | A2 |
| **M4：任务列表 MVP** | 筛选 + 分页 + 行操作（不含删除） | A1 |
| **M5：配置中心** | JAV / Raw 表单 + MediaPickerDialog | B1 |
| **M6：文件结果 Tab** | 详情页 Tab B | A3 |
| **M7：日志 Tab + 删除** | 详情页 Tab C + 列表/详情删除按钮 | A5、A4 |
| **M8：全局配置只读 + 系统信息** | 配置 Tab 1 + Dashboard 页脚 | B1、B2 |

**后续可迭代方向**：日志 SSE 实时流（替代轮询）、系统默认字典搜索/展开交互、文件结果导出。

---

## 11. 常见陷阱（给前端 AI Agent）

- **不要在前端自行 `fetch`**：所有请求必须经 [`apiClient`](../frontend/src/api/client.ts)，统一错误体 `{ code, message }`。
- **不要绕开 hook 直接调 React Query**：每个端点都先在 `api/*.ts` 加一个 hook，页面只消费 hook，便于改轮询策略与做 mock。
- **task_type 不要散落**：始终用 `TASK_TYPES.JAV` / `TASK_TYPES.RAW`（[`api/tasks.ts`](../frontend/src/api/tasks.ts)），不要在组件里写裸字符串。
- **互斥状态以 `useActiveTaskRun()` 为准**：不要用 `useTaskRunList` 的第一行推断"是否有任务在跑"，那会浪费带宽并产生竞态。
- **dry_run 默认 ON**：UI 默认安全，用户必须显式关掉 toggle 才会真删/真移。
- **路径输入校验**：`workspace_root` 前端先用 `useSystemInfo()` 拿到 root 做前缀校验（见 [`lib/paths.ts`](../frontend/src/lib/paths.ts)），再发请求；只让后端做兜底，不让后端做主校验入口。
- **轮询要在终态停止**：参考 `useTaskRunDetail` 中 `refetchInterval` 的回调写法，避免 completed 后继续 poll 制造无意义请求。
- **FastAPI 错误体兼容**：部分接口返回 `{ detail: { code, message } }` 而非根级 `{ code, message }`，[`apiClient`](../frontend/src/api/client.ts) 已同时兼容两种形态；添加新接口时注意核对实际错误体格式。
- **JAV PATCH 浅合并**：服务端 `merge_jav_video_organizer_config()` 是顶层合并，`inbox_delete_rules` 必须提交完整子对象，只提交其中一个子字段会覆盖其他子字段。
- **results / logs URL 参数需加前缀**：文件结果 Tab 使用 `results_*` 前缀，日志 Tab 使用 `logs_*` 前缀，避免同一详情页下多 Tab 参数互相污染。
- **日志文件不存在不等于错误**：run 存在但日志文件尚未创建时，A5 返回空分页；前端展示"暂无任务日志"，不要当作异常处理。
- **长列表只展示摘要**：系统默认字典等可能很长的集合，前端只展示前 8 项 + 总数，避免 UI 被大集合淹没。
