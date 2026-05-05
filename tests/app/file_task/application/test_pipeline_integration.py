"""Pipeline 端到端集成测试

验证 scan → analyze → execute 全流程，覆盖核心文件过滤与分类逻辑。
"""

from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.slow]


class TestVideoWithSerialMovedToSorted:
    """有番号视频 → sorted 目录"""

    def test_video_with_serial_moved_to_sorted(
        self,
        pipeline_with_real_repo,
        tmp_path: Path,
    ) -> None:
        """ABC-123.mp4 移动到 sorted/A/AB/ABC/"""
        inbox = tmp_path / "inbox"
        inbox.mkdir(parents=True)
        (tmp_path / "logs").mkdir(parents=True)
        (tmp_path / "sorted").mkdir(parents=True)
        (tmp_path / "unsorted").mkdir(parents=True)
        (tmp_path / "archive").mkdir(parents=True)
        (tmp_path / "misc").mkdir(parents=True)

        source = inbox / "ABC-123.mp4"
        source.touch()

        pipeline_with_real_repo.run(dry_run=False)

        target = tmp_path / "sorted" / "A" / "AB" / "ABC" / "ABC-123.mp4"
        assert target.exists()
        assert not source.exists()


class TestVideoWithoutSerialMovedToUnsorted:
    """无番号视频 → unsorted 目录"""

    def test_video_without_serial_moved_to_unsorted(
        self,
        pipeline_with_real_repo,
        tmp_path: Path,
    ) -> None:
        """no_serial.mp4 移动到 unsorted"""
        inbox = tmp_path / "inbox"
        inbox.mkdir(parents=True)
        (tmp_path / "logs").mkdir(parents=True)
        (tmp_path / "sorted").mkdir(parents=True)
        (tmp_path / "unsorted").mkdir(parents=True)
        (tmp_path / "archive").mkdir(parents=True)
        (tmp_path / "misc").mkdir(parents=True)

        source = inbox / "no_serial.mp4"
        source.touch()

        pipeline_with_real_repo.run(dry_run=False)

        target = tmp_path / "unsorted" / "no_serial.mp4"
        assert target.exists()
        assert not source.exists()


class TestInboxPreDelete:
    """收件箱预删除（扩展名分类前）"""

    def test_exact_stem_matched_file_deleted(
        self,
        pipeline_with_inbox_delete_repo,
        tmp_path: Path,
    ) -> None:
        """stem 为 junk 的文件在分类前被删除，不会进入 sorted/unsorted"""
        inbox = tmp_path / "inbox"
        inbox.mkdir(parents=True)
        (tmp_path / "logs").mkdir(parents=True)
        (tmp_path / "sorted").mkdir(parents=True)
        (tmp_path / "unsorted").mkdir(parents=True)
        (tmp_path / "archive").mkdir(parents=True)
        (tmp_path / "misc").mkdir(parents=True)

        source = inbox / "junk.mp4"
        source.touch()

        pipeline_with_inbox_delete_repo.run(dry_run=False)

        assert not source.exists()
        assert not (tmp_path / "unsorted" / "junk.mp4").exists()


class TestMiscFileDeleted:
    """Misc 文件删除规则"""

    def test_misc_file_deleted_by_extension(
        self,
        pipeline_with_real_repo,
        tmp_path: Path,
    ) -> None:
        """扩展名匹配 .tmp 时删除"""
        inbox = tmp_path / "inbox"
        inbox.mkdir(parents=True)
        (tmp_path / "logs").mkdir(parents=True)
        (tmp_path / "sorted").mkdir(parents=True)
        (tmp_path / "unsorted").mkdir(parents=True)
        (tmp_path / "archive").mkdir(parents=True)
        (tmp_path / "misc").mkdir(parents=True)

        source = inbox / "temp.tmp"
        source.touch()

        pipeline_with_real_repo.run(dry_run=False)

        assert not source.exists()

    def test_misc_file_deleted_by_size(
        self,
        pipeline_with_real_repo,
        tmp_path: Path,
    ) -> None:
        """小体积 Misc 文件在 max_size 阈值内时删除"""
        inbox = tmp_path / "inbox"
        inbox.mkdir(parents=True)
        (tmp_path / "logs").mkdir(parents=True)
        (tmp_path / "sorted").mkdir(parents=True)
        (tmp_path / "unsorted").mkdir(parents=True)
        (tmp_path / "archive").mkdir(parents=True)
        (tmp_path / "misc").mkdir(parents=True)

        source = inbox / "normal_payload.xyz"
        source.write_bytes(b"x")

        pipeline_with_real_repo.run(dry_run=False)

        assert not source.exists()


class TestArchiveMovedToArchiveDir:
    """压缩包 → archive 目录"""

    def test_archive_moved_to_archive_dir(
        self,
        pipeline_with_real_repo,
        tmp_path: Path,
    ) -> None:
        """data.zip 移动到 archive"""
        inbox = tmp_path / "inbox"
        inbox.mkdir(parents=True)
        (tmp_path / "logs").mkdir(parents=True)
        (tmp_path / "sorted").mkdir(parents=True)
        (tmp_path / "unsorted").mkdir(parents=True)
        (tmp_path / "archive").mkdir(parents=True)
        (tmp_path / "misc").mkdir(parents=True)

        source = inbox / "data.zip"
        source.touch()

        pipeline_with_real_repo.run(dry_run=False)

        target = tmp_path / "archive" / "data.zip"
        assert target.exists()
        assert not source.exists()


class TestDryRunNoPhysicalChanges:
    """dry_run 仅分析不执行"""

    def test_dry_run_no_physical_changes(
        self,
        pipeline_with_real_repo,
        tmp_path: Path,
    ) -> None:
        """dry_run 时文件仍在 inbox"""
        inbox = tmp_path / "inbox"
        inbox.mkdir(parents=True)
        (tmp_path / "logs").mkdir(parents=True)
        (tmp_path / "sorted").mkdir(parents=True)
        (tmp_path / "unsorted").mkdir(parents=True)
        (tmp_path / "archive").mkdir(parents=True)
        (tmp_path / "misc").mkdir(parents=True)

        source = inbox / "ABC-123.mp4"
        source.touch()

        pipeline_with_real_repo.run(dry_run=True)

        assert source.exists()
        target = tmp_path / "sorted" / "A" / "AB" / "ABC" / "ABC-123.mp4"
        assert not target.exists()
