"""phase2 目录级分类行为测试。"""

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
from j_file_kit.app.file_task.application.raw_pipeline.pipeline import RawFilePipeline

pytestmark = pytest.mark.unit


def test_flatten_skipped_when_more_than_five_files(
    tmp_path: Path,
    raw_pipeline_factory: Callable[..., RawFilePipeline],
) -> None:
    inbox = tmp_path / "inbox"
    source_dir = inbox / "sixpack"
    source_dir.mkdir(parents=True)
    for idx in range(6):
        (source_dir / f"{idx}.mp4").write_text("x")

    stats = raw_pipeline_factory(run_id=202).run()

    assert stats.phase2_flattened_dirs == 0
    assert stats.phase2_moved_to_video_dirs == 1
    folders_video = tmp_path / "folders_video"
    assert len(list(folders_video.iterdir())) == 1


def test_whole_nested_image_dir_moved_to_pic(
    tmp_path: Path,
    raw_pipeline_factory: Callable[..., RawFilePipeline],
) -> None:
    inbox = tmp_path / "inbox"
    album = inbox / "vacation"
    album.mkdir(parents=True)
    (album / "a.jpg").write_text("a")
    (album / "deep").mkdir()
    (album / "deep" / "x.jpg").write_text("p")

    stats = raw_pipeline_factory(run_id=204).run()

    assert stats.phase2_moved_to_pic_dirs == 1
    pic_root = tmp_path / "folders_pic" / "vacation"
    assert pic_root.is_dir()
    assert (pic_root / "deep" / "x.jpg").exists()


# --- 整目录按媒体画像分类（直接调用 run_phase2_classify，避开 pipeline 的 collapse / phase3） ---


def test_whole_audio_nested_dir_routed_to_audio(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
    phase_context_factory: Callable[[RawAnalyzeConfig], PhaseContext],
) -> None:
    # 含子目录 → 走整目录分类分支；扩展名命中 fixture 中的 audio_extensions ({".mp3"})
    config = raw_analyze_config_factory(tmp_path)
    src = tmp_path / "songs"
    src.mkdir()
    (src / "a.mp3").write_text("a")
    (src / "deep").mkdir()
    (src / "deep" / "b.mp3").write_text("b")

    phases = RawPhaseCounters()
    cancelled = run_phase2_classify(
        phase_context_factory(config),
        src,
        phases,
        dry_run=False,
        cancellation_event=None,
    )
    assert cancelled is False
    assert phases.phase2_moved_to_audio_dirs == 1
    audio_root = config.folders_audio / "songs"
    assert audio_root.is_dir()
    assert (audio_root / "deep" / "b.mp3").exists()


def test_whole_compressed_nested_dir_routed_to_compressed(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
    phase_context_factory: Callable[[RawAnalyzeConfig], PhaseContext],
) -> None:
    # 含子目录 → 整目录分类；扩展名命中 fixture 的 archive_extensions ({".zip"})
    config = raw_analyze_config_factory(tmp_path)
    src = tmp_path / "downloads"
    src.mkdir()
    (src / "a.zip").write_text("z")
    (src / "more").mkdir()
    (src / "more" / "b.zip").write_text("r")

    phases = RawPhaseCounters()
    cancelled = run_phase2_classify(
        phase_context_factory(config),
        src,
        phases,
        dry_run=False,
        cancellation_event=None,
    )
    assert cancelled is False
    assert phases.phase2_moved_to_compressed_dirs == 1
    compressed_root = config.folders_compressed / "downloads"
    assert compressed_root.is_dir()
    assert (compressed_root / "more" / "b.zip").exists()


def test_whole_unknown_nested_dir_routed_to_misc(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
    phase_context_factory: Callable[[RawAnalyzeConfig], PhaseContext],
) -> None:
    # 全部为未知扩展名 → kinds={"unknown"} → fallback misc 桶
    config = raw_analyze_config_factory(tmp_path)
    src = tmp_path / "weirdpack"
    src.mkdir()
    (src / "a.txt").write_text("t")
    (src / "sub").mkdir()
    (src / "sub" / "b.xyz").write_text("u")

    phases = RawPhaseCounters()
    cancelled = run_phase2_classify(
        phase_context_factory(config),
        src,
        phases,
        dry_run=False,
        cancellation_event=None,
    )
    assert cancelled is False
    assert phases.phase2_moved_to_misc_dirs == 1
    misc_root = config.folders_misc / "weirdpack"
    assert misc_root.is_dir()
    assert (misc_root / "sub" / "b.xyz").exists()


# --- 单层目录拆解（flatten）行为：直接调用 flatten_dir_into_misc ---


def test_flatten_dir_moves_files_with_dir_prefix(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
    phase_context_factory: Callable[[RawAnalyzeConfig], PhaseContext],
) -> None:
    # 单层 2 个 mp4 且 stem 不同于目录名 → files_misc/{dir}_{stem}{suffix}
    files_misc = tmp_path / "files_misc"
    files_misc.mkdir()
    config = raw_analyze_config_factory(tmp_path, files_misc=files_misc)

    src = tmp_path / "duo"
    src.mkdir()
    (src / "a.mp4").write_text("a")
    (src / "b.mp4").write_text("b")

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
    assert phases.phase2_flattened_files == 2
    assert phases.phase2_removed_dirs == 1
    assert not src.exists()
    assert (files_misc / "duo_a.mp4").read_text() == "a"
    assert (files_misc / "duo_b.mp4").read_text() == "b"


def test_flatten_dir_keeps_basename_when_stem_matches_dir(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
    phase_context_factory: Callable[[RawAnalyzeConfig], PhaseContext],
) -> None:
    # stem 与目录名相同时，文件直接保留 path.name 而非加 dir_ 前缀
    files_misc = tmp_path / "files_misc"
    files_misc.mkdir()
    config = raw_analyze_config_factory(tmp_path, files_misc=files_misc)

    src = tmp_path / "movie01"
    src.mkdir()
    (src / "movie01.mp4").write_text("v")

    phases = RawPhaseCounters()
    flatten_dir_into_misc(
        phase_context_factory(config),
        src,
        phases,
        dry_run=False,
        cancellation_event=None,
    )
    assert (files_misc / "movie01.mp4").read_text() == "v"
    assert not (files_misc / "movie01_movie01.mp4").exists()
    assert not src.exists()


def test_flatten_dry_run_increments_counters_without_moving(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
    phase_context_factory: Callable[[RawAnalyzeConfig], PhaseContext],
) -> None:
    files_misc = tmp_path / "files_misc"
    files_misc.mkdir()
    config = raw_analyze_config_factory(tmp_path, files_misc=files_misc)

    src = tmp_path / "duo_dry"
    src.mkdir()
    (src / "a.mp4").write_text("a")
    (src / "b.mp4").write_text("b")

    phases = RawPhaseCounters()
    cancelled = flatten_dir_into_misc(
        phase_context_factory(config),
        src,
        phases,
        dry_run=True,
        cancellation_event=None,
    )
    assert cancelled is False
    assert phases.phase2_flattened_dirs == 1
    assert phases.phase2_flattened_files == 2
    # 文件未移动，原目录保留
    assert (src / "a.mp4").exists()
    assert (src / "b.mp4").exists()
    assert list(files_misc.iterdir()) == []


# --- 取消事件 ---


def test_flatten_cancellation_returns_true_during_file_loop(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
    phase_context_factory: Callable[[RawAnalyzeConfig], PhaseContext],
) -> None:
    # cancellation_event 在循环开始前已被 set，第一次循环检查即返回 True
    files_misc = tmp_path / "files_misc"
    files_misc.mkdir()
    config = raw_analyze_config_factory(tmp_path, files_misc=files_misc)

    src = tmp_path / "small_album"
    src.mkdir()
    (src / "a.mp4").write_text("v")
    (src / "b.mp4").write_text("v")

    phases = RawPhaseCounters()
    event = threading.Event()
    event.set()

    cancelled = flatten_dir_into_misc(
        phase_context_factory(config),
        src,
        phases,
        dry_run=False,
        cancellation_event=event,
    )
    assert cancelled is True
    # 目录与文件都应保留（循环开始即被取消，未触发 rmdir）
    assert src.exists()
    assert (src / "a.mp4").exists()
    assert (src / "b.mp4").exists()


def test_flatten_subdirs_present_increments_classification_errors(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
    phase_context_factory: Callable[[RawAnalyzeConfig], PhaseContext],
) -> None:
    # flatten_dir_into_misc 仅处理单层目录；含子目录时计数自增并返回 False（不取消）
    files_misc = tmp_path / "files_misc"
    files_misc.mkdir()
    config = raw_analyze_config_factory(tmp_path, files_misc=files_misc)

    src = tmp_path / "with_subdir"
    src.mkdir()
    (src / "a.mp4").write_text("v")
    (src / "sub").mkdir()

    phases = RawPhaseCounters()
    cancelled = flatten_dir_into_misc(
        phase_context_factory(config),
        src,
        phases,
        dry_run=False,
        cancellation_event=None,
    )
    assert cancelled is False
    assert phases.phase2_classification_errors == 1
    assert src.exists()


def test_run_phase2_classify_skips_when_dir_missing(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
    phase_context_factory: Callable[[RawAnalyzeConfig], PhaseContext],
) -> None:
    config = raw_analyze_config_factory(tmp_path)
    phases = RawPhaseCounters()
    cancelled = run_phase2_classify(
        phase_context_factory(config),
        tmp_path / "does_not_exist",
        phases,
        dry_run=False,
        cancellation_event=None,
    )
    assert cancelled is False
    assert phases.phase2_classification_errors == 0


def test_run_phase2_classify_returns_true_when_cancelled_before_call(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
    phase_context_factory: Callable[[RawAnalyzeConfig], PhaseContext],
) -> None:
    config = raw_analyze_config_factory(tmp_path)
    src = tmp_path / "any_dir"
    src.mkdir()
    (src / "a.mp4").write_text("v")

    event = threading.Event()
    event.set()

    phases = RawPhaseCounters()
    cancelled = run_phase2_classify(
        phase_context_factory(config),
        src,
        phases,
        dry_run=False,
        cancellation_event=event,
    )
    assert cancelled is True
    # 早期取消 → 不应触发任何分类计数
    assert phases.phase2_moved_to_misc_dirs == 0
    assert phases.phase2_flattened_dirs == 0
