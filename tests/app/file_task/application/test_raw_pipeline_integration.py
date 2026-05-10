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


class TestConflictResolutionPreservesDestination:
    """完整管道：目标桶已有同名文件/目录时，不得静默覆盖。"""

    def test_existing_file_in_dest_not_overwritten_by_inbox_file(
        self,
        raw_pipeline_with_real_repo: RawFilePipeline,
        raw_integration_paths: RawWorkspacePaths,
    ) -> None:
        """``files_video_misc/hello.mp4`` 已存在时，inbox 的同名文件经 phase1→phase3
        落地时应生成 -jfk-xxxx 后缀，原文件内容不被覆盖。"""
        raw_integration_paths.files_video_misc.mkdir(parents=True, exist_ok=True)
        (raw_integration_paths.files_video_misc / "hello.mp4").write_bytes(b"original")

        (raw_integration_paths.inbox / "hello.mp4").write_bytes(b"incoming")

        raw_pipeline_with_real_repo.run(dry_run=False)

        assert not (raw_integration_paths.inbox / "hello.mp4").exists()

        all_mp4 = list(raw_integration_paths.files_video_misc.glob("hello*.mp4"))
        assert len(all_mp4) == 2, (
            f"期望 2 个文件（原始 + 冲突命名），实际: {[f.name for f in all_mp4]}"
        )
        assert (
            raw_integration_paths.files_video_misc / "hello.mp4"
        ).read_bytes() == b"original", "原始文件内容被覆盖"
        new_files = [f for f in all_mp4 if f.name != "hello.mp4"]
        assert len(new_files) == 1
        assert new_files[0].read_bytes() == b"incoming"

    def test_existing_file_in_dest_not_overwritten_by_inbox_zip(
        self,
        raw_pipeline_with_real_repo: RawFilePipeline,
        raw_integration_paths: RawWorkspacePaths,
    ) -> None:
        """``files_compressed/foo.zip`` 已存在时，inbox/foo.zip 经 phase1→phase3
        落地时应生成 -jfk-xxxx 后缀，原文件内容不被覆盖。"""
        raw_integration_paths.files_compressed.mkdir(parents=True, exist_ok=True)
        (raw_integration_paths.files_compressed / "foo.zip").write_bytes(b"old_zip")

        (raw_integration_paths.inbox / "foo.zip").write_bytes(b"new_zip")

        raw_pipeline_with_real_repo.run(dry_run=False)

        assert not (raw_integration_paths.inbox / "foo.zip").exists()

        all_zip = list(raw_integration_paths.files_compressed.glob("foo*.zip"))
        assert len(all_zip) == 2, (
            f"期望 2 个文件（原始 + 冲突命名），实际: {[f.name for f in all_zip]}"
        )
        assert (
            raw_integration_paths.files_compressed / "foo.zip"
        ).read_bytes() == b"old_zip", "原始文件内容被覆盖"

    def test_existing_dir_in_folders_to_delete_not_overwritten(
        self,
        raw_pipeline_with_real_repo: RawFilePipeline,
        raw_integration_paths: RawWorkspacePaths,
    ) -> None:
        """``folders_to_delete/FC2-PPV`` 已存在时，inbox/FC2-PPV/ 经 phase2.1
        迁入时应生成 -jfk-xxxx 后缀，原目录内容不被覆盖。"""
        raw_integration_paths.folders_to_delete.mkdir(parents=True, exist_ok=True)
        existing = raw_integration_paths.folders_to_delete / "FC2-PPV"
        existing.mkdir()
        (existing / "keep.mp4").write_bytes(b"keep_this")

        junk_dir = raw_integration_paths.inbox / "FC2-PPV"
        junk_dir.mkdir(parents=True)
        (junk_dir / "new.mp4").write_bytes(b"new_content")

        raw_pipeline_with_real_repo.run(dry_run=False)

        assert not junk_dir.exists()

        dirs = [
            p for p in raw_integration_paths.folders_to_delete.iterdir() if p.is_dir()
        ]
        assert len(dirs) == 2, (
            f"期望 2 个目录（原始 + 冲突命名），实际: {[d.name for d in dirs]}"
        )
        assert (existing / "keep.mp4").read_bytes() == b"keep_this", (
            "原始目录内容被覆盖"
        )
