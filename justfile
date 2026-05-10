# j-file-kit 开发任务配置

# 默认任务：显示所有可用任务
default:
    @just --list

# 安装 pre-commit 钩子
pre-install:
    uv run pre-commit install --hook-type pre-commit --hook-type pre-push

# 手工运行 pre-commit 阶段检查
pre-commit:
    uv run pre-commit run --hook-stage pre-commit --all-files

# 清理临时文件
clean:
    rm -rf .pytest_cache
    rm -rf .ruff_cache
    rm -rf dist
    rm -rf build
    rm -rf *.egg-info
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete
    @echo "清理完成"

# 同步依赖
deps-sync:
	uv sync --all-groups

# 升级依赖
deps-upgrade:
    uv lock --upgrade
    uv sync --all-groups
    
# 初始化或升级python版本（例如3.14）
py-upgrade VERSION:
    uv python install {{VERSION}}
    uv python pin {{VERSION}}
    uv venv --refresh
    uv sync --all-groups
    uv run python -V


# ── 前端开发 ────────────────────────────────────────────────────────────────────────────────

# 安装/同步前端依赖
fe-install:
    cd frontend && bun install

# 启动前端开发服务器（Vite HMR，:5173）
fe-dev:
    cd frontend && bun run dev

# 构建前端产物（输出到 src/j_file_kit/static/）
fe-build:
    cd frontend && bun run build

# 前端 lint + format 检查（Biome）
fe-check:
    cd frontend && bunx biome check .

# 自动修复前端 lint + format 问题
fe-fix:
    cd frontend && bunx biome check --write .

# 运行前端单元测试（vitest）
fe-test:
    cd frontend && bun run test

# 清理前端依赖和构建产物（重装前用）
fe-clean:
    rm -rf frontend/node_modules frontend/dist
    rm -rf src/j_file_kit/static
    @echo "前端清理完成"

# 添加 shadcn/ui 组件，用法：just fe-add button
fe-add COMPONENT:
    cd frontend && bunx shadcn add {{COMPONENT}}

# ── 全栈本地开发 ─────────────────────────────────────────────────────────────────────────────

# 同时启动后端（:8000）和前端（:5173），两者就绪后自动打开默认浏览器 —— Ctrl+C 同时终止两者
dev:
    #!/usr/bin/env bash
    set -euo pipefail
    trap 'echo ""; echo "正在关闭…"; kill $(jobs -p) 2>/dev/null; wait 2>/dev/null; echo "已退出"' INT TERM EXIT
    echo "▶ 后端启动中 → http://localhost:8000  (base_dir=./app-data)"
    J_FILE_KIT_BASE_DIR=./app-data uv run j-file-kit &
    echo "▶ 前端启动中 → http://localhost:5173"
    (cd frontend && bun run dev) &
    # 等待 Vite 就绪（轮询 :5173），超时 30s
    timeout=30
    until curl -sf http://localhost:5173 >/dev/null 2>&1; do
        sleep 0.5
        timeout=$((timeout - 1))
        if (( timeout <= 0 )); then
            echo "⚠ 前端未在 30s 内就绪，跳过自动打开浏览器"
            break
        fi
    done
    if (( timeout > 0 )); then
        echo "✓ 前端就绪，打开浏览器 → http://localhost:5173"
        open http://localhost:5173
    fi
    wait

# ── 基于 Docker的本地E2E测试 ────────────────────────────────────────────────────────────────

# 确保 Docker 可用：就绪则跳过；macOS 未就绪时 `open -a Docker` 并最多等待 180s（懒加载）。非 macOS 请手动启动 Docker
ensure-docker:
    #!/usr/bin/env bash
    set -euo pipefail
    if docker info >/dev/null 2>&1; then
        echo "Docker 已就绪"
        exit 0
    fi
    case "$(uname -s)" in
        Darwin)
            echo "正在启动 Docker Desktop…"
            open -a Docker
            deadline=$((SECONDS + 180))
            while ! docker info >/dev/null 2>&1; do
                if (( SECONDS > deadline )); then
                    echo "超时：Docker 仍未就绪，请检查 Docker Desktop。" >&2
                    exit 1
                fi
                sleep 2
            done
            echo "Docker 已就绪"
            ;;
        *)
            echo "未检测到可用的 Docker，且当前系统未配置自动启动（仅 macOS 支持 open Docker Desktop）。" >&2
            exit 1
            ;;
    esac

# 运行 E2E 测试（需要 Docker 运行中）
test-e2e: ensure-docker
    uv run pytest -m e2e -v

# 构建镜像并在后台启动容器（读取 .env 中的 MEDIA_ROOT）
docker-up: ensure-docker
    docker compose up -d --build

# 停止并移除容器
docker-down:
    docker compose down

# 实时跟踪容器日志（Ctrl+C 退出）
docker-logs:
    docker compose logs -f

# 打版本 tag 并推送，触发 GitHub Actions 构建镜像
# 会先运行 E2E 测试，全部通过后才打 tag（需要 Docker 运行中）
# 用法：just release 1.2.3
release VERSION: test-e2e
    git tag v{{VERSION}}
    git push origin v{{VERSION}}