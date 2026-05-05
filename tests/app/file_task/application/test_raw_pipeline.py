"""RawFilePipeline 三阶段行为单元测试。"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from j_file_kit.app.file_task.application.file_ops import (
    JFK_CONFLICT_STEM_SUFFIX_BYTES,
    MAX_FILENAME_BYTES,
)
from j_file_kit.app.file_task.application.raw_analyze_config import RawAnalyzeConfig
from j_file_kit.app.file_task.application.raw_pipeline.pipeline import RawFilePipeline
from j_file_kit.app.file_task.domain.task_run import FileTaskRunStatistics
from j_file_kit.infrastructure.persistence.sqlite.file_task.file_result_repository import (
    FileResultRepositoryImpl,
)

pytestmark = pytest.mark.unit


def _empty_repo_stats() -> dict[str, float | int]:
    return {
        "total_items": 0,
        "success_items": 0,
        "error_items": 0,
        "skipped_items": 0,
        "warning_items": 0,
        "total_duration_ms": 0.0,
    }


def _raw_cfg(
    tmp_path: Path,
    *,
    files_misc: Path | None,
    folders_to_delete: Path | None = None,
    with_classification_destinations: bool = True,
) -> RawAnalyzeConfig:
    _ = tmp_path
    fp = fa = fc = fv = fm = None
    if with_classification_destinations:
        fp = tmp_path / "folders_pic"
        fa = tmp_path / "folders_audio"
        fc = tmp_path / "folders_compressed"
        fv = tmp_path / "folders_video"
        fm = tmp_path / "folders_misc"
        for p in (fp, fa, fc, fv, fm):
            p.mkdir(parents=True, exist_ok=True)
    return RawAnalyzeConfig(
        folders_to_delete=folders_to_delete,
        folders_video=fv,
        folders_compressed=fc,
        folders_pic=fp,
        folders_audio=fa,
        folders_misc=fm,
        files_video_jav=None,
        files_video_us=None,
        files_video_vr=None,
        files_video_movie=None,
        files_video_misc=None,
        files_compressed=None,
        files_pic=None,
        files_audio=None,
        files_misc=files_misc,
        video_extensions={".mp4"},
        image_extensions={".jpg", ".jpeg", ".png"},
        subtitle_extensions={".srt"},
        archive_extensions={".zip"},
        audio_extensions={".mp3"},
    )


def test_run_empty_inbox_mock_repo(tmp_path: Path) -> None:
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    repo = MagicMock()
    repo.get_statistics.return_value = _empty_repo_stats()
    pipe = RawFilePipeline(
        run_id=1,
        run_name="raw_file_organizer",
        scan_root=inbox,
        analyze_config=_raw_cfg(tmp_path, files_misc=tmp_path / "misc"),
        log_dir=tmp_path / "logs",
        file_result_repository=repo,
    )
    stats = pipe.run()
    assert stats == FileTaskRunStatistics()
    repo.save_result.assert_not_called()


def test_phase1_moves_level1_file_only(
    tmp_path: Path,
    file_result_repository: FileResultRepositoryImpl,
) -> None:
    inbox = tmp_path / "inbox"
    misc = tmp_path / "files_misc"
    inbox.mkdir()
    misc.mkdir()
    sub = inbox / "nested"
    sub.mkdir()
    (sub / "inner.mp4").write_text("in")
    (inbox / "root.txt").write_text("root")

    pipe = RawFilePipeline(
        run_id=42,
        run_name="raw_file_organizer",
        scan_root=inbox,
        analyze_config=_raw_cfg(tmp_path, files_misc=misc),
        log_dir=tmp_path / "logs",
        file_result_repository=file_result_repository,
    )
    stats = pipe.run()

    assert (misc / "root.txt").exists()
    assert (misc / "root.txt").read_text() == "root"
    assert not (inbox / "root.txt").exists()
    assert (misc / "nested_inner.mp4").exists()
    assert not sub.exists()

    assert stats.phase1_seen_files == 1
    assert stats.phase1_moved_files == 1
    assert stats.phase1_error_files == 0
    assert stats.phase2_seen_dirs == 1
    assert stats.phase2_flattened_dirs == 1
    assert stats.phase2_flattened_files == 1
    assert stats.phase2_moved_to_delete_dirs == 0
    assert stats.phase3_seen_files_misc == 2
    assert stats.phase3_deferred_files_misc == 2
    assert stats.total_items >= 1


def test_phase1_conflict_resolution(
    tmp_path: Path,
    file_result_repository: FileResultRepositoryImpl,
) -> None:
    inbox = tmp_path / "inbox"
    misc = tmp_path / "files_misc"
    inbox.mkdir()
    misc.mkdir()
    (misc / "dup.txt").write_text("old")
    (inbox / "dup.txt").write_text("new")

    pipe = RawFilePipeline(
        run_id=7,
        run_name="raw_file_organizer",
        scan_root=inbox,
        analyze_config=_raw_cfg(tmp_path, files_misc=misc),
        log_dir=tmp_path / "logs",
        file_result_repository=file_result_repository,
    )
    stats = pipe.run()

    assert not (inbox / "dup.txt").exists()
    moved = list(misc.glob("dup*.txt"))
    assert len(moved) == 2
    contents = {p.read_text() for p in moved}
    assert contents == {"old", "new"}
    assert stats.phase1_moved_files == 1


def test_phase1_truncates_long_but_fs_valid_filename(
    tmp_path: Path,
    file_result_repository: FileResultRepositoryImpl,
) -> None:
    inbox = tmp_path / "inbox"
    misc = tmp_path / "files_misc"
    inbox.mkdir()
    misc.mkdir()
    # APFS 单分量文件名 UTF-8 须 ≤255 字节；此处 246+4=250，仍触发预留冲突后缀的裁剪
    long_name = "y" * 246 + ".dat"
    assert len(long_name.encode()) == 250
    (inbox / long_name).write_text("x")

    pipe = RawFilePipeline(
        run_id=3,
        run_name="raw_file_organizer",
        scan_root=inbox,
        analyze_config=_raw_cfg(tmp_path, files_misc=misc),
        log_dir=tmp_path / "logs",
        file_result_repository=file_result_repository,
    )
    stats = pipe.run()

    assert stats.phase1_moved_files == 1
    remaining = list(misc.iterdir())
    assert len(remaining) == 1
    assert (
        len(remaining[0].name.encode())
        <= MAX_FILENAME_BYTES - JFK_CONFLICT_STEM_SUFFIX_BYTES
    )


def test_dry_run_does_not_move(
    tmp_path: Path,
    file_result_repository: FileResultRepositoryImpl,
) -> None:
    inbox = tmp_path / "inbox"
    misc = tmp_path / "files_misc"
    inbox.mkdir()
    misc.mkdir()
    (inbox / "keep.txt").write_text("data")

    pipe = RawFilePipeline(
        run_id=9,
        run_name="raw_file_organizer",
        scan_root=inbox,
        analyze_config=_raw_cfg(tmp_path, files_misc=misc),
        log_dir=tmp_path / "logs",
        file_result_repository=file_result_repository,
    )
    stats = pipe.run(dry_run=True)

    assert (inbox / "keep.txt").exists()
    assert list(misc.iterdir()) == []
    assert stats.phase1_moved_files == 1
    assert stats.success_items >= 1


def test_phase2_keyword_moves_dir_to_folders_to_delete(
    tmp_path: Path,
    file_result_repository: FileResultRepositoryImpl,
) -> None:
    inbox = tmp_path / "inbox"
    misc = tmp_path / "files_misc"
    td = tmp_path / "folders_to_delete"
    inbox.mkdir()
    misc.mkdir()
    td.mkdir()
    d = inbox / "something-FC2-PPV-xyz"
    d.mkdir()
    (d / "kept.mp4").write_text("vid")

    pipe = RawFilePipeline(
        run_id=11,
        run_name="raw_file_organizer",
        scan_root=inbox,
        analyze_config=_raw_cfg(
            tmp_path,
            files_misc=misc,
            folders_to_delete=td,
        ),
        log_dir=tmp_path / "logs",
        file_result_repository=file_result_repository,
    )
    stats = pipe.run()

    assert not (inbox / "something-FC2-PPV-xyz").exists()
    dest_dirs = [p for p in td.iterdir() if p.is_dir()]
    assert len(dest_dirs) == 1
    assert (dest_dirs[0] / "kept.mp4").read_text() == "vid"
    assert stats.phase2_moved_to_delete_dirs == 1
    assert stats.phase2_removed_dirs == 0


def test_phase2_keyword_moves_dir_case_insensitive(
    tmp_path: Path,
    file_result_repository: FileResultRepositoryImpl,
) -> None:
    inbox = tmp_path / "inbox"
    misc = tmp_path / "files_misc"
    td = tmp_path / "folders_to_delete"
    inbox.mkdir()
    misc.mkdir()
    td.mkdir()
    d = inbox / "fc2-ppv-pack"
    d.mkdir()
    (d / "a.txt").write_text("x")

    pipe = RawFilePipeline(
        run_id=22,
        run_name="raw_file_organizer",
        scan_root=inbox,
        analyze_config=_raw_cfg(
            tmp_path,
            files_misc=misc,
            folders_to_delete=td,
        ),
        log_dir=tmp_path / "logs",
        file_result_repository=file_result_repository,
    )
    stats = pipe.run()
    assert stats.phase2_moved_to_delete_dirs == 1
    assert not d.exists()


def test_phase2_raises_when_keyword_hit_but_folders_to_delete_unset(
    tmp_path: Path,
    file_result_repository: FileResultRepositoryImpl,
) -> None:
    inbox = tmp_path / "inbox"
    misc = tmp_path / "files_misc"
    inbox.mkdir()
    misc.mkdir()
    d = inbox / "FC2-PPV-only"
    d.mkdir()
    (d / "a.txt").write_text("x")

    pipe = RawFilePipeline(
        run_id=55,
        run_name="raw_file_organizer",
        scan_root=inbox,
        analyze_config=_raw_cfg(tmp_path, files_misc=misc, folders_to_delete=None),
        log_dir=tmp_path / "logs",
        file_result_repository=file_result_repository,
    )
    with pytest.raises(ValueError, match="folders_to_delete"):
        pipe.run()


def test_phase2_clean_deletes_junk_and_removes_empty_root(
    tmp_path: Path,
    file_result_repository: FileResultRepositoryImpl,
) -> None:
    inbox = tmp_path / "inbox"
    misc = tmp_path / "files_misc"
    td = tmp_path / "folders_to_delete"
    inbox.mkdir()
    misc.mkdir()
    td.mkdir()
    d = inbox / "junk_root"
    d.mkdir()
    (d / "note.txt").write_text("rm")
    (d / "preview_release.mp4").write_text("junk stem")
    (d / "zero.mp4").write_bytes(b"")

    pipe = RawFilePipeline(
        run_id=33,
        run_name="raw_file_organizer",
        scan_root=inbox,
        analyze_config=_raw_cfg(
            tmp_path,
            files_misc=misc,
            folders_to_delete=td,
        ),
        log_dir=tmp_path / "logs",
        file_result_repository=file_result_repository,
    )
    stats = pipe.run()

    assert not d.exists()
    assert stats.phase2_cleaned_deleted_files >= 3
    assert stats.phase2_removed_dirs == 1


def test_phase2_clean_keeps_non_junk_then_flattens_small_video_dir(
    tmp_path: Path,
    file_result_repository: FileResultRepositoryImpl,
) -> None:
    inbox = tmp_path / "inbox"
    misc = tmp_path / "files_misc"
    td = tmp_path / "folders_to_delete"
    inbox.mkdir()
    misc.mkdir()
    td.mkdir()
    d = inbox / "keep_dir"
    d.mkdir()
    (d / "video.mp4").write_text("full")
    (d / "junk.txt").write_text("bye")

    pipe = RawFilePipeline(
        run_id=44,
        run_name="raw_file_organizer",
        scan_root=inbox,
        analyze_config=_raw_cfg(
            tmp_path,
            files_misc=misc,
            folders_to_delete=td,
        ),
        log_dir=tmp_path / "logs",
        file_result_repository=file_result_repository,
    )
    stats = pipe.run()

    assert not d.exists()
    assert (misc / "keep_dir_video.mp4").exists()
    assert stats.phase2_cleaned_deleted_files == 1
    assert stats.phase2_flattened_dirs == 1
    assert stats.phase2_flattened_files == 1
    assert stats.phase2_removed_dirs == 1


def test_phase2_dry_run_count_without_deleting_dir_contents(
    tmp_path: Path,
    file_result_repository: FileResultRepositoryImpl,
) -> None:
    inbox = tmp_path / "inbox"
    misc = tmp_path / "files_misc"
    td = tmp_path / "folders_to_delete"
    inbox.mkdir()
    misc.mkdir()
    td.mkdir()
    d = inbox / "trash"
    d.mkdir()
    (d / "x.txt").write_text("stay")

    pipe = RawFilePipeline(
        run_id=66,
        run_name="raw_file_organizer",
        scan_root=inbox,
        analyze_config=_raw_cfg(
            tmp_path,
            files_misc=misc,
            folders_to_delete=td,
        ),
        log_dir=tmp_path / "logs",
        file_result_repository=file_result_repository,
    )
    stats = pipe.run(dry_run=True)

    assert (d / "x.txt").exists()
    assert stats.phase2_cleaned_deleted_files == 1
    assert stats.phase2_moved_to_misc_dirs == 1


def test_phase2_collapses_single_chain_directory(
    tmp_path: Path,
    file_result_repository: FileResultRepositoryImpl,
) -> None:
    inbox = tmp_path / "inbox"
    misc = tmp_path / "files_misc"
    td = tmp_path / "folders_to_delete"
    inbox.mkdir()
    misc.mkdir()
    td.mkdir()
    root = inbox / "abc"
    root.mkdir()
    (root / "def").mkdir()
    (root / "def" / "ghi").mkdir()
    (root / "def" / "ghi" / "clip.mp4").write_text("vid")

    pipe = RawFilePipeline(
        run_id=101,
        run_name="raw_file_organizer",
        scan_root=inbox,
        analyze_config=_raw_cfg(
            tmp_path,
            files_misc=misc,
            folders_to_delete=td,
        ),
        log_dir=tmp_path / "logs",
        file_result_repository=file_result_repository,
    )
    stats = pipe.run()

    assert (misc / "abc_def_ghi_clip.mp4").exists()
    assert not (inbox / "abc_def_ghi").exists()
    assert not root.exists()
    assert stats.phase2_collapsed_chain_dirs == 1
    assert stats.phase2_skipped_collapse_dirs == 0
    assert stats.phase2_flattened_dirs == 1
    assert stats.phase2_flattened_files == 1


def test_phase2_collapse_renames_on_destination_conflict(
    tmp_path: Path,
    file_result_repository: FileResultRepositoryImpl,
) -> None:
    inbox = tmp_path / "inbox"
    misc = tmp_path / "files_misc"
    td = tmp_path / "folders_to_delete"
    inbox.mkdir()
    misc.mkdir()
    td.mkdir()
    (inbox / "abc_def_ghi").mkdir()

    root = inbox / "abc"
    root.mkdir()
    (root / "def").mkdir()
    (root / "def" / "ghi").mkdir()
    (root / "def" / "ghi" / "clip.mp4").write_text("vid")

    pipe = RawFilePipeline(
        run_id=102,
        run_name="raw_file_organizer",
        scan_root=inbox,
        analyze_config=_raw_cfg(
            tmp_path,
            files_misc=misc,
            folders_to_delete=td,
        ),
        log_dir=tmp_path / "logs",
        file_result_repository=file_result_repository,
    )
    stats = pipe.run()

    assert stats.phase2_collapsed_chain_dirs == 1
    assert stats.phase2_skipped_collapse_dirs == 0
    assert stats.phase2_flattened_dirs == 1
    dest_files = [p for p in misc.iterdir() if p.is_file()]
    assert len(dest_files) == 1
    assert dest_files[0].suffix == ".mp4"
    assert "-jfk-" in dest_files[0].stem or dest_files[0].stem.startswith("abc_def_ghi")
    assert dest_files[0].read_text() == "vid"
    assert not root.exists()


def test_phase2_collapse_skips_when_merge_budget_impossible(
    tmp_path: Path,
    file_result_repository: FileResultRepositoryImpl,
) -> None:
    inbox = tmp_path / "inbox"
    misc = tmp_path / "files_misc"
    td = tmp_path / "folders_to_delete"
    inbox.mkdir()
    misc.mkdir()
    td.mkdir()

    name_seg = "n" * 9
    root = inbox / name_seg
    root.mkdir()
    cur = root
    for _ in range(34):
        nxt = cur / name_seg
        nxt.mkdir()
        cur = nxt
    (cur / "z.mp4").write_text("p")

    pipe = RawFilePipeline(
        run_id=103,
        run_name="raw_file_organizer",
        scan_root=inbox,
        analyze_config=_raw_cfg(
            tmp_path,
            files_misc=misc,
            folders_to_delete=td,
        ),
        log_dir=tmp_path / "logs",
        file_result_repository=file_result_repository,
    )
    stats = pipe.run()

    assert stats.phase2_collapsed_chain_dirs == 0
    assert stats.phase2_skipped_collapse_dirs == 1
    assert not root.exists()
    assert stats.phase2_moved_to_video_dirs == 1
    fv = tmp_path / "folders_video"
    moved_roots = list(fv.iterdir())
    assert len(moved_roots) == 1
    assert list(moved_roots[0].rglob("z.mp4"))


def test_phase2_collapse_dry_run_counts_only(
    tmp_path: Path,
    file_result_repository: FileResultRepositoryImpl,
) -> None:
    inbox = tmp_path / "inbox"
    misc = tmp_path / "files_misc"
    td = tmp_path / "folders_to_delete"
    inbox.mkdir()
    misc.mkdir()
    td.mkdir()
    root = inbox / "abc"
    root.mkdir()
    (root / "def").mkdir()
    (root / "def" / "ghi").mkdir()
    (root / "def" / "ghi" / "clip.mp4").write_text("vid")

    pipe = RawFilePipeline(
        run_id=104,
        run_name="raw_file_organizer",
        scan_root=inbox,
        analyze_config=_raw_cfg(
            tmp_path,
            files_misc=misc,
            folders_to_delete=td,
        ),
        log_dir=tmp_path / "logs",
        file_result_repository=file_result_repository,
    )
    stats = pipe.run(dry_run=True)

    assert root.exists()
    assert (root / "def" / "ghi" / "clip.mp4").exists()
    assert stats.phase2_collapsed_chain_dirs == 1
    assert stats.phase2_moved_to_video_dirs == 1


def test_phase2_raises_when_classification_destinations_unconfigured(
    tmp_path: Path,
    file_result_repository: FileResultRepositoryImpl,
) -> None:
    inbox = tmp_path / "inbox"
    misc = tmp_path / "files_misc"
    inbox.mkdir()
    misc.mkdir()
    d = inbox / "needs_buckets"
    d.mkdir()
    (d / "a.mp4").write_text("v")

    pipe = RawFilePipeline(
        run_id=200,
        run_name="raw_file_organizer",
        scan_root=inbox,
        analyze_config=_raw_cfg(
            tmp_path,
            files_misc=misc,
            with_classification_destinations=False,
        ),
        log_dir=tmp_path / "logs",
        file_result_repository=file_result_repository,
    )
    with pytest.raises(ValueError, match="阶段2.4"):
        pipe.run()


def test_phase2_flatten_video_plus_cover_jpg(
    tmp_path: Path,
    file_result_repository: FileResultRepositoryImpl,
) -> None:
    inbox = tmp_path / "inbox"
    misc = tmp_path / "files_misc"
    td = tmp_path / "folders_to_delete"
    inbox.mkdir()
    misc.mkdir()
    td.mkdir()
    rel = inbox / "release"
    rel.mkdir()
    (rel / "cover.jpg").write_text("img")
    (rel / "main.mp4").write_text("vid")

    pipe = RawFilePipeline(
        run_id=201,
        run_name="raw_file_organizer",
        scan_root=inbox,
        analyze_config=_raw_cfg(tmp_path, files_misc=misc, folders_to_delete=td),
        log_dir=tmp_path / "logs",
        file_result_repository=file_result_repository,
    )
    stats = pipe.run()

    assert not rel.exists()
    assert (misc / "release_cover.jpg").exists()
    assert (misc / "release_main.mp4").exists()
    assert stats.phase2_flattened_dirs == 1
    assert stats.phase2_flattened_files == 2


def test_phase2_flatten_skipped_when_more_than_five_files(
    tmp_path: Path,
    file_result_repository: FileResultRepositoryImpl,
) -> None:
    inbox = tmp_path / "inbox"
    misc = tmp_path / "files_misc"
    td = tmp_path / "folders_to_delete"
    inbox.mkdir()
    misc.mkdir()
    td.mkdir()
    pack = inbox / "sixpack"
    pack.mkdir()
    for i in range(6):
        (pack / f"{i}.mp4").write_text("x")

    pipe = RawFilePipeline(
        run_id=202,
        run_name="raw_file_organizer",
        scan_root=inbox,
        analyze_config=_raw_cfg(tmp_path, files_misc=misc, folders_to_delete=td),
        log_dir=tmp_path / "logs",
        file_result_repository=file_result_repository,
    )
    stats = pipe.run()

    assert stats.phase2_flattened_dirs == 0
    assert stats.phase2_moved_to_video_dirs == 1
    fv = tmp_path / "folders_video"
    assert len(list(fv.iterdir())) == 1


def test_phase2_flatten_preserves_name_when_stem_matches_dir(
    tmp_path: Path,
    file_result_repository: FileResultRepositoryImpl,
) -> None:
    inbox = tmp_path / "inbox"
    misc = tmp_path / "files_misc"
    td = tmp_path / "folders_to_delete"
    inbox.mkdir()
    misc.mkdir()
    td.mkdir()
    d = inbox / "episode"
    d.mkdir()
    (d / "episode.mp4").write_text("z")

    pipe = RawFilePipeline(
        run_id=203,
        run_name="raw_file_organizer",
        scan_root=inbox,
        analyze_config=_raw_cfg(tmp_path, files_misc=misc, folders_to_delete=td),
        log_dir=tmp_path / "logs",
        file_result_repository=file_result_repository,
    )
    stats = pipe.run()

    assert (misc / "episode.mp4").exists()
    assert stats.phase2_flattened_files == 1


def test_phase2_whole_dir_nested_images_to_pic(
    tmp_path: Path,
    file_result_repository: FileResultRepositoryImpl,
) -> None:
    inbox = tmp_path / "inbox"
    misc = tmp_path / "files_misc"
    td = tmp_path / "folders_to_delete"
    inbox.mkdir()
    misc.mkdir()
    td.mkdir()
    album = inbox / "vacation"
    album.mkdir()
    (album / "a.jpg").write_text("a")
    (album / "deep").mkdir()
    (album / "deep" / "x.jpg").write_text("p")

    pipe = RawFilePipeline(
        run_id=204,
        run_name="raw_file_organizer",
        scan_root=inbox,
        analyze_config=_raw_cfg(tmp_path, files_misc=misc, folders_to_delete=td),
        log_dir=tmp_path / "logs",
        file_result_repository=file_result_repository,
    )
    stats = pipe.run()

    assert stats.phase2_moved_to_pic_dirs == 1
    pic_root = tmp_path / "folders_pic" / "vacation"
    assert pic_root.is_dir()
    assert (pic_root / "deep" / "x.jpg").exists()
