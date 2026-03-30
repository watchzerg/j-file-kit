# j-file-kit

基于 Python + FastAPI 的媒体文件自动整理工具，**以 Docker 容器方式运行，面向 Unraid 设计**。核心功能是将 `inbox` 目录中的 JAV 视频文件，按番号识别后自动分类归档到对应目录（`sorted/`、`unsorted/`、`archive/` 等），通过 HTTP API 触发和查询任务状态。

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

媒体目录结构（`inbox` 需提前存在，其余子目录由任务执行时自动创建）：

| 宿主机 | 容器内 | 用途 |
|---|---|---|
| `$MEDIA_ROOT` | `/media` | 媒体根目录 |
| `$MEDIA_ROOT/inbox` | `/media/inbox` | 待处理（需提前存在） |
| `$MEDIA_ROOT/sorted` | `/media/sorted` | 有番号归档 |
| `$MEDIA_ROOT/unsorted` | `/media/unsorted` | 无番号 |
| `$MEDIA_ROOT/archive` | `/media/archive` | 压缩包 |
| `$MEDIA_ROOT/misc` | `/media/misc` | 杂项 |

---

## 部署到 Unraid

使用 [unraid/j-file-kit.xml](unraid/j-file-kit.xml) 作为 CA template，无需手动填写参数。

**步骤：**

1. 在 Unraid 进入 `Settings → Community Applications → Template Repositories`，添加：
   ```
   https://raw.githubusercontent.com/watchzerg/j-file-kit/main/unraid/
   ```
2. 在 Apps 页面搜索 `j-file-kit`，点击安装，按需修改媒体目录路径后确认。
3. 容器启动后访问 `http://<unraid-ip>:1307/docs` 查看 API 文档，或通过 WebUI 按钮直接打开。
