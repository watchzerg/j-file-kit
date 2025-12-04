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
    rm -rf .mypy_cache
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
