"""Raw 收件箱整理任务 E2E 测试

通过 Docker 容器验证 ``raw_file_organizer`` 任务：在宿主机 ``raw_workspace/inbox`` 下放置文件，
HTTP 触发任务并等待完成，断言 ``/media/raw_workspace`` 下落地路径（与 ``docs/RAW_FILE_PROCESSING_PIPELINE.md`` 一致）。

前置条件：Docker 可用。运行方式：``just test-e2e``。
"""

import time
from pathlib import Path

import pytest
import requests

from j_file_kit.app.file_task.domain.constants import TASK_TYPE_RAW_FILE_ORGANIZER

_1MB = 1024 * 1024


def _raw_workspace_root(host_media_mount: Path) -> Path:
    """宿主挂载媒体根下的 Raw workspace（与容器内 ``/media/raw_workspace`` 对应）。"""
    return host_media_mount / "raw_workspace"


def _write_file(path: Path, size: int = _1MB * 2) -> None:
    """创建指定大小的测试文件（零填充）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x00" * size)


def _trigger_raw_task(base_url: str, dry_run: bool = False) -> int:
    """触发 raw_file_organizer 任务，返回 run_id。"""
    resp = requests.post(
        f"{base_url}/api/tasks/{TASK_TYPE_RAW_FILE_ORGANIZER}/start",
        json={"dry_run": dry_run},
        timeout=10,
    )
    assert resp.status_code == 200, f"启动任务失败：{resp.status_code} {resp.text}"
    return int(resp.json()["run_id"])


def _wait_for_completion(base_url: str, run_id: int, timeout: int = 30) -> str:
    """轮询任务状态直到 completed / failed 或超时。"""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        resp = requests.get(f"{base_url}/api/tasks/{run_id}", timeout=5)
        assert resp.status_code == 200, f"查询任务状态失败：{resp.status_code}"
        status = str(resp.json()["status"])
        if status in ("completed", "failed"):
            return status
        time.sleep(0.5)

    raise TimeoutError(f"任务 {run_id} 在 {timeout}s 内未完成")


def _run_raw_task(base_url: str) -> str:
    """触发 Raw 任务并等待完成，返回最终状态。"""
    run_id = _trigger_raw_task(base_url)
    return _wait_for_completion(base_url, run_id)


pytestmark = pytest.mark.e2e


class TestRawFileOrganizerE2E:
    """Raw 整理任务端到端：阶段 1 + 阶段 3 串联后的磁盘结果。"""

    def test_level1_video_goes_to_files_video_misc(
        self,
        docker_service: str,
        clean_media: Path,
    ) -> None:
        """无番号视频经 phase1→phase3 归入 ``files_video_misc``。"""
        _write_file(_raw_workspace_root(clean_media) / "inbox" / "hello.mp4")

        status = _run_raw_task(docker_service)

        assert status == "completed"
        root = _raw_workspace_root(clean_media)
        assert (root / "files_video_misc" / "hello.mp4").exists()
        assert not (root / "inbox" / "hello.mp4").exists()

    def test_zip_goes_to_files_compressed(
        self,
        docker_service: str,
        clean_media: Path,
    ) -> None:
        """压缩包经 ``files_misc`` 分流至 ``files_compressed``。"""
        _write_file(_raw_workspace_root(clean_media) / "inbox" / "foo.zip", size=_1MB)

        status = _run_raw_task(docker_service)

        assert status == "completed"
        root = _raw_workspace_root(clean_media)
        assert (root / "files_compressed" / "foo.zip").exists()
        assert not (root / "inbox" / "foo.zip").exists()

    def test_dry_run_leaves_inbox_untouched(
        self,
        docker_service: str,
        clean_media: Path,
    ) -> None:
        """``dry_run=True`` 时 inbox 源文件仍在，目标目录无迁入实体。"""
        source = _raw_workspace_root(clean_media) / "inbox" / "preview_hold.mp4"
        _write_file(source)

        run_id = _trigger_raw_task(docker_service, dry_run=True)
        status = _wait_for_completion(docker_service, run_id)

        assert status == "completed"
        assert source.exists()
        root = _raw_workspace_root(clean_media)
        assert not (root / "files_video_misc" / "preview_hold.mp4").exists()
