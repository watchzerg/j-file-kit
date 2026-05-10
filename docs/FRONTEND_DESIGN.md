# 前端页面设计文档

本文档面向 **后续接手的开发者与 AI Agent**，从「业务页面 → 模块 → 后端接口」三个维度定义前端的功能边界。

- 技术栈、目录结构、构建集成请参考 [`ARCHITECTURE.md` §12 前端架构](./ARCHITECTURE.md)，本文不再重复。
- 业务规则（JAV 分析 / Raw 三阶段）请分别参考 [`JAV_VIDEO_PROCESSING_PIPELINE.md`](./JAV_VIDEO_PROCESSING_PIPELINE.md) 与 [`RAW_FILE_PROCESSING_PIPELINE.md`](./RAW_FILE_PROCESSING_PIPELINE.md)。
- 本设计是 **第一版蓝图**：先把页面骨架与必要后端接口对齐；细节交互、设计 token、组件库选型在落地时迭代。

---

## 1. 设计原则

1. **后端互斥 → 前端可见**：`FileTaskRunManager` 全局只允许一个 run 处于 `pending/running`（见 [`file_task_run_manager.py`](../src/j_file_kit/infrastructure/file_task/file_task_run_manager.py)）。前端必须在所有"启动任务"入口共享这一状态：通过 **顶部全局任务条** 与 **启动按钮的禁用态** 把约束直接呈现给用户，而非让后端兜底报 `FileTaskAlreadyRunningError`。
2. **薄页面 + 厚 hooks**：`pages/` 只组合布局与组件；所有数据获取、轮询、Mutation 全部走 `api/*.ts` 中的 TanStack Query hook（见现有 `api/tasks.ts`、`api/config.ts`、`api/media.ts` 的写法）。
3. **以"任务 run"为核心实体**：所有页面入口都能跳转到 **任务详情**，详情页是数据最完整、刷新策略最复杂的页面。
4. **dry_run 是一等公民**：JAV / Raw 都支持 dry_run 预览。新建任务、任务卡、详情页都需要明显的 dry_run 标记（颜色或徽标），避免用户误以为已实际改动磁盘。
5. **不堆砌可扩展性**：当前只有 2 个 task_type。task_type 用 `TASK_TYPES` 常量穷举（见 [`api/tasks.ts`](../frontend/src/api/tasks.ts)），不要在前端做泛化的"任务插件"框架。

---

## 2. 路由与全局布局

### 2.1 路由表

| 路径 | 页面 | 说明 |
|------|------|------|
| `/` | **Dashboard（主页）** | 入口面板：启动任务、各模块入口、最近 10 个 run |
| `/tasks` | **任务列表** | 全量 run，支持 task_type / status 筛选与翻页 |
| `/tasks/:runId` | **任务详情** | 单 run 状态、统计、文件结果、日志 |
| `/config` | **配置中心** | 全局配置 + 各 task_type 专属配置（Tab 切换） |
| `/media` | **媒体浏览器** | 已有占位，对 `/media` 树做懒加载浏览（次要工具） |

> 当前 `App.tsx` 仅注册了 `/`、`/config`、`/media`；本设计需要新增 `/tasks` 与 `/tasks/:runId` 两条路由，并把 `/` 从 `TasksPage` 改造为真正的 Dashboard，把"任务列表"职责迁出。

### 2.2 全局壳（AppShell）

所有页面共享同一壳层，建议拆出 `components/layout/AppShell.tsx`：

- **TopNav**：左侧 logo / 名称；右侧导航链接（Dashboard / 任务列表 / 配置 / 媒体），保留版本号显示位（来自 `APP_VERSION`，见后文新增接口建议）。
- **GlobalRunBanner**：固定在 TopNav 下方的状态条，仅当存在 `pending/running` 的 run 时显示。  
  内容：`{run_name}` · 状态徽标 · 已运行时长 · "查看详情" 链接 · "取消" 按钮。  
  数据源：`useActiveTaskRun()`（见 §8 轮询策略）。
- **ContentArea**：路由出口（`<Outlet />`）。
- **Toast 区**：统一承载 Mutation 成功/失败提示。

---

## 3. 页面：Dashboard（`/`）

### 3.1 目标

让用户在 **一屏内** 完成两件事：(a) 决定是否启动新任务；(b) 概览最近的执行状况。  
**不承担**列表浏览、详情查看、配置编辑职责，这些都跳出。

### 3.2 模块组成

| 模块 | 能力 | 数据源 |
|------|------|--------|
| `RunningTaskCard`（可选） | 当前活跃 run 的醒目卡片：进度（如有）、已耗时、取消按钮、跳转详情 | `useActiveTaskRun()` |
| `NewTaskPanel` | 启动新任务的统一入口（详见 §3.3） | `useStartTask(taskType)` |
| `QuickLinks` | 4 张大卡片：「配置中心」「媒体浏览器」「任务列表」「文档/帮助」 | 静态 |
| `RecentRunsList` | 最近 10 个 run，每行：状态徽标 · run_name · task_type · 触发类型 · 耗时 · 概要统计 · 跳转 | `useTaskRunList()` 截前 10 条 |
| `SystemInfoFooter` | 版本号、`workspace_root`(JAV/Raw) 是否就绪、`/media` 挂载状态 | 新增 `GET /api/system/info`（见 §7） |

### 3.3 `NewTaskPanel`（核心）

- 上方两张卡片，分别对应 `jav_video_organizer` 与 `raw_file_organizer`。每张卡片显示：
  - 任务名称、一行说明；
  - **当前 `workspace_root`**（从 `useTaskConfig` 取，让用户启动前确认路径）；
  - **enabled 状态**（若 `enabled=false` 则禁用启动按钮，并提示"请先在配置中启用"）；
  - 启动控件：
    - "**Dry Run（预览）**" toggle（默认 ON，避免误操作）；
    - "**启动**" 主按钮 → `useStartTask(taskType).mutate({ dry_run })`；
    - 触发类型固定为 `manual`，前端不暴露选择。
- 启动按钮的禁用条件（任一即禁用，按优先级显示提示文案）：
  1. 当前已有活跃 run（互斥）；
  2. 该 task_type 配置 `enabled=false`；
  3. Mutation 处于 `isPending`。
- 启动成功后：
  - 失效 `["tasks","runs"]` 与 `["tasks","active"]` 查询；
  - 路由跳转到新建 run 的详情页 `/tasks/{run_id}`。

### 3.4 `RecentRunsList` 行级信息

`useTaskRunList()` 当前已返回足够字段（`run_id` / `run_name` / `status` / `start_time` / `end_time`）。  
为了"概要统计"列（用户提到的"简报"），需要 list 接口补充 `task_type` 与 `statistics` 摘要（见 §7-A1）。

---

## 4. 页面：任务列表（`/tasks`）

### 4.1 目标

按筛选条件浏览全部历史 run，作为进入详情的导航页。此页 **只读**，不直接做启动/配置。

### 4.2 模块组成

| 模块 | 说明 |
|------|------|
| `RunFilterBar` | 三段筛选：`task_type`（all / jav / raw），`status`（all / running / completed / failed / cancelled / pending），日期范围（可选 v2） |
| `RunTable` | 每行：状态徽标 · run_name · task_type · 触发类型 · dry_run 标记 · 开始/结束时间 · 总耗时 · 概要计数（total / success / error / skipped） · 操作（详情、取消、删除） |
| `Pagination` | 服务端分页：`page` + `page_size`；展示总数 |

### 4.3 设计要点

- **筛选与分页全部走 URL search params**（如 `?task_type=jav&status=failed&page=2`），便于刷新/分享/回退。
- "取消" 按钮仅对 `running/pending` 显示；"删除" 按钮仅对终态显示，且二次确认。
- 删除依赖新增接口（见 §7-A4），如果暂不实现，先在 v1 隐藏该按钮即可。
- 当前 `GET /api/tasks` 不支持筛选与分页（见 [`api.py` `list_runs`](../src/j_file_kit/app/file_task/api.py)），必须先扩展（§7-A1）。

---

## 5. 页面：任务详情（`/tasks/:runId`）

### 5.1 目标

完整呈现一个 run 的执行结果，是问题排查与归因的主要页面。状态机实时反映后端 `FileTaskRunStatus`。

### 5.2 模块组成（建议 Tab 切分）

#### Tab A：概览（默认）

| 模块 | 说明 |
|------|------|
| `RunHeader` | run_name、task_type 徽标、状态徽标（含轮询动画）、dry_run 标记、触发类型 |
| `RunTimeline` | 创建时间 / 开始时间 / 结束时间 / 已耗时（活跃中实时滚动）、`error_message`（FAILED 时高亮） |
| `RunActions` | 「取消」（仅 active）/「重跑」（用同 task_type + 同 dry_run 重新启动，受 §3.3 互斥规则约束）/「删除」 |
| `StatsSummaryGrid` | 通用统计：total / success / error / skipped / total_duration_ms（来自 `FileTaskRunStatistics`） |
| `RawPhaseStats` | **仅 Raw 任务显示**：把 `phase1_*` / `phase2_*` / `phase3_*` 字段按"阶段 1 收散落 / 阶段 2 子目录处理（细分 2.1–2.4） / 阶段 3 分流"分组卡片化展示。字段含义见 [`FileTaskRunStatistics`](../src/j_file_kit/app/file_task/domain/task_run.py) 与 `RAW_FILE_PROCESSING_PIPELINE.md` |

> 后端 `FileTaskRunStatistics` 已经把 Raw 的 phase 计数全部建模，但当前 `GET /api/tasks/{run_id}` 只返回 `total_items` 一项（见 [`api.py` `get_run_status`](../src/j_file_kit/app/file_task/api.py)）。需要扩展（§7-A2）。

#### Tab B：文件结果

| 模块 | 说明 |
|------|------|
| `ResultFilterBar` | 筛选：`decision_type`（move / delete / skip）、`success`（成功 / 失败）、关键字（按 `file_stem` / `serial_id`） |
| `ResultTable` | 每行：source_path、stem、file_type、serial_id（JAV）、decision、target_path、success、error_message、duration_ms |
| `Pagination` | 服务端分页 |

依赖新增接口 `GET /api/tasks/{run_id}/results`（§7-A3）。这是任务详情最有价值的功能：把目前只能看 SQLite 才能看到的 `file_results` 数据可视化。

#### Tab C：日志（v2 推荐，v1 可隐藏）

- 后端日志写在 `{base_dir}/logs/{run_name}_{run_id}.jsonl`，结构化 JSON 行。
- v1：提供 `GET /api/tasks/{run_id}/logs?offset=&limit=` 分页拉取（§7-A5）；前端用虚拟列表渲染。
- v2：升级为 SSE 流式（active 时实时跟随）。

### 5.3 数据获取策略

- `useTaskRunDetail(runId)`：active 时 2s 轮询、终态后停止（参考现有 `useTaskRunStatus` 的 `refetchInterval` 写法）。
- `useTaskRunResults(runId, filter, page)`：active 时 5s 轮询；终态后只拉一次 + 手动刷新按钮。
- 切 Tab 不重置查询缓存，TanStack Query 自动按 key 复用。

---

## 6. 页面：配置中心（`/config`）

### 6.1 结构

页面顶部三段 Tab（与未来 task_type 数对齐）：

1. **全局配置**（v1 占位）
2. **JAV 视频整理**（`jav_video_organizer`）
3. **Raw 文件整理**（`raw_file_organizer`）

### 6.2 Tab 1：全局配置（占位）

后端目前没有真正的"全局配置"端点，但前端先把这个 Tab 占住，承载下面这些代码常量的 **只读展示**，给用户一个"系统默认值"的可见性：

| 区块 | 展示内容 | 数据来源 |
|------|---------|---------|
| 路径与挂载 | `MEDIA_ROOT`、`JAV_MEDIA_ROOT`、`RAW_MEDIA_ROOT`、`{base_dir}` | 新增 `GET /api/system/info`（§7-B1） |
| 文件类型字典 | 视频/图片/音频/压缩 等扩展名集合（来自 `organizer_defaults.py`） | 新增 `GET /api/system/file-type-defaults`（§7-B2，可选） |
| Raw 关键字字典 | junk / video / pic / audio 等关键字集合 | 同上 |

> 这些数据当前都是代码常量，未来可能下放到配置库。先用只读展示占位，避免后续要做编辑时前端从零起步。

### 6.3 Tab 2：JAV 视频整理配置

后端 schema 见 [`JavVideoOrganizeConfig`](../src/j_file_kit/app/file_task/application/jav_task_config.py)。表单分组：

| 分组 | 字段 | 控件 |
|------|------|------|
| 工作区 | `workspace_root` | 路径输入 + "选择目录"按钮（弹出 `MediaPickerDialog`，复用 `/api/media/directories` 懒加载） |
| Misc 删除规则 | `misc_file_delete_rules.max_size`（仅可调字段；`extensions` / `keywords` 由后端 strip 掉，见 `strip_misc_extensions_from_yaml`） | 数字输入（字节） |
| 视频小文件 | `video_small_delete_bytes` | 数字输入；可清空（None 表示不启用） |
| 收件箱预删除 | `inbox_delete_rules.exact_stems`、`inbox_delete_rules.max_size_bytes` | tag 编辑器（`exact_stems` 多值）、数字输入 |
| 启用开关 | `enabled` | Switch，提交时一并 PATCH |

提交：调用 `useUpdateTaskConfig("jav_video_organizer")`，部分字段 PATCH。  
**前端镜像校验**：`workspace_root` 必须以 `JAV_MEDIA_ROOT` 为前缀，否则不发请求（避免被后端 `INVALID_CONFIG` 兜底）。从 §7-B1 的 system info 接口拿到 root 值。

### 6.4 Tab 3：Raw 文件整理配置

后端 schema 见 [`RawFileOrganizeConfig`](../src/j_file_kit/app/file_task/application/raw_task_config.py)，目前 **仅** `workspace_root` 一个字段 + `enabled`。表单很简单，但要保留扩展位（未来阶段 2/3 规则若下放到 YAML，会加在这里）。

### 6.5 通用约束

- 所有 PATCH 操作成功后：toast + 失效相关 query。
- 修改 `workspace_root` 后用 banner 提示"已变更工作区，下一次任务启动将使用新路径；请确认 inbox 目录就绪"。
- 失败时把后端 `{code, message}` 直接展示（已有 `lib/errors.ts` 体系）。

---

## 7. 后端需要新增 / 调整的接口

> 这部分是本设计落地的硬依赖，建议按 A → B 的优先级分两批实现。

### 7.A 任务相关（驱动 §3、§4、§5，必须）

| ID | 端点 | 说明 |
|----|------|------|
| **A1** | `GET /api/tasks?task_type=&status=&page=&page_size=` | 现有 `list_runs` 改造：支持筛选 + 分页；返回项扩展 `task_type`、`trigger_type`、`dry_run`、`statistics_summary`（至少含 total / success / error / skipped 与 duration_ms）。响应包 `total`、`page`、`page_size`。 |
| **A2** | `GET /api/tasks/{run_id}` | 现有端点扩展：返回完整 `FileTaskRunStatistics`（含 Raw `phase*` 全字段）、`task_type`、`trigger_type`、`dry_run`、派生 `duration_ms`。当前只暴露 `total_items`。 |
| **A3** | `GET /api/tasks/{run_id}/results?decision_type=&success=&q=&page=&page_size=` | 新增：分页查询 `file_results` 表，列字段对齐 `FileItemData`。仓储层在 [`file_result_repository.py`](../src/j_file_kit/infrastructure/persistence/sqlite/file_task/file_result_repository.py) 已有写入路径，需要补 `list_results` 与 `count_results` 方法 + 索引（`run_id`、`decision_type`、`success`）。 |
| **A4** | `DELETE /api/tasks/{run_id}` | 新增：仅允许终态删除；级联删 `file_results` 行 + 日志文件。前端列表/详情的"删除"按钮依赖。 |
| **A5** | `GET /api/tasks/{run_id}/logs?offset=&limit=` | 新增：按行分页读取 `{base_dir}/logs/{run_name}_{run_id}.jsonl`。返回 `{total_lines, offset, limit, lines: [{ ts, level, msg, fields }]}`。v2 升级 SSE。 |
| **A6** | `GET /api/tasks/active` | 新增轻量端点：返回 `null` 或当前活跃 run 简要信息。供 `GlobalRunBanner` 高频轮询，避免调 `list_runs` 拉全表。可由 `FileTaskRunRepository.get_running_run()` 直接复用。 |

### 7.B 系统/元数据（驱动 §3.5、§6.2、§6.5）

| ID | 端点 | 说明 |
|----|------|------|
| **B1** | `GET /api/system/info` | 新增：`{ app_version, env, base_dir, media_root, jav_media_root, raw_media_root, media_mounted }`。供 Dashboard 页脚与配置页路径选择器消费。 |
| **B2** | `GET /api/system/file-type-defaults` | 可选（v2）：把 `organizer_defaults.py` 中的扩展名 / 关键字集合暴露给前端只读展示。v1 可在前端硬编码同一份镜像。 |

### 7.C 现有接口微调（不破坏兼容也可单独做）

- `POST /api/tasks/{task_type}/start` 的响应增加 `dry_run` 字段回显，便于详情页头部一眼可辨。
- `GET /api/file-task/config/...` 的响应增加 `defaults` 字段（即"当前 YAML vs 代码默认"对比），帮助配置页区分用户改过 vs 默认。该项也可推迟到 v2。

---

## 8. 数据获取与轮询策略

| Hook | 端点 | 轮询条件 | 备注 |
|------|------|---------|------|
| `useActiveTaskRun()` | `GET /api/tasks/active`（A6） | **常驻 3s 轮询** | 全局 banner、新建任务按钮禁用态 |
| `useTaskRunList(filter, page)` | `GET /api/tasks`（A1） | 仅在列表页挂载时；存在 active run 时缩短到 5s | 服务端分页 |
| `useTaskRunDetail(runId)` | `GET /api/tasks/{run_id}`（A2） | active 时 2s；终态停止（参考现有 `useTaskRunStatus`） | |
| `useTaskRunResults(runId, filter, page)` | A3 | active 时 5s；终态停止 | 详情 Tab B |
| `useTaskRunLogs(runId, offset, limit)` | A5 | active 时 3s 拉增量；终态停止 | v1 是分页 |
| `useTaskConfig(taskType)` | 现有 | 不轮询 | |
| `useStartTask` / `useCancelTaskRun` / `useUpdateTaskConfig` | 现有 + A4 | Mutation | 成功后 invalidate 相关 key |
| `useMediaDirectories(path)` | 现有 | 不轮询；单层懒加载，子层按需展开 | |
| `useSystemInfo()` | B1 | 不轮询；`staleTime: Infinity` | 只在版本变化时手动刷新 |

`QueryClient` 的全局 `staleTime: 30_000` 保留，单 hook 可覆盖。

---

## 9. 共享组件清单（建议放 `components/`）

| 组件 | 用途 |
|------|------|
| `layout/AppShell` | TopNav + GlobalRunBanner + Outlet |
| `layout/GlobalRunBanner` | 全局活跃 run 状态条 |
| `task/StatusBadge` | 5 种状态的统一徽标（颜色映射固定） |
| `task/TaskTypeBadge` | jav / raw 两色徽标 |
| `task/DryRunBadge` | 醒目橙色徽标 |
| `task/RunRowActions` | 取消 / 删除 / 详情 三个按钮（按状态显隐） |
| `task/StatsSummaryGrid` | 通用 5 项统计卡片 |
| `task/RawPhaseStats` | Raw phase 卡片组（按阶段折叠） |
| `task/StartTaskCard` | Dashboard 上单个 task_type 的启动卡 |
| `media/MediaPickerDialog` | 复用 `/api/media/directories` 的目录选择树 |
| `form/PathInput` | 路径输入 + 选择按钮 |
| `form/StemTagsInput` | `exact_stems` 多值标签输入 |
| `common/EmptyState` / `common/ErrorState` / `common/LoadingState` | 三态 |

原子组件优先 `bunx shadcn add`，不手写。

---

## 10. 落地里程碑

当前进度：

- **M1：骨架已完成**。完成记录见 [`FE-M1.md`](./FE-M1.md)。
- **M2：Dashboard MVP 已完成**。完成记录见 [`FE-M2.md`](./FE-M2.md)。
- **M3：任务详情 MVP 已完成**。完成记录见 [`FE-M3.md`](./FE-M3.md)。
- **M4：任务列表 MVP 已完成**。完成记录见 [`FE-M4.md`](./FE-M4.md)。
- **M5：配置中心已完成**。完成记录见 [`FE-M5.md`](./FE-M5.md)。
- **M6：文件结果 Tab 已完成**。完成记录见 [`FE-M6.md`](./FE-M6.md)。
- **M7：日志 Tab + 删除已完成**。完成记录见 [`FE-M7.md`](./FE-M7.md)。
- **下一阶段准备进行 M8：全局配置只读 + 系统信息**。重点是配置中心全局配置 Tab 与 Dashboard 系统信息页脚。

| 阶段 | 状态 | 范围 | 依赖后端 |
|------|------|------|----------|
| **M1：骨架** | 已完成 | AppShell + 路由扩展（`/tasks`、`/tasks/:runId`）+ 现有页面占位重构 | 无 |
| **M2：Dashboard MVP** | 已完成 | NewTaskPanel（双卡）+ RecentRunsList（用现有 list 接口，简报字段先空） + GlobalRunBanner | A6 已完成；A1 简报字段仍待 M4 |
| **M3：任务详情 MVP** | 已完成 | 概览 Tab（含 Raw phase 卡片） + 取消 / 重跑 | A2 已完成 |
| **M4：任务列表 MVP** | 已完成 | 筛选 + 分页 + 行操作（不含删除） | A1 已完成 |
| **M5：配置中心** | 已完成 | JAV / Raw 表单 + MediaPickerDialog | B1 已完成 |
| **M6：文件结果 Tab** | 已完成 | 详情页 Tab B | A3 已完成 |
| **M7：日志 Tab + 删除** | 已完成 | 详情页 Tab C + 列表/详情删除按钮 | A5、A4 已完成 |
| **M8：全局配置只读 + 系统信息** | 下一步 | 配置 Tab 1 + Dashboard 页脚 | B1、B2 |

每个里程碑独立可发布；M2 / M3 完成后已经显著优于"什么都没有"的现状。

---

## 11. 常见陷阱（给前端 AI Agent）

- **不要在前端自行 `fetch`**：所有请求必须经 `apiClient`（[`api/client.ts`](../frontend/src/api/client.ts)），统一错误体 `{ code, message }`。
- **不要绕开 hook 直接调 React Query**：每个端点都先在 `api/*.ts` 加一个 hook，页面只消费 hook，便于改轮询策略与做 mock。
- **task_type 不要散落**：始终用 `TASK_TYPES.JAV` / `TASK_TYPES.RAW`（[`api/tasks.ts`](../frontend/src/api/tasks.ts)），不要在组件里写裸字符串。
- **互斥状态以 `useActiveTaskRun()` 为准**：不要用 `useTaskRunList` 的第一行去推断"是否有任务在跑"，那会浪费带宽并产生竞态。
- **dry_run 默认 ON**：UI 默认安全；用户必须显式关掉 toggle 才会真删/真移。
- **路径输入校验**：`workspace_root` 前端先用 `system/info` 拿到 root 做前缀校验，再发请求；只让后端做兜底，不让后端做主校验入口。
- **轮询要在终态停止**：参考 `useTaskRunStatus` 中 `refetchInterval` 的回调写法，避免 completed 后继续 poll 制造无意义请求。
