# FE-M1：骨架已完成（AppShell + 路由扩展 + 页面存根）

本文档记录 [`FRONTEND_DESIGN.md` §10](./FRONTEND_DESIGN.md) 中 **M1：骨架** 的完成状态，供后续开发者与 AI Agent 接手 M2+ 时参考。

- **状态**：已完成
- **范围**：AppShell、TopNav、GlobalRunBanner 占位、5 条路由、5 个页面存根、自动化测试
- **后端依赖**：无
- **下一阶段**：M2（Dashboard MVP）

---

## 1. 已完成内容

M1 已把前端从单页占位扩展为可继续迭代的应用骨架：

| 交付物 | 完成情况 |
|--------|----------|
| 全局布局壳 | 已新增 `AppShell`，所有页面共享 TopNav、GlobalRunBanner 占位和唯一 `<main>` 内容出口 |
| 顶部导航 | 已新增 `TopNav`，包含 Dashboard、任务列表、配置、媒体 4 个导航入口 |
| 导航活跃态 | 已使用 React Router `NavLink` 实现；`/` 链接使用 `end`，避免在所有路由下误高亮 |
| 路由扩展 | 已注册 `/`、`/tasks`、`/tasks/:runId`、`/config`、`/media` |
| 页面存根 | 已拆出 Dashboard、任务列表、任务详情、配置、媒体 5 个页面 |
| 旧任务页拆分 | 已删除 `frontend/src/pages/TasksPage.tsx`，`/` 不再显示旧的“任务管理”页 |
| 测试覆盖 | 已新增 `frontend/src/App.test.tsx`，覆盖 M1 关键行为 |

M1 不包含真实业务数据、API 调用、TanStack Query hook、任务启动逻辑或全局任务条数据逻辑。这些从 M2 开始逐步接入。

---

## 2. 当前文件结构

### 新增文件

| 文件 | 说明 |
|------|------|
| `frontend/src/components/layout/AppShell.tsx` | 全局布局壳，组合 `TopNav`、`GlobalRunBanner` 与 `<Outlet />` |
| `frontend/src/components/layout/TopNav.tsx` | 顶部导航栏，负责应用名称、Logo 与路由导航 |
| `frontend/src/components/layout/GlobalRunBanner.tsx` | 全局活跃任务状态条占位；M1 返回 `null` |
| `frontend/src/pages/DashboardPage.tsx` | Dashboard 存根，对应 `/` |
| `frontend/src/pages/TasksListPage.tsx` | 任务列表存根，对应 `/tasks` |
| `frontend/src/pages/TaskDetailPage.tsx` | 任务详情存根，对应 `/tasks/:runId` |
| `frontend/src/App.test.tsx` | M1 路由、导航和页面语义测试 |

### 修改文件

| 文件 | 说明 |
|------|------|
| `frontend/src/App.tsx` | 改为布局路由结构，挂载 5 条页面路由 |
| `frontend/src/pages/ConfigPage.tsx` | 最外层从 `<main>` 改为 `<div>`，避免与 AppShell 重复 |
| `frontend/src/pages/MediaPage.tsx` | 最外层从 `<main>` 改为 `<div>`，避免与 AppShell 重复 |

### 删除文件

| 文件 | 说明 |
|------|------|
| `frontend/src/pages/TasksPage.tsx` | 原 `/` 旧占位页，职责已拆到 `DashboardPage` 与 `TasksListPage` |

---

## 3. 路由现状

当前 `App.tsx` 使用 React Router v7 的布局路由模式：

```tsx
<Routes>
  <Route element={<AppShell />}>
    <Route path="/" element={<DashboardPage />} />
    <Route path="/tasks" element={<TasksListPage />} />
    <Route path="/tasks/:runId" element={<TaskDetailPage />} />
    <Route path="/config" element={<ConfigPage />} />
    <Route path="/media" element={<MediaPage />} />
  </Route>
</Routes>
```

| 路径 | 页面 | 当前内容 |
|------|------|----------|
| `/` | `DashboardPage` | 标题 `Dashboard`；启动任务、快捷链接、最近任务、系统信息 4 个占位区块 |
| `/tasks` | `TasksListPage` | 标题 `任务列表`；筛选栏、任务表格、分页 3 个占位区块 |
| `/tasks/:runId` | `TaskDetailPage` | 标题 `任务详情 #{runId}`；本地 Tab 占位：概览、文件结果、日志 |
| `/config` | `ConfigPage` | 标题 `任务配置` |
| `/media` | `MediaPage` | 标题 `媒体目录` |

---

## 4. AppShell 与导航约定

`AppShell` 是后续所有页面的共同外壳：

- 外层使用 `flex min-h-screen flex-col bg-background`。
- `TopNav` 固定在顶部：`sticky top-0 z-40 w-full border-b bg-background/95 backdrop-blur`。
- `GlobalRunBanner` 已放在 `TopNav` 下方，但 M1 期间不渲染任何元素。
- `<main className="flex-1">` 只在 `AppShell` 中出现一次，子页面不要再使用 `<main>` 作为最外层。
- 页面内容仍由各 page 自己控制容器宽度、padding 和区块间距。

`TopNav` 当前导航项：

| 文案 | 路由 |
|------|------|
| Dashboard | `/` |
| 任务列表 | `/tasks` |
| 配置 | `/config` |
| 媒体 | `/media` |

活跃态通过 `NavLink` 计算：

- 活跃：`font-medium text-foreground`
- 非活跃：`text-muted-foreground hover:text-foreground`
- 通用：`text-sm transition-colors`

---

## 5. 测试与验证

已新增 `frontend/src/App.test.tsx`，覆盖：

1. `/` 渲染 `Dashboard`，不再显示旧 `任务管理`。
2. `/tasks`、`/tasks/123`、`/config`、`/media` 均可渲染对应标题。
3. 每个页面下 DOM 中只存在一个 `<main>`。
4. TopNav 点击 `任务列表` 后浏览器路径更新为 `/tasks`。
5. TopNav 当前路由链接高亮，Dashboard 与任务列表活跃态不会互相污染。
6. `/tasks/:runId` 正确展示 `任务详情 #123`。
7. 任务详情页的 Tab 占位可在本地切换。

已执行并通过：

```bash
bun run check
bun run test
bun run build
```

其中 `bun run test` 当前结果为 1 个测试文件、4 个测试通过。

---

## 6. 给下一阶段 Agent 的交接说明

### 6.1 M2 应从哪里开始

下一阶段是 **M2：Dashboard MVP**。建议优先参考 [`FRONTEND_DESIGN.md`](./FRONTEND_DESIGN.md) 的这些章节：

- §3 Dashboard
- §7.A6 `GET /api/tasks/active`
- §8 数据获取与轮询策略
- §9 共享组件清单
- §10 落地里程碑

M2 的主要目标：

1. 实现 `GlobalRunBanner` 的真实数据逻辑。
2. 实现 Dashboard 上的 `NewTaskPanel`。
3. 实现 Dashboard 上的 `RecentRunsList`。

### 6.2 M2 预计要改的现有文件

| 文件 | M2 可能改动 |
|------|-------------|
| `frontend/src/components/layout/GlobalRunBanner.tsx` | 接入 `useActiveTaskRun()`，有活跃任务时渲染状态条 |
| `frontend/src/pages/DashboardPage.tsx` | 用真实 Dashboard 模块替换 M1 占位区块 |
| `frontend/src/api/tasks.ts` | 增加或调整 active run、recent runs、start task 相关 hook |
| `frontend/src/api/types.ts` | 补齐 M2 所需响应类型 |

M2 可能新增：

| 目录/文件 | 用途 |
|-----------|------|
| `frontend/src/components/task/StartTaskCard.tsx` | Dashboard 中单个任务类型的启动卡 |
| `frontend/src/components/task/RecentRunsList.tsx` | 最近任务列表 |
| `frontend/src/components/task/StatusBadge.tsx` | 任务状态徽标 |
| `frontend/src/components/task/DryRunBadge.tsx` | dry_run 徽标 |
| `frontend/src/components/common/*State.tsx` | Loading / Error / Empty 等通用三态（如确有复用需求再建） |

### 6.3 保持不变的 M1 约束

- 不要恢复 `TasksPage.tsx`。
- 不要让 page 组件重新包 `<main>`。
- 不要绕过 `AppShell` 注册独立页面壳。
- 不要在组件里直接 `fetch`；新增请求应通过 `src/api/` 中的 typed hook 暴露。
- Dashboard 路由继续是 `/`，任务列表路由继续是 `/tasks`。
- `GlobalRunBanner` 的位置已经固定在 `TopNav` 下方，M2 只需要填充内容，不需要改 AppShell 结构。

---

## 7. 后续里程碑提示

M1 已经为后续里程碑留下了占位：

| 占位位置 | 后续阶段 |
|----------|----------|
| Dashboard：启动任务 | M2 |
| Dashboard：快捷链接 | M2 |
| Dashboard：最近任务 | M2 |
| Dashboard：系统信息 | M8 |
| 任务列表：筛选栏 / 表格 / 分页 | M4 |
| 任务详情：概览 Tab | M3 |
| 任务详情：文件结果 Tab | M6 |
| 任务详情：日志 Tab | M7 |
| 配置页真实表单 | M5 |

下一步建议从 M2 开始；若后端 **A6 `GET /api/tasks/active`** 尚未就绪，需要先补后端或在 M2 中明确用临时策略降级。
