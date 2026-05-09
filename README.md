# j-file-kit

基于 Python + FastAPI 的媒体文件自动整理工具，**以 Docker 容器方式运行，面向 Unraid 设计**。核心功能之一是在配置的 **`workspace_root`**（默认 **`/media/jav_workspace`**）下，从派生的 **`inbox`** 扫描视频并按番号识别后归入 **`sorted`、`unsorted`、`archive`、`misc`**（子目录名由代码约定，不经 YAML 逐项配置）；另提供 **`raw_workspace`** 下的 **Raw 收件箱整理**（inbox 第一层：文件归集 `files_misc`、目录迁至 `folders_to_delete`/清洗/`files_misc` 分流规划等；详见 [docs/RAW_FILE_PROCESSING_PIPELINE.md](docs/RAW_FILE_PROCESSING_PIPELINE.md)）。通过 HTTP API 更新 **`workspace_root`** 时会自动创建 **`workspace_root/inbox`**；任务通过 HTTP API 触发与查询状态。

架构设计见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。

---

## 本地开发

> 本项目为 Docker 设计，`/data`、`/media` 均为容器内路径，**建议通过 Docker 运行**。

```bash
brew install uv         # 安装 uv（macOS）
brew install just       # 安装 just（macOS）
just pre-install        # 安装 pre-commit 钩子
just deps-sync          # 创建 .venv 并安装全部依赖
```

所有常用开发命令见 [justfile](justfile)，核心命令如下：

| 命令 | 说明 |
|---|---|
| `just test` | 运行全部测试 |
| `just test-unit` | 仅运行单元测试（快速） |
| `just test-cov` | 测试 + 覆盖率报告 |
| `just docker-up` | 构建镜像并后台启动容器 |
| `just docker-logs` | 实时跟踪容器日志 |
| `just task-run` | 触发整理任务（加 `DRY_RUN=true` 可预览） |
| `just task-list` | 列出最近 10 个任务状态 |
| `just release 1.2.3` | 打 tag 并推送，触发 CI 构建镜像 |

---

## 本地 Docker 测试

```bash
# 复制并编辑 .env，填写宿主机媒体根目录
cp .env.example .env

# 构建镜像并后台启动
just docker-up
```

媒体目录：`jav_workspace` / `raw_workspace` 默认对应 **`/media/jav_workspace`**、**`/media/raw_workspace`**。**PATCH 保存任务配置**时会创建对应 **`workspace_root`** 与 **`inbox`**。其余业务子目录（如 `sorted`、`folders_pic`、`files_misc` 等）名由 [`application/config_common.py`](src/j_file_kit/app/file_task/application/config_common.py) 约定，任务执行时按需创建（参见各流水线文档）。

| 宿主机 | 容器内 | 用途 |
|---|---|---|
| `$MEDIA_ROOT` | `/media` | 媒体根目录 |
| `$MEDIA_ROOT/jav_workspace` | `/media/jav_workspace` | JAV **`workspace_root`**（默认）；其下 **`inbox`** 在保存配置时创建 |
| `$MEDIA_ROOT/jav_workspace/inbox` | `/media/jav_workspace/inbox` | JAV 待处理收件箱 |
| `$MEDIA_ROOT/jav_workspace/sorted` | `/media/jav_workspace/sorted` | JAV 有番号归档（按需创建） |
| `$MEDIA_ROOT/jav_workspace/unsorted` | `/media/jav_workspace/unsorted` | JAV 无番号（按需创建） |
| `$MEDIA_ROOT/jav_workspace/archive` | `/media/jav_workspace/archive` | JAV 压缩包（按需创建） |
| `$MEDIA_ROOT/jav_workspace/misc` | `/media/jav_workspace/misc` | JAV 杂项（按需创建） |
| `$MEDIA_ROOT/raw_workspace` | `/media/raw_workspace` | Raw **`workspace_root`**（默认）；子目录同上按需创建 |

---

## 部署到 Unraid

**首次部署：** 进入 `Docker` 页面，点击 `Add Container`，手动填写以下参数：

| 字段 | 值 |
|---|---|
| Name | `j-file-kit` |
| Repository | `ghcr.io/watchzerg/j-file-kit:latest` |
| Port（容器→宿主） | `8000` → `8000`，`1307` → `1307` |
| 路径 1（容器→宿主） | `/data` → `/mnt/user/appdata/j-file-kit` |
| 路径 2（容器→宿主） | `/media` → `/mnt/user/Porn-Japan/media` |
| 环境变量 `PUID` | 你的 uid（执行 `id <username>` 查询） |
| 环境变量 `PGID` | 你的 gid |

> 在 unraid 里执行 `id [username]`来获取 PUID 与 PGID。

确认后容器启动，访问 `http://<unraid-ip>:1307/docs`。

**后续部署：** 首次创建即相当于保存了模板，之后进入 `Add Container`，在顶部 Template 下拉菜单中选择 `j-file-kit` 即可直接使用。
