"""JAV 视频整理任务 E2E 测试

通过真实 Docker 容器验证文件整理任务的完整处理流程：
- 在宿主机 inbox 目录下创建测试文件
- 调用 HTTP API 触发任务并等待完成
- 直接断言宿主机文件系统的结果路径

测试场景：
  A. 有番号视频 → sorted/<首字母>/<前2字母>/<前缀>/
  B. 无番号视频 → unsorted/
  C. 压缩包 → archive/
  D. Misc 扩展名匹配 → 删除
  E. Misc 关键字 + 小体积 → 删除
  F. Misc 大文件 → misc/
  G. 文件名冲突消解 → sorted/（含 -jfk- 后缀的副本）
  H. 处理后空子目录 → 自动被清除

前置条件：Docker 已运行，镜像可构建。运行方式：
  just test-e2e
"""

import time
from pathlib import Path

import pytest
import requests

from j_file_kit.app.file_task.domain.constants import TASK_TYPE_JAV_VIDEO_ORGANIZER

_1MB = 1024 * 1024
_512KB = 512 * 1024


def _write_file(path: Path, size: int = _1MB * 2) -> None:
    """创建指定大小的测试文件（零填充）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x00" * size)


def _trigger_task(base_url: str) -> int:
    """触发 jav_video_organizer 文件整理任务。

    Args:
        base_url: 服务根 URL

    Returns:
        任务执行实例 run_id
    """
    resp = requests.post(
        f"{base_url}/api/tasks/{TASK_TYPE_JAV_VIDEO_ORGANIZER}/start",
        json={"dry_run": False},
        timeout=10,
    )
    assert resp.status_code == 200, f"启动任务失败：{resp.status_code} {resp.text}"
    return int(resp.json()["run_id"])


def _wait_for_completion(base_url: str, run_id: int, timeout: int = 30) -> str:
    """轮询任务状态直到 completed / failed 或超时。

    Args:
        base_url: 服务根 URL
        run_id: 任务执行实例 ID
        timeout: 最长等待秒数

    Returns:
        最终任务状态字符串（"completed" 或 "failed"）

    Raises:
        TimeoutError: 超时后任务仍未结束
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        resp = requests.get(f"{base_url}/api/tasks/{run_id}", timeout=5)
        assert resp.status_code == 200, f"查询任务状态失败：{resp.status_code}"
        status = str(resp.json()["status"])
        if status in ("completed", "failed"):
            return status
        time.sleep(0.5)

    raise TimeoutError(f"任务 {run_id} 在 {timeout}s 内未完成")


def _run_task(base_url: str) -> str:
    """触发任务并等待完成，返回最终状态。"""
    run_id = _trigger_task(base_url)
    return _wait_for_completion(base_url, run_id)


pytestmark = pytest.mark.e2e


class TestJavVideoOrganizerE2E:
    """JAV 视频整理任务端到端测试。

    每个测试方法通过 clean_media fixture 获得干净的媒体目录，
    docker_service fixture 保证容器在整个模块期间只启动一次。
    """

    def test_video_with_serial_id_goes_to_sorted(
        self,
        docker_service: str,
        clean_media: Path,
    ) -> None:
        """有番号视频应被移动到 sorted/<首字母>/<前2字母>/<前缀>/ 目录下。"""
        _write_file(clean_media / "inbox" / "ABC-001.mp4")

        status = _run_task(docker_service)

        assert status == "completed"
        assert (clean_media / "sorted" / "A" / "AB" / "ABC" / "ABC-001.mp4").exists()
        assert not (clean_media / "inbox" / "ABC-001.mp4").exists()

    def test_video_without_serial_id_goes_to_unsorted(
        self,
        docker_service: str,
        clean_media: Path,
    ) -> None:
        """无番号视频应被移动到 unsorted/ 目录下。"""
        _write_file(clean_media / "inbox" / "home_video_2024.mp4")

        status = _run_task(docker_service)

        assert status == "completed"
        assert (clean_media / "unsorted" / "home_video_2024.mp4").exists()
        assert not (clean_media / "inbox" / "home_video_2024.mp4").exists()

    def test_archive_goes_to_archive(
        self,
        docker_service: str,
        clean_media: Path,
    ) -> None:
        """压缩包（无论是否含番号）应被移动到 archive/ 目录下。"""
        _write_file(clean_media / "inbox" / "backup.zip", size=_1MB * 3)

        status = _run_task(docker_service)

        assert status == "completed"
        assert (clean_media / "archive" / "backup.zip").exists()
        assert not (clean_media / "inbox" / "backup.zip").exists()

    def test_misc_matching_extension_deleted(
        self,
        docker_service: str,
        clean_media: Path,
    ) -> None:
        """扩展名匹配删除规则（.nfo）的 Misc 文件应被删除。"""
        nfo = clean_media / "inbox" / "info.nfo"
        _write_file(nfo, size=512)

        status = _run_task(docker_service)

        assert status == "completed"
        assert not nfo.exists()

    def test_misc_keyword_small_file_deleted(
        self,
        docker_service: str,
        clean_media: Path,
    ) -> None:
        """文件名含 sample 关键字且体积 ≤ 1MB 的 Misc 文件应被删除。"""
        dat = clean_media / "inbox" / "sample_clip.dat"
        _write_file(dat, size=_512KB)

        status = _run_task(docker_service)

        assert status == "completed"
        assert not dat.exists()

    def test_misc_large_file_goes_to_misc(
        self,
        docker_service: str,
        clean_media: Path,
    ) -> None:
        """体积超过 1MB 的 Misc 文件（即使含关键字）应被移动到 misc/ 目录。"""
        dat = clean_media / "inbox" / "sample_over_limit.dat"
        _write_file(dat, size=_1MB * 2)

        status = _run_task(docker_service)

        assert status == "completed"
        assert (clean_media / "misc" / "sample_over_limit.dat").exists()
        assert not dat.exists()

    def test_filename_conflict_resolution(
        self,
        docker_service: str,
        clean_media: Path,
    ) -> None:
        """inbox 根目录和子目录各有同名番号文件时，第二个应以 -jfk-xxxx 后缀落地。

        scan_directory_items 自底向上遍历，子目录文件先处理（正常移动），
        根目录同名文件后处理（触发冲突消解，文件名含 -jfk-）。
        """
        _write_file(clean_media / "inbox" / "ABC-002.mp4")
        _write_file(clean_media / "inbox" / "conflict_subdir" / "ABC-002.mp4")

        status = _run_task(docker_service)

        assert status == "completed"
        target_dir = clean_media / "sorted" / "A" / "AB" / "ABC"
        files_in_target = list(target_dir.iterdir())
        assert len(files_in_target) == 2  # noqa: PLR2004
        normal = [f for f in files_in_target if "-jfk-" not in f.name]
        conflict = [f for f in files_in_target if "-jfk-" in f.name]
        assert len(normal) == 1
        assert len(conflict) == 1
        assert normal[0].suffix == ".mp4"
        assert conflict[0].suffix == ".mp4"

    def test_empty_subdirectory_cleaned_after_processing(
        self,
        docker_service: str,
        clean_media: Path,
    ) -> None:
        """文件被处理后变空的子目录应被自动删除。"""
        subdir = clean_media / "inbox" / "to_be_cleaned"
        _write_file(subdir / "STAR-001.mp4")

        status = _run_task(docker_service)

        assert status == "completed"
        assert (clean_media / "sorted" / "S" / "ST" / "STAR" / "STAR-001.mp4").exists()
        assert not subdir.exists()
