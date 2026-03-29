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

> **前置要求**：启动前必须在 `docker-compose.yml` 的 `volumes` 中取消注释并配置至少一个 `/media` 子目录挂载（如 `/path/to/your/inbox:/media/inbox`）。生产模式下若未挂载任何 `/media` 路径，容器将启动失败并报错。

**首次构建并启动：**

```bash
docker compose up --build
```

**后续启动（无需重新构建）：**

```bash
docker compose up
```

**后台运行：**

```bash
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