# j-file-kit 开发任务配置

# 默认任务：显示所有可用任务
default:
    @just --list

# 安装 pre-commit 钩子
pre-install:
    uv run pre-commit install --hook-type pre-commit --hook-type pre-push

# 运行 pre-commit 阶段的钩子
pre-commit:
    uv run pre-commit run --hook-stage pre-commit --all-files

# 运行 pre-push 阶段的钩子
pre-push:
    uv run pre-commit run --hook-stage pre-push --all-files

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

# 运行所有测试
test:
    uv run pytest

# 仅运行单元测试（快速，无 I/O）
test-unit:
    uv run pytest -m unit

# 仅运行集成测试（涉及文件系统 / 数据库）
test-int:
    uv run pytest -m integration

# 运行 E2E 测试（需要 Docker 运行中）
test-e2e:
    uv run pytest -m e2e -v

# 运行测试并输出覆盖率报告
test-cov:
    uv run pytest --cov=src/j_file_kit --cov-report=term-missing

# ── 手工调试辅助 ────────────────────────────────────────────────────────────────

# 生成测试文件到 $MEDIA_ROOT/jav_workspace/inbox（需 .env 中配置 MEDIA_ROOT）
gen-test-files:
    uv run python scripts/gen_test_files.py

# 打版本 tag 并推送，触发 GitHub Actions 构建镜像
# 会先运行 E2E 测试，全部通过后才打 tag（需要 Docker 运行中）
# 用法：just release 1.2.3
release VERSION:
    uv run pytest -m e2e -v
    git tag v{{VERSION}}
    git push origin v{{VERSION}}

# 本地构建镜像（不启动容器），完成后输出镜像体积
docker-build:
    docker build -t j-file-kit:local .
    @echo ""
    docker images j-file-kit:local --format "镜像: {{{{.Repository}}}}:{{{{.Tag}}}}  大小: {{{{.Size}}}}  创建: {{{{.CreatedSince}}}}"

# 进入本地构建的镜像，查看文件结构（需先执行 docker-build）
docker-sh:
    docker run --rm -it --entrypoint sh j-file-kit:local

# 构建镜像并在后台启动容器（读取 .env 中的 MEDIA_ROOT）
docker-up:
    docker compose up -d --build

# 停止并移除容器
docker-down:
    docker compose down

# 实时跟踪容器日志（Ctrl+C 退出）
docker-logs:
    docker compose logs -f

# 触发 jav_video_organizer 整理任务；DRY_RUN=true 可预览不实际移动文件
# 用法：just task-run 或 just task-run DRY_RUN=true
task-run DRY_RUN="false":
    curl -sf -X POST http://localhost:8000/api/tasks/jav_video_organizer/start \
        -H "Content-Type: application/json" \
        -d '{"dry_run": {{DRY_RUN}}}' | python3 -m json.tool

# 列出最近 10 个任务（run_id、状态、创建时间等）
task-list:
    #!/usr/bin/env python3
    import json, urllib.request
    with urllib.request.urlopen("http://localhost:8000/api/tasks") as resp:
        data = json.load(resp)
    runs = list(reversed(data.get("runs", [])[-10:]))
    print("{:<8} {:<12} {:<40} {:<25} {}".format("run_id", "status", "run_name", "start_time", "end_time"))
    print("-" * 110)
    for r in runs:
        print("{:<8} {:<12} {:<40} {:<25} {}".format(
            r["run_id"], r["status"], r["run_name"],
            str(r.get("start_time") or ""), str(r.get("end_time") or ""),
        ))

# 查询指定 run_id 的任务状态
# 用法：just task-status 1
task-status RUN_ID:
    curl -sf http://localhost:8000/api/tasks/{{RUN_ID}} | python3 -m json.tool
