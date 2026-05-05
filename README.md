# j-file-kit

基于 Python + FastAPI 的媒体文件自动整理工具，**以 Docker 容器方式运行，面向 Unraid 设计**。核心功能之一是将 **`jav_workspace/inbox`（容器内默认路径为 `/media/jav_workspace/inbox`）** 中的视频文件按番号识别后自动分类归档到 `sorted`、`unsorted`、`archive` 等目录；另提供 **`raw_workspace`** 下的 **Raw 收件箱整理**任务骨架（路径与 API 见 [docs/RAW_FILE_PROCESSING_PIPELINE.md](docs/RAW_FILE_PROCESSING_PIPELINE.md)）。任务通过 HTTP API 触发与查询状态。

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

媒体目录结构（**`jav_workspace/inbox` 需提前存在**；**`raw_workspace` 下各业务子目录**可按默认配置自行创建，参见 `task_config.yaml` / [RAW_FILE_PROCESSING_PIPELINE.md](docs/RAW_FILE_PROCESSING_PIPELINE.md)。JAV 其余子目录多由任务执行时自动创建）：

| 宿主机 | 容器内 | 用途 |
|---|---|---|
| `$MEDIA_ROOT` | `/media` | 媒体根目录 |
| `$MEDIA_ROOT/jav_workspace/inbox` | `/media/jav_workspace/inbox` | JAV 待处理（需提前存在） |
| `$MEDIA_ROOT/jav_workspace/sorted` | `/media/jav_workspace/sorted` | JAV 有番号归档 |
| `$MEDIA_ROOT/jav_workspace/unsorted` | `/media/jav_workspace/unsorted` | JAV 无番号 |
| `$MEDIA_ROOT/jav_workspace/archive` | `/media/jav_workspace/archive` | JAV 压缩包 |
| `$MEDIA_ROOT/jav_workspace/misc` | `/media/jav_workspace/misc` | JAV 杂项 |
| `$MEDIA_ROOT/raw_workspace/...` | `/media/raw_workspace/...` | Raw 整理（默认见配置，如 `inbox`、`folders_*`、`files_*`） |

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
