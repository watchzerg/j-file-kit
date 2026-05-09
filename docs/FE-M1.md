# FE-M1：骨架（AppShell + 路由扩展 + 页面存根重构）

本文档是 [`FRONTEND_DESIGN.md` §10 里程碑 M1](./FRONTEND_DESIGN.md) 的详细落地计划，面向 **开发者与 AI Agent**。

- **M1 范围**：AppShell + 路由扩展（`/tasks`、`/tasks/:runId`）+ 现有 4 页占位重构，**无任何后端依赖**。
- **本文不重复**前端通用设计原则，请先阅读 [`FRONTEND_DESIGN.md`](./FRONTEND_DESIGN.md)。

---

## 1. 目标与交付物

M1 完成后，整个应用具备：

| 交付物 | 说明 |
|--------|------|
| `AppShell` 布局壳 | 所有页面共用同一 TopNav + GlobalRunBanner 占位 + Outlet |
| 完整路由表 | 5 条路由全部注册，导航链接可跳转，浏览器前进/后退正常 |
| 5 个页面存根 | Dashboard、TasksList、TaskDetail、Config、Media 各自独立 |
| 导航活跃态 | 当前路由对应的导航链接高亮 |

M1 **不包含**：

- 任何真实数据展示（无 API 调用，无 TanStack Query hook）
- GlobalRunBanner 的数据逻辑（M2 实现）
- 各页面内部的业务模块（M2~M8 分别补齐）

---

## 2. 文件变更清单

### 2.1 新建文件

| 文件路径 | 说明 |
|----------|------|
| `frontend/src/components/layout/AppShell.tsx` | 全局布局壳：TopNav + GlobalRunBanner + Outlet |
| `frontend/src/components/layout/TopNav.tsx` | 顶部导航栏 |
| `frontend/src/components/layout/GlobalRunBanner.tsx` | 全局活跃任务状态条（M1 为空占位） |
| `frontend/src/pages/DashboardPage.tsx` | Dashboard 存根，路由 `/` |
| `frontend/src/pages/TasksListPage.tsx` | 任务列表存根，路由 `/tasks` |
| `frontend/src/pages/TaskDetailPage.tsx` | 任务详情存根，路由 `/tasks/:runId` |

### 2.2 修改文件

| 文件路径 | 变更内容 |
|----------|----------|
| `frontend/src/App.tsx` | 引入 AppShell 布局路由；扩展路由表（新增 `/tasks`、`/tasks/:runId`）；`/` 改指向 DashboardPage |
| `frontend/src/pages/ConfigPage.tsx` | 移除页面内的冗余外壳标签（由 AppShell 统一提供），保留内容区 |
| `frontend/src/pages/MediaPage.tsx` | 同上 |

### 2.3 删除文件

| 文件路径 | 原因 |
|----------|------|
| `frontend/src/pages/TasksPage.tsx` | 职责已拆分为 `DashboardPage`（`/`）与 `TasksListPage`（`/tasks`），原文件废弃 |

---

## 3. AppShell 设计

### 3.1 整体结构

```
┌─────────────────────────────────────────────┐
│  TopNav（固定在顶部）                         │
│  左：Logo + 应用名称                          │
│  右：导航链接 × 4                             │
├─────────────────────────────────────────────┤
│  GlobalRunBanner（条件显示，M1 为空）          │
├─────────────────────────────────────────────┤
│                                             │
│  ContentArea（<Outlet />）                   │
│  各页面自行管理内边距与容器宽度               │
│                                             │
└─────────────────────────────────────────────┘
```

### 3.2 `AppShell.tsx` 实现规范

- 使用 `react-router-dom` 的 `<Outlet />` 作为内容区出口。
- 外层 `<div>` 采用 `flex flex-col min-h-screen` 撑满视口高度。
- TopNav 使用 `sticky top-0 z-40` 实现吸顶效果。
- ContentArea 使用 `flex-1` 确保可伸展。

```tsx
// components/layout/AppShell.tsx（示意，非最终实现）
export default function AppShell() {
  return (
    <div className="flex flex-col min-h-screen bg-background">
      <TopNav />
      <GlobalRunBanner />
      <main className="flex-1">
        <Outlet />
      </main>
    </div>
  );
}
```

### 3.3 `TopNav.tsx` 实现规范

#### 布局

- 整体：`sticky top-0 z-40 w-full border-b bg-background/95 backdrop-blur`
- 内容区：`container mx-auto flex h-14 items-center justify-between px-4`
- 左侧：Logo 图标（可用 `lucide-react` 的 `Layers` 图标）+ 应用名称 `j-file-kit`，样式 `font-semibold text-lg`
- 右侧：导航链接组

#### 导航链接

使用 `react-router-dom` 的 `<NavLink>` 实现活跃态高亮：

| 链接文案 | 目标路由 |
|----------|----------|
| Dashboard | `/` |
| 任务列表 | `/tasks` |
| 配置 | `/config` |
| 媒体 | `/media` |

`NavLink` 的 `className` 回调判断 `isActive`：
- 活跃态：`text-foreground font-medium`
- 非活跃态：`text-muted-foreground hover:text-foreground`
- 通用：`text-sm transition-colors`

`/` 路由需传 `end` 属性避免所有路由都匹配 Dashboard。

### 3.4 `GlobalRunBanner.tsx` 实现规范（M1 占位）

M1 阶段该组件**不渲染任何内容**，仅作为占位，确保 AppShell 组合结构完整。M2 实现数据逻辑时直接在此文件填充内容，不需改动 AppShell。

```tsx
// components/layout/GlobalRunBanner.tsx（M1 占位）
export default function GlobalRunBanner() {
  // M2 在此处接入 useActiveTaskRun() 并渲染状态条
  return null;
}
```

---

## 4. 路由表调整

### 4.1 调整后的 `App.tsx` 路由结构

使用 React Router v7 的 **布局路由**（Layout Route）模式：`AppShell` 作为父路由渲染 `<Outlet />`，所有页面作为子路由。

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

### 4.2 路由表完整视图（M1 后）

| 路径 | 页面组件 | M1 状态 |
|------|----------|---------|
| `/` | `DashboardPage` | 存根 |
| `/tasks` | `TasksListPage` | 存根 |
| `/tasks/:runId` | `TaskDetailPage` | 存根 |
| `/config` | `ConfigPage` | 已有，接入 AppShell |
| `/media` | `MediaPage` | 已有，接入 AppShell |

---

## 5. 各页面存根设计

M1 阶段所有页面只提供**内容占位**，不调用任何 API。以下规范为每个页面明确 M1 应交付的最小内容，为后续里程碑留下清晰的扩展点。

### 5.1 `DashboardPage`（路由 `/`）

**文件**：`frontend/src/pages/DashboardPage.tsx`

M1 呈现内容：

```
页面标题：Dashboard

[区块占位] 启动任务（M2 实现）
[区块占位] 快捷链接（M2 实现）
[区块占位] 最近任务（M2 实现）
[区块占位] 系统信息（M8 实现）
```

实现要点：
- 各区块用带有虚线边框与占位文案的 `<div>` 标记，帮助开发者定位扩展点。
- 容器：`container mx-auto px-4 py-6`。
- 区块间距：`space-y-6`。

### 5.2 `TasksListPage`（路由 `/tasks`）

**文件**：`frontend/src/pages/TasksListPage.tsx`

M1 呈现内容：

```
页面标题：任务列表

[区块占位] 筛选栏（M4 实现）
[区块占位] 任务表格（M4 实现）
[区块占位] 分页（M4 实现）
```

### 5.3 `TaskDetailPage`（路由 `/tasks/:runId`）

**文件**：`frontend/src/pages/TaskDetailPage.tsx`

M1 呈现内容：

```
页面标题：任务详情 #{runId}（从 useParams 读取 runId 并展示）

Tab 导航占位：
  [Tab] 概览（默认，M3 实现）
  [Tab] 文件结果（M6 实现）
  [Tab] 日志（M7 实现）

当前 Tab 内容：[区块占位]
```

实现要点：
- 使用 `react-router-dom` 的 `useParams()` 获取 `runId` 并在标题中展示。
- Tab 导航可用简单的按钮组模拟，点击切换本地状态（`useState`），M3 时再接入真实数据。
- M1 所有 Tab 内容都是占位 `<div>`。

### 5.4 `ConfigPage`（路由 `/config`）

**文件**：`frontend/src/pages/ConfigPage.tsx`（修改）

当前实现有 `<main className="container mx-auto p-6">` 外壳，AppShell 接入后 `<main>` 语义由 AppShell 的 `<main>` 元素承担。

调整内容：
- 将最外层 `<main>` 改为 `<div>`，保留 `className="container mx-auto p-6"`。
- 内部标题与占位内容不变（具体配置表单在 M5 实现）。

### 5.5 `MediaPage`（路由 `/media`）

**文件**：`frontend/src/pages/MediaPage.tsx`（修改）

与 ConfigPage 同理：最外层 `<main>` 改为 `<div>`，内容不变。

---

## 6. 实施步骤

按依赖顺序，建议分以下步骤提交（可合并为 1~2 个 PR）：

### Step 1：创建 layout 组件

1. 创建 `frontend/src/components/layout/GlobalRunBanner.tsx`（空组件，`return null`）。
2. 创建 `frontend/src/components/layout/TopNav.tsx`（含 Logo + 4 个 NavLink）。
3. 创建 `frontend/src/components/layout/AppShell.tsx`（组合 TopNav + GlobalRunBanner + Outlet）。

### Step 2：创建新页面存根

4. 创建 `frontend/src/pages/DashboardPage.tsx`。
5. 创建 `frontend/src/pages/TasksListPage.tsx`。
6. 创建 `frontend/src/pages/TaskDetailPage.tsx`（含 `useParams` + Tab 占位）。

### Step 3：调整现有页面与路由

7. 修改 `frontend/src/pages/ConfigPage.tsx`：`<main>` → `<div>`。
8. 修改 `frontend/src/pages/MediaPage.tsx`：`<main>` → `<div>`。
9. 修改 `frontend/src/App.tsx`：引入所有新组件，改为布局路由结构，移除旧 `TasksPage` 引用。
10. 删除 `frontend/src/pages/TasksPage.tsx`。

---

## 7. 样式约定

- 遵循现有 Tailwind CSS v4 配置，不引入新 CSS 文件。
- 颜色用语义 token（`bg-background`、`text-foreground`、`text-muted-foreground`、`border`），不硬编码颜色值。
- 若需要使用 shadcn/ui 组件（如 `<Separator />`），通过 `bunx shadcn add <组件名>` 安装，不手写复刻。
- M1 只依赖现有的 `lucide-react` 和 `react-router-dom`，不引入新运行时依赖。

---

## 8. 验收标准

以下条件**全部满足**才视为 M1 完成：

| # | 验收项 |
|---|--------|
| 1 | `bun run build`（`tsc --noEmit && vite build`）无编译错误 |
| 2 | `bun run check`（Biome lint）无错误 |
| 3 | 访问 `/`、`/tasks`、`/tasks/123`、`/config`、`/media` 均可正常渲染，不报白屏 |
| 4 | TopNav 导航链接点击后路由跳转正确，浏览器地址栏更新 |
| 5 | TopNav 当前激活路由对应链接有高亮样式，其余链接无高亮 |
| 6 | `/` 路由展示 DashboardPage（标题 "Dashboard"），**不再是**原 TasksPage 的"任务管理" |
| 7 | `/tasks/:runId` 路由中 `runId` 正确显示在页面标题（如 `/tasks/123` → "任务详情 #123"） |
| 8 | AppShell 的 `<main>` 元素在页面中只出现一次（语义正确） |
| 9 | GlobalRunBanner 不渲染任何可见元素（M1 期间 `return null`） |
| 10 | 旧文件 `pages/TasksPage.tsx` 已删除，无孤立引用 |

---

## 9. 下一里程碑

**M2（Dashboard MVP）**：

- 实现 `GlobalRunBanner` 数据逻辑（依赖后端 **A6** `GET /api/tasks/active`）。
- 实现 `NewTaskPanel`（双任务启动卡）与 `RecentRunsList`。

