"""E2E 测试 fixtures

管理 Docker 容器的生命周期，为端到端测试提供：
- 宿主机临时媒体目录（挂载进容器的 /media）
- 宿主机临时数据目录（挂载进容器的 /data）
- 运行中的容器服务 URL
- 每个测试前清理媒体目录的 fixture
"""

import os
import shutil
import subprocess
import time
from collections.abc import Generator
from pathlib import Path

import pytest
import requests
import yaml

from j_file_kit.app.file_task.application.config import (
    create_default_jav_video_organizer_task_config,
)
from j_file_kit.app.file_task.domain.constants import TASK_TYPE_JAV_VIDEO_ORGANIZER

# 项目根目录（conftest.py 位于 tests/e2e/，向上两级）
_PROJECT_ROOT = Path(__file__).parent.parent.parent

_MEDIA_SUBDIRS = ("inbox", "sorted", "unsorted", "archive", "misc")
_BASE_URL = "http://localhost:8000"


# ── fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def media_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """创建临时媒体根目录，包含所有必要子目录。

    目录层级与容器内一致：root/jav/inbox 等，对应 /media/jav/inbox。
    module 级别：同一测试文件内所有用例共享同一目录，
    通过 clean_media fixture 在用例间清理。
    """
    root = tmp_path_factory.mktemp("media")
    jav_root = root / "jav"
    jav_root.mkdir()
    for subdir in _MEDIA_SUBDIRS:
        (jav_root / subdir).mkdir()
    return root


@pytest.fixture(scope="module")
def app_data_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """创建临时应用数据目录（SQLite / config / logs）。

    module 级别：整个测试模块共用一个数据目录，避免反复初始化数据库。
    """
    return tmp_path_factory.mktemp("app_data")


@pytest.fixture(scope="module")
def docker_service(
    media_root: Path,
    app_data_dir: Path,
) -> Generator[str]:
    """启动 Docker 容器，yield 服务根 URL，测试结束后关闭容器。

    使用 MEDIA_ROOT 和 APP_DATA_DIR 环境变量将临时目录挂载进容器，
    确保与宿主机文件系统直接共享，测试可直接断言宿主机路径。

    Yields:
        容器服务根 URL，如 "http://localhost:8000"
    """
    env = {
        **os.environ,
        "MEDIA_ROOT": str(media_root),
        "APP_DATA_DIR": str(app_data_dir),
    }

    _seed_e2e_task_config_yaml(app_data_dir)

    subprocess.run(
        ["docker", "compose", "up", "-d", "--build"],
        cwd=_PROJECT_ROOT,
        env=env,
        check=True,
        capture_output=True,
    )

    try:
        _wait_for_health(_BASE_URL, timeout=90)
        yield _BASE_URL
    finally:
        subprocess.run(
            ["docker", "compose", "down"],
            cwd=_PROJECT_ROOT,
            env=env,
            check=False,
            capture_output=True,
        )


@pytest.fixture
def clean_media(media_root: Path) -> Path:
    """在每个测试前清空并重建所有媒体子目录。

    Returns:
        媒体根目录路径，各子目录已清空就绪。
    """
    jav_root = media_root / "jav"
    for subdir in _MEDIA_SUBDIRS:
        d = jav_root / subdir
        shutil.rmtree(d, ignore_errors=True)
        d.mkdir()
    return media_root


# ── 内部辅助函数 ───────────────────────────────────────────────────────────────


def _seed_e2e_task_config_yaml(app_data_dir: Path) -> None:
    """在首次启动前写入 task_config.yaml，关闭小视频删除（E2E 使用数 MB 的占位文件）。"""
    tc = create_default_jav_video_organizer_task_config()
    cfg = dict(tc.config)
    cfg["video_small_delete_bytes"] = None
    config_dir = app_data_dir / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    path = config_dir / "task_config.yaml"
    data = {
        TASK_TYPE_JAV_VIDEO_ORGANIZER: {
            "enabled": tc.enabled,
            "config": cfg,
        },
    }
    path.write_text(
        yaml.dump(
            data,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def _wait_for_health(base_url: str, timeout: int = 90) -> None:
    """轮询 /health 端点直到返回 200 或超时。

    Args:
        base_url: 服务根 URL
        timeout: 最长等待秒数

    Raises:
        TimeoutError: 超时后仍未就绪
    """
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None

    while time.monotonic() < deadline:
        try:
            resp = requests.get(f"{base_url}/health", timeout=3)
            if resp.status_code == 200:
                return
        except requests.RequestException as e:
            last_error = e
        time.sleep(1)

    raise TimeoutError(
        f"容器在 {timeout}s 内未就绪（{base_url}/health）。最后一次错误：{last_error}",
    )
