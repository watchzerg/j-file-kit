"""RawFilePipeline 集成测试：完整 workspace 布局 + 真实 SQLite 仓储。

验证阶段 1（inbox 第一层 → ``files_misc``）与阶段 3（``files_misc`` 分流）串联行为，
以及 ``dry_run`` 不写盘；统计快照含仓储聚合字段（见 ``RawFilePipeline._finish_task``）。
"""

import pytest

from j_file_kit.app.file_task.application.config_common import RawWorkspacePaths
from j_file_kit.app.file_task.application.raw_pipeline.pipeline import RawFilePipeline
from j_file_kit.infrastructure.persistence.sqlite.file_task.file_result_repository import (
    FileResultRepositoryImpl,
)

pytestmark = [pytest.mark.integration, pytest.mark.slow]


class TestZipPhase1ThenPhase3ToCompressed:
    """压缩包：阶段 1 收编 → 阶段 3 迁入 ``files_compressed``。"""

    def test_zip_moves_to_files_compressed(
        self,
        raw_pipeline_with_real_repo: RawFilePipeline,
        raw_integration_paths: RawWorkspacePaths,
        file_result_repository: FileResultRepositoryImpl,
    ) -> None:
        """``inbox/foo.zip`` 经 ``files_misc`` 最终出现在 ``files_compressed``。"""
        src = raw_integration_paths.inbox / "foo.zip"
        src.write_bytes(b"z")

        stats = raw_pipeline_with_real_repo.run(dry_run=False)

        assert not src.exists()
        dest = raw_integration_paths.files_compressed / "foo.zip"
        assert dest.exists()
        assert dest.read_bytes() == b"z"
        assert stats.phase1_moved_files == 1
        repo_stats = file_result_repository.get_statistics(1)
        assert stats.total_items == repo_stats["total_items"]
        assert stats.total_items >= 1


class TestVideoSerialPhase1ThenPhase3ToJavBucket:
    """含番号视频迁入 ``files_video_jav``（默认关键字未抢先命中）。"""

    def test_serial_mp4_goes_to_files_video_jav(
        self,
        raw_pipeline_with_real_repo: RawFilePipeline,
        raw_integration_paths: RawWorkspacePaths,
    ) -> None:
        """``ABC-123.mp4`` 最终落在 ``files_video_jav`` 根目录。"""
        src = raw_integration_paths.inbox / "ABC-123.mp4"
        src.write_bytes(b"v")

        stats = raw_pipeline_with_real_repo.run(dry_run=False)

        assert not src.exists()
        target = raw_integration_paths.files_video_jav / "ABC-123.mp4"
        assert target.exists()
        assert stats.phase1_moved_files == 1


class TestDryRunLeavesInboxIntact:
    """预览模式不落盘。"""

    def test_dry_run_keeps_file_in_inbox(
        self,
        raw_pipeline_with_real_repo: RawFilePipeline,
        raw_integration_paths: RawWorkspacePaths,
    ) -> None:
        """``dry_run=True`` 时 inbox 源文件仍在，目标桶无实体文件。"""
        src = raw_integration_paths.inbox / "keep_me.mp4"
        src.write_bytes(b"x")

        raw_pipeline_with_real_repo.run(dry_run=True)

        assert src.exists()
        assert not list(raw_integration_paths.files_misc.iterdir())
        assert not list(raw_integration_paths.files_compressed.iterdir())
