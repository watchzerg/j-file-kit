"""JAV 视频整理任务 E2E 测试

通过真实 Docker 容器验证文件整理任务的完整处理流程：
- 在宿主机 `jav_workspace/inbox`（媒体挂载根之下）目录下创建测试文件
- 调用 HTTP API 触发任务并等待完成
- 直接断言宿主机文件系统的结果路径

测试场景：
  A. 有番号视频 → jav_workspace/sorted/<首字母>/<前2字母>/<前缀>/
  B. 无番号视频 → jav_workspace/unsorted/
  C. 压缩包 → jav_workspace/archive/
  D. Misc 扩展名匹配 → 删除
  E. Misc 关键字 + 小体积 → 删除
  F. Misc 大文件 → jav_workspace/misc/
  G. 文件名冲突消解 → jav_workspace/sorted/（含 -jfk- 后缀的副本）
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


def _jav_workspace_root(host_media_mount: Path) -> Path:
    """宿主挂载的「媒体树根」下的 JAV workspace（与容器内 `/media/jav_workspace` 对应）。"""
    return host_media_mount / "jav_workspace"


def _write_file(path: Path, size: int = _1MB * 2) -> None:
    """创建指定大小的测试文件（零填充）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x00" * size)


def _trigger_task(base_url: str, dry_run: bool = False) -> int:
    """触发 jav_video_organizer 文件整理任务。

    Args:
        base_url: 服务根 URL
        dry_run: 是否为预览模式

    Returns:
        任务执行实例 run_id
    """
    resp = requests.post(
        f"{base_url}/api/tasks/{TASK_TYPE_JAV_VIDEO_ORGANIZER}/start",
        json={"dry_run": dry_run},
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
        _write_file(_jav_workspace_root(clean_media) / "inbox" / "ABC-100.mp4")

        status = _run_task(docker_service)

        assert status == "completed"
        assert (
            _jav_workspace_root(clean_media)
            / "sorted"
            / "A"
            / "AB"
            / "ABC"
            / "ABC-100.mp4"
        ).exists()
        assert not (_jav_workspace_root(clean_media) / "inbox" / "ABC-100.mp4").exists()

    def test_video_without_serial_id_goes_to_unsorted(
        self,
        docker_service: str,
        clean_media: Path,
    ) -> None:
        """无番号视频应被移动到 unsorted/ 目录下。"""
        _write_file(_jav_workspace_root(clean_media) / "inbox" / "family_trip.mp4")

        status = _run_task(docker_service)

        assert status == "completed"
        assert (
            _jav_workspace_root(clean_media) / "unsorted" / "family_trip.mp4"
        ).exists()
        assert not (
            _jav_workspace_root(clean_media) / "inbox" / "family_trip.mp4"
        ).exists()

    def test_archive_goes_to_archive(
        self,
        docker_service: str,
        clean_media: Path,
    ) -> None:
        """压缩包（无论是否含番号）应被移动到 archive/ 目录下。"""
        _write_file(
            _jav_workspace_root(clean_media) / "inbox" / "backup.zip",
            size=_1MB * 3,
        )

        status = _run_task(docker_service)

        assert status == "completed"
        assert (_jav_workspace_root(clean_media) / "archive" / "backup.zip").exists()
        assert not (_jav_workspace_root(clean_media) / "inbox" / "backup.zip").exists()

    def test_misc_matching_extension_deleted(
        self,
        docker_service: str,
        clean_media: Path,
    ) -> None:
        """扩展名匹配删除规则（.nfo）的 Misc 文件应被删除。"""
        nfo = _jav_workspace_root(clean_media) / "inbox" / "info.nfo"
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
        dat = _jav_workspace_root(clean_media) / "inbox" / "sample_clip.dat"
        _write_file(dat, size=_512KB)

        status = _run_task(docker_service)

        assert status == "completed"
        assert not dat.exists()

    def test_misc_large_file_goes_to_misc(
        self,
        docker_service: str,
        clean_media: Path,
    ) -> None:
        """体积超过 1MB、无 misc 删除规则匹配的 Misc 文件应被移动到 misc/ 目录。

        扩展名使用 .xyz（不在 misc 扩展名删除列表中）；stem 不含常见过滤关键字子串。
        若使用 .dat，会先被 misc 扩展名规则删除，无法覆盖「大文件进 misc」路径。
        """
        dat = _jav_workspace_root(clean_media) / "inbox" / "large_blob.xyz"
        _write_file(dat, size=_1MB * 2)

        status = _run_task(docker_service)

        assert status == "completed"
        assert (_jav_workspace_root(clean_media) / "misc" / "large_blob.xyz").exists()
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
        _write_file(_jav_workspace_root(clean_media) / "inbox" / "ABC-234.mp4")
        _write_file(
            _jav_workspace_root(clean_media)
            / "inbox"
            / "conflict_subdir"
            / "ABC-234.mp4",
        )

        status = _run_task(docker_service)

        assert status == "completed"
        target_dir = _jav_workspace_root(clean_media) / "sorted" / "A" / "AB" / "ABC"
        files_in_target = list(target_dir.iterdir())
        assert len(files_in_target) == 2  # noqa: PLR2004
        normal = [f for f in files_in_target if "-jfk-" not in f.name]
        conflict = [f for f in files_in_target if "-jfk-" in f.name]
        assert len(normal) == 1
        assert len(conflict) == 1
        assert normal[0].suffix == ".mp4"
        assert conflict[0].suffix == ".mp4"

    def test_dry_run_leaves_files_untouched(
        self,
        docker_service: str,
        clean_media: Path,
    ) -> None:
        """dry_run=True 时任务完成但文件保持原位，inbox 内容不变。

        验证 HTTP 层正确将 dry_run 标志透传到 Pipeline，
        而非仅靠单元/集成层保证。
        """
        source = _jav_workspace_root(clean_media) / "inbox" / "ABC-350.mp4"
        _write_file(source)

        run_id = _trigger_task(docker_service, dry_run=True)
        status = _wait_for_completion(docker_service, run_id)

        assert status == "completed"
        assert source.exists()
        assert not (
            _jav_workspace_root(clean_media)
            / "sorted"
            / "A"
            / "AB"
            / "ABC"
            / "ABC-350.mp4"
        ).exists()

    def test_empty_subdirectory_cleaned_after_processing(
        self,
        docker_service: str,
        clean_media: Path,
    ) -> None:
        """文件被处理后变空的子目录应被自动删除。"""
        subdir = _jav_workspace_root(clean_media) / "inbox" / "to_be_cleaned"
        _write_file(subdir / "STAR-100.mp4")

        status = _run_task(docker_service)

        assert status == "completed"
        assert (
            _jav_workspace_root(clean_media)
            / "sorted"
            / "S"
            / "ST"
            / "STAR"
            / "STAR-100.mp4"
        ).exists()
        assert not subdir.exists()
