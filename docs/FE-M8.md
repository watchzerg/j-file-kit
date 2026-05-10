# FE-M8：全局配置只读 + 系统信息已完成

本文档记录 [`FRONTEND_DESIGN.md` §10](./FRONTEND_DESIGN.md) 中 **M8：全局配置只读 + 系统信息** 的完成状态，供后续开发者与 AI Agent 接手后续优化时参考。

- **状态**：已完成
- **范围**：`GET /api/system/file-type-defaults`、配置中心「全局配置」只读展示、Dashboard 系统信息页脚、自动化测试
- **后端依赖**：B1 已存在；B2 已实现
- **下一阶段**：后续可做系统默认字典搜索/展开、日志 SSE、结果导出等增量优化

---

## 1. 已完成内容

M8 已把配置中心第一个 Tab 从 M5 占位推进到真实只读系统配置，并把 Dashboard 底部的 M8 占位替换为运行时系统信息：

| 交付物 | 完成情况 |
|--------|----------|
| 系统信息接口 | 复用已有 `GET /api/system/info`，展示版本、环境、数据目录、媒体根、JAV/Raw 根与挂载状态 |
| 默认字典接口 | 新增 `GET /api/system/file-type-defaults`，从 `organizer_defaults.py` 映射后端整理管线常量 |
| 前端 API | 增加 typed defaults response 与 `useSystemFileTypeDefaults()` |
| 配置中心全局 Tab | 展示系统信息 + 文件扩展名、Raw 关键字、JAV 命名规则等只读默认值摘要 |
| Dashboard 页脚 | 展示 compact 系统信息面板，替换 M8 占位块 |
| 测试覆盖 | 后端 system API、前端 Dashboard 页脚与全局配置 Tab 行为均已覆盖 |

M8 不包含默认字典编辑、全文搜索、复杂展开/折叠、日志 SSE 或结果导出。

---

## 2. 接口契约

### 2.1 `GET /api/system/info`

B1 已在 M5 前后完成，M8 继续使用该接口：

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

### 2.2 `GET /api/system/file-type-defaults`

响应包：

```json
{
  "extensions": {
    "video": [".mp4"],
    "image": [".jpg"],
    "subtitle": [".srt"],
    "archive": [".rar"],
    "music": [".mp3"],
    "misc_delete": [".nfo"]
  },
  "raw": {
    "junk_keywords": ["FC2-PPV"],
    "video_bucket_movie_keywords": ["AMZN"],
    "video_bucket_us_vr_keywords": ["LethalHardcoreVR"],
    "video_bucket_us_keywords": ["Brazzers"],
    "camelcase_no_split_words": ["VR"],
    "cleanup_junk_max_bytes": 104857600
  },
  "jav": {
    "vr_serial_prefixes": ["3DSVR"],
    "filename_strip_substrings": ["BBS-2048"]
  }
}
```

扩展名与无语义顺序的集合会稳定排序；Raw/JAV 关键字 tuple 保留后端常量定义顺序。

---

## 3. 当前文件结构

### 新增文件

| 文件 | 说明 |
|------|------|
| `docs/FE-M8.md` | M8 完成交接记录 |
| `frontend/src/components/system/SystemInfoPanel.tsx` | 系统信息只读面板，支持 full / compact |
| `frontend/src/components/system/SystemDefaultsPanel.tsx` | 后端默认字典只读摘要面板 |

### 修改文件

| 文件 | 说明 |
|------|------|
| `src/j_file_kit/app/system/schemas.py` | 增加系统默认字典响应模型 |
| `src/j_file_kit/app/system/api.py` | 新增 B2 默认字典接口 |
| `tests/api/test_system_api.py` | 覆盖 B2 接口 |
| `frontend/src/api/types.ts` | 增加 system defaults 类型 |
| `frontend/src/api/system.ts` | 增加 `useSystemFileTypeDefaults()` |
| `frontend/src/pages/ConfigPage.tsx` | 全局配置 Tab 接入系统信息与默认字典 |
| `frontend/src/pages/DashboardPage.tsx` | Dashboard 页脚接入系统信息 |
| `frontend/src/test/server.ts` | 增加 B2 MSW mock |
| `frontend/src/App.test.tsx` | 覆盖 Dashboard 页脚与全局配置 Tab |
| `docs/FRONTEND_DESIGN.md` | 更新 M8 进度 |

---

## 4. 踩坑记录

- **B1 已经存在**：M8 不需要重做 `/api/system/info`，只需要复用并补足前端展示字段。
- **默认字典不要前端复制**：B2 直接从 `organizer_defaults.py` 映射，避免前端维护第二份规则。
- **集合要稳定序列化**：`frozenset` 需要转为排序后的 list，保证测试、快照和 UI 顺序稳定。
- **关键字顺序有业务含义**：Raw 视频桶关键字按后端 tuple 顺序返回，不对其做字母排序。
- **长列表不要铺满页面**：前端只展示前 8 项和总数摘要，避免全局 Tab 被大字典淹没。

---

## 5. 测试与验证

已执行并通过：

```bash
uv run pytest tests/api/test_system_api.py
uv run ruff check src/j_file_kit/app/system tests/api/test_system_api.py
just fe-check
just fe-test
just fe-build
```
