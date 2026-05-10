"""Phase2 冲突消解安全性测试

验证 Phase2 各子阶段在目标路径已存在同名文件/目录时，
不会发生静默覆盖，原有内容得到完整保留。
"""

import threading
from collections.abc import Callable
from pathlib import Path

import pytest

from j_file_kit.app.file_task.application.raw_analyze_config import RawAnalyzeConfig
from j_file_kit.app.file_task.application.raw_pipeline.context import PhaseContext
from j_file_kit.app.file_task.application.raw_pipeline.counters import RawPhaseCounters
from j_file_kit.app.file_task.application.raw_pipeline.phase2_classify import (
    flatten_dir_into_misc,
    run_phase2_classify,
)
from j_file_kit.app.file_task.application.raw_pipeline.phase2_delete_move import (
    move_dir_to_delete,
)
from j_file_kit.app.file_task.application.raw_pipeline.pipeline import RawFilePipeline

pytestmark = pytest.mark.unit


class TestPhase21MoveToDeleteConflict:
    """Phase2.1：同名目录迁入 folders_to_delete 时不覆盖已有目录。"""

    def test_conflict_dir_gets_suffix_original_preserved(
        self,
        tmp_path: Path,
        raw_pipeline_factory: Callable[..., RawFilePipeline],
    ) -> None:
        """已有 folders_to_delete/FC2-PPV-pack/ 时，新同名目录应以 -jfk-xxxx 落地，
        原目录内容完整保留，不被覆盖。"""
        pipeline = raw_pipeline_factory(run_id=1)

        folders_to_delete = tmp_path / "folders_to_delete"
        existing_dir = folders_to_delete / "FC2-PPV-pack"
        existing_dir.mkdir(parents=True, exist_ok=True)
        (existing_dir / "old_video.mp4").write_text("original_content")

        inbox_dir = tmp_path / "inbox" / "FC2-PPV-pack"
        inbox_dir.mkdir(parents=True, exist_ok=True)
        (inbox_dir / "new_video.mp4").write_text("new_content")

        pipeline.run(dry_run=False)

        dirs_in_delete = [p for p in folders_to_delete.iterdir() if p.is_dir()]
        assert len(dirs_in_delete) == 2, (
            f"期望 2 个目录（原始 + 冲突命名），实际: {[d.name for d in dirs_in_delete]}"
        )

        assert (existing_dir / "old_video.mp4").read_text() == "original_content", (
            "原始目录内容被覆盖"
        )

        new_videos = [f for f in folders_to_delete.rglob("new_video.mp4")]
        assert len(new_videos) == 1, "新目录的文件未迁移成功"
        assert new_videos[0].read_text() == "new_content"

    def test_direct_move_dir_to_delete_conflict(
        self,
        tmp_path: Path,
        raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
        phase_context_factory: Callable[[RawAnalyzeConfig], PhaseContext],
    ) -> None:
        """直接调用 move_dir_to_delete：目标已存在时原目录内容完整保留，
        新目录以 -jfk-xxxx 后缀落地。"""
        config = raw_analyze_config_factory(tmp_path)

        dest_delete = config.folders_to_delete
        dest_delete.mkdir(parents=True, exist_ok=True)
        existing = dest_delete / "collision_dir"
        existing.mkdir()
        (existing / "kept.txt").write_text("kept")

        src = tmp_path / "collision_dir"
        src.mkdir()
        (src / "new.txt").write_text("new")

        phases = RawPhaseCounters()
        move_dir_to_delete(
            phase_context_factory(config),
            src,
            phases,
            dest_delete=dest_delete,
            dry_run=False,
        )

        assert phases.phase2_moved_to_delete_dirs == 1
        assert not src.exists(), "源目录应已被移走"

        dirs = [p for p in dest_delete.iterdir() if p.is_dir()]
        assert len(dirs) == 2, f"期望 2 个目录，实际: {[d.name for d in dirs]}"
        assert (existing / "kept.txt").read_text() == "kept", "原目录内容被覆盖"

        new_txts = [f for f in dest_delete.rglob("new.txt")]
        assert len(new_txts) == 1
        assert new_txts[0].read_text() == "new"


class TestPhase24FlattenConflict:
    """Phase2.4 拆解：目标 files_misc 已有同名文件时不覆盖原文件。"""

    def test_flatten_conflict_preserves_existing_misc_file(
        self,
        tmp_path: Path,
        raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
        phase_context_factory: Callable[[RawAnalyzeConfig], PhaseContext],
    ) -> None:
        """flatten_dir_into_misc：files_misc 已有 show_ep01.mp4 时，
        inbox/show/ep01.mp4 以 -jfk-xxxx 后缀迁入，原文件内容完整保留。"""
        files_misc = tmp_path / "files_misc"
        files_misc.mkdir()
        config = raw_analyze_config_factory(tmp_path, files_misc=files_misc)

        (files_misc / "show_ep01.mp4").write_text("existing_content")

        src = tmp_path / "show"
        src.mkdir()
        (src / "ep01.mp4").write_text("new_content")

        phases = RawPhaseCounters()
        cancelled = flatten_dir_into_misc(
            phase_context_factory(config),
            src,
            phases,
            dry_run=False,
            cancellation_event=None,
        )

        assert cancelled is False
        assert phases.phase2_flattened_dirs == 1
        assert not src.exists(), "源目录应已被清空并删除"

        assert (files_misc / "show_ep01.mp4").read_text() == "existing_content", (
            "原始文件内容被覆盖"
        )

        all_mp4 = list(files_misc.glob("show*.mp4"))
        assert len(all_mp4) == 2, (
            f"期望 2 个文件（原始 + 冲突命名），实际: {[f.name for f in all_mp4]}"
        )
        contents = {f.read_text() for f in all_mp4}
        assert contents == {"existing_content", "new_content"}

    def test_flatten_stem_matches_dir_conflict_preserves_existing(
        self,
        tmp_path: Path,
        raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
        phase_context_factory: Callable[[RawAnalyzeConfig], PhaseContext],
    ) -> None:
        """stem 与目录名相同（直接保留文件名）时的冲突：files_misc/movie01.mp4 已存在，
        inbox/movie01/movie01.mp4 不应覆盖原文件。"""
        files_misc = tmp_path / "files_misc"
        files_misc.mkdir()
        config = raw_analyze_config_factory(tmp_path, files_misc=files_misc)

        (files_misc / "movie01.mp4").write_text("original")

        src = tmp_path / "movie01"
        src.mkdir()
        (src / "movie01.mp4").write_text("incoming")

        phases = RawPhaseCounters()
        flatten_dir_into_misc(
            phase_context_factory(config),
            src,
            phases,
            dry_run=False,
            cancellation_event=None,
        )

        assert (files_misc / "movie01.mp4").read_text() == "original", (
            "原始文件内容被覆盖"
        )
        all_mp4 = list(files_misc.glob("movie01*.mp4"))
        assert len(all_mp4) == 2
        contents = {f.read_text() for f in all_mp4}
        assert contents == {"original", "incoming"}


class TestPhase24WholeClassifyConflict:
    """Phase2.4 整目录分类：目标 folders_* 已有同名目录时不覆盖原目录。"""

    def test_whole_video_dir_conflict_preserves_existing(
        self,
        tmp_path: Path,
        raw_pipeline_factory: Callable[..., RawFilePipeline],
    ) -> None:
        """folders_video/my_show/ 已存在时，inbox/my_show/（6 个视频，触发整目录迁移）
        应以 -jfk-xxxx 落地，原目录内容完整保留。"""
        pipeline = raw_pipeline_factory(run_id=10)

        folders_video = tmp_path / "folders_video"
        existing = folders_video / "my_show"
        existing.mkdir(parents=True, exist_ok=True)
        (existing / "old_ep.mp4").write_text("old_content")

        show_dir = tmp_path / "inbox" / "my_show"
        show_dir.mkdir(parents=True)
        for i in range(6):
            (show_dir / f"ep{i:02d}.mp4").write_text(f"new_ep_{i}")

        pipeline.run(dry_run=False)

        assert not show_dir.exists(), "源目录应已被移走"

        dirs = [p for p in folders_video.iterdir() if p.is_dir()]
        assert len(dirs) == 2, (
            f"期望 2 个目录（原始 + 冲突命名），实际: {[d.name for d in dirs]}"
        )

        assert (existing / "old_ep.mp4").read_text() == "old_content", (
            "原始目录内容被覆盖"
        )

        new_eps = [f for f in folders_video.rglob("ep00.mp4")]
        assert len(new_eps) == 1
        assert new_eps[0].read_text() == "new_ep_0"

    def test_whole_dir_classify_conflict_via_run_phase2_classify(
        self,
        tmp_path: Path,
        raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
        phase_context_factory: Callable[[RawAnalyzeConfig], PhaseContext],
    ) -> None:
        """直接调用 run_phase2_classify：folders_pic/album 已存在时，
        新同名图片目录以 -jfk-xxxx 落地，原目录内容完整保留。

        含子目录使 should_flatten_small_dir 返回 False，从而走整目录迁移分支。
        """
        config = raw_analyze_config_factory(tmp_path)

        existing = config.folders_pic / "album"
        existing.mkdir(parents=True, exist_ok=True)
        (existing / "original.jpg").write_text("old_photo")

        src = tmp_path / "album"
        src.mkdir()
        (src / "new_photo.jpg").write_text("new_photo")
        # 含子目录：should_flatten_small_dir 返回 False，走整目录迁移分支
        (src / "sub").mkdir()
        (src / "sub" / "extra.jpg").write_text("extra")

        phases = RawPhaseCounters()
        run_phase2_classify(
            phase_context_factory(config),
            src,
            phases,
            dry_run=False,
            cancellation_event=threading.Event(),
        )

        assert not src.exists(), "源目录应已被移走"

        dirs = [p for p in config.folders_pic.iterdir() if p.is_dir()]
        assert len(dirs) == 2, (
            f"期望 2 个目录（原始 + 冲突命名），实际: {[d.name for d in dirs]}"
        )
        assert (existing / "original.jpg").read_text() == "old_photo", (
            "原始目录内容被覆盖"
        )
        new_photos = [f for f in config.folders_pic.rglob("new_photo.jpg")]
        assert len(new_photos) == 1
        assert new_photos[0].read_text() == "new_photo"
