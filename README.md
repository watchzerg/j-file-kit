# j-file-kit

项目目标：提供一个基于 Python 的文件任务处理工具，用于批量文件整理与自动化处理。

## 本地开发

```bash
# 安装依赖
uv sync --all-groups

# 启动服务（开发模式，自动重载）
uv run python -m j_file_kit.main --reload
```

服务启动后访问 http://localhost:8000/docs 查看 API 文档。

## Docker 本地测试

### 1. 配置本地媒体目录

媒体目录路径通过 `.env` 文件配置，不需要修改 `docker-compose.yml`：

```bash
cp .env.example .env
```

编辑 `.env`，填写宿主机上的实际媒体根目录：

```bash
MEDIA_ROOT=/path/to/your/media
```

Docker Compose 会自动读取 `.env`，将以下目录挂载进容器：

| 宿主机路径 | 容器内路径 |
|---|---|
| `$MEDIA_ROOT/inbox` | `/media/inbox`（待处理目录） |
| `$MEDIA_ROOT/sorted` | `/media/sorted`（整理后目录） |
| `$MEDIA_ROOT/unsorted` | `/media/unsorted`（无番号目录） |
| `$MEDIA_ROOT/archive` | `/media/archive`（压缩包目录） |
| `$MEDIA_ROOT/misc` | `/media/misc`（杂项目录） |

> **注意**：启动前上述目录必须存在，生产模式下若未挂载任何 `/media` 路径，容器将启动失败。

### 2. 生成测试文件（可选）

`scripts/gen_test_files.py` 可在 `inbox` 目录下快速生成覆盖各类场景的测试文件：

```bash
# 自动读取 MEDIA_ROOT 环境变量，生成到 $MEDIA_ROOT/inbox
MEDIA_ROOT=/path/to/your/media python scripts/gen_test_files.py

# 或直接指定目标目录
python scripts/gen_test_files.py /path/to/your/media/inbox
```

生成的测试场景包括：有番号视频/图片（→ `sorted/`）、无番号媒体（→ `unsorted/`）、压缩包（→ `archive/`）、各类 Misc 文件（删除或移至 `misc/`）、文件名冲突消解（`-jfk-xxxx` 后缀）、空目录自动清理等。

### 3. 启动容器

```bash
# 首次构建并启动
docker compose up --build

# 后续启动（无需重新构建）
docker compose up

# 后台运行
docker compose up -d
```

**查看日志：**

```bash
docker logs -f j-file-kit
```

**停止：**

```bash
docker compose down
```

服务启动后访问 http://localhost:8000/docs 查看 API 文档。

应用数据（配置、数据库、日志）保存在项目目录下的 `app-data/` 中。

## 部署到 Unraid

1. 构建镜像并推送到 Docker Hub：

```bash
docker build -t your-username/j-file-kit:latest .
docker push your-username/j-file-kit:latest
```

2. 在 Unraid Docker UI 中添加容器，填入以下参数：

| 参数 | 值 |
|------|----|
| Repository | `your-username/j-file-kit:latest` |
| Port | `宿主机端口:8000`（如 `8000:8000`） |
| Volume `/data` | `/mnt/user/appdata/j-file-kit` |
| 媒体目录（**必填**，至少一个） | 宿主机实际路径 `:` 容器内路径（如 `/mnt/user/media/inbox:/media/inbox`） |

3. 通过 API（`/api/file-task/config`）配置任务，将各目录路径设置为容器内挂载路径（如 `/media/inbox`）。