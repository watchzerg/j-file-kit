# syntax=docker/dockerfile:1

# ── Builder ──────────────────────────────────────────────────────────────────
# uv 官方镜像内置 uv 和 Python 3.14，用于安装依赖并打包虚拟环境
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS builder

WORKDIR /app

# 先复制依赖声明文件，利用 Docker 层缓存；代码变更不会重新安装依赖
COPY pyproject.toml uv.lock ./

# 仅安装生产依赖（不包含 dev 组），锁定版本，不安装项目本身
RUN uv sync --no-dev --no-install-project --frozen

# 复制源码后安装项目（包名注册到 .venv）
COPY src/ ./src/
RUN uv sync --no-dev --frozen

# ── Runtime ───────────────────────────────────────────────────────────────────
# 使用官方 Python slim 镜像，不包含 uv 和构建工具，减小镜像体积
FROM python:3.14-slim-bookworm AS runtime

WORKDIR /app

# 从 builder 阶段复制已完整安装的虚拟环境和源码
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src

# 将 .venv 优先放入 PATH，使 python / uvicorn 等命令直接可用
ENV PATH="/app/.venv/bin:$PATH"

# 应用数据目录（config、sqlite、logs），需在运行时挂载持久化 volume
ENV J_FILE_KIT_BASE_DIR="/data"

# 使用 JSON 格式日志，便于容器日志收集系统解析
ENV J_FILE_KIT_ENV="production"

# 创建与 Unraid nobody:users（UID=99, GID=100）一致的用户，避免文件权限问题
RUN groupadd -g 100 users 2>/dev/null || true \
    && useradd -u 99 -g 100 -M -s /sbin/nologin nobody 2>/dev/null || true

# 创建 /data 目录并赋予正确权限；运行时由 volume 覆盖，但需保证初始存在
RUN mkdir -p /data && chown 99:100 /data

USER nobody

EXPOSE 8000

# 每 30 秒检查一次 /health 端点，10 秒启动宽限期，连续 3 次失败则标记 unhealthy
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["j-file-kit", "--host", "0.0.0.0", "--port", "8000"]
