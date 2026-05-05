"""RawFilePipeline 阶段 2 行为单元测试（经 pipeline.run 驱动）。"""

from collections.abc import Callable
from pathlib import Path

import pytest

from j_file_kit.app.file_task.application.raw_analyze_config import RawAnalyzeConfig
from j_file_kit.app.file_task.application.raw_pipeline.pipeline import RawFilePipeline
from j_file_kit.infrastructure.persistence.sqlite.file_task.file_result_repository import (
    FileResultRepositoryImpl,
)

pytestmark = pytest.mark.unit


def test_phase2_keyword_moves_dir_to_folders_to_delete(
    tmp_path: Path,
    file_result_repository: FileResultRepositoryImpl,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
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
        analyze_config=raw_analyze_config_factory(
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
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
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
        analyze_config=raw_analyze_config_factory(
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
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
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
        analyze_config=raw_analyze_config_factory(
            tmp_path,
            files_misc=misc,
            folders_to_delete=None,
        ),
        log_dir=tmp_path / "logs",
        file_result_repository=file_result_repository,
    )
    with pytest.raises(ValueError, match="folders_to_delete"):
        pipe.run()


def test_phase2_clean_deletes_junk_and_removes_empty_root(
    tmp_path: Path,
    file_result_repository: FileResultRepositoryImpl,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
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
        analyze_config=raw_analyze_config_factory(
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
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
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
        analyze_config=raw_analyze_config_factory(
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
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
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
        analyze_config=raw_analyze_config_factory(
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


def test_phase2_raises_when_classification_destinations_unconfigured(
    tmp_path: Path,
    file_result_repository: FileResultRepositoryImpl,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
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
        analyze_config=raw_analyze_config_factory(
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
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
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
        analyze_config=raw_analyze_config_factory(
            tmp_path, files_misc=misc, folders_to_delete=td
        ),
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
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
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
        analyze_config=raw_analyze_config_factory(
            tmp_path, files_misc=misc, folders_to_delete=td
        ),
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
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
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
        analyze_config=raw_analyze_config_factory(
            tmp_path, files_misc=misc, folders_to_delete=td
        ),
        log_dir=tmp_path / "logs",
        file_result_repository=file_result_repository,
    )
    stats = pipe.run()

    assert (misc / "episode.mp4").exists()
    assert stats.phase2_flattened_files == 1


def test_phase2_whole_dir_nested_images_to_pic(
    tmp_path: Path,
    file_result_repository: FileResultRepositoryImpl,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
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
        analyze_config=raw_analyze_config_factory(
            tmp_path, files_misc=misc, folders_to_delete=td
        ),
        log_dir=tmp_path / "logs",
        file_result_repository=file_result_repository,
    )
    stats = pipe.run()

    assert stats.phase2_moved_to_pic_dirs == 1
    pic_root = tmp_path / "folders_pic" / "vacation"
    assert pic_root.is_dir()
    assert (pic_root / "deep" / "x.jpg").exists()
