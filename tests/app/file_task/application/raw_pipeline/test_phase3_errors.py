"""phase3 边界与错误路径测试。

聚焦 ``_video_destination_root`` / ``_destination_root_for_routed_kind`` 在未知桶或类型时
的快速失败、``_move_routed_file`` 在移动失败时返回 False 让上层 ``deferred += 1``，
以及字幕文件经视频桶路由的链路完整性。
"""

from collections.abc import Callable
from pathlib import Path
from unittest.mock import patch

import pytest

from j_file_kit.app.file_task.application.raw_analyze_config import RawAnalyzeConfig
from j_file_kit.app.file_task.application.raw_pipeline.context import PhaseContext
from j_file_kit.app.file_task.application.raw_pipeline.counters import RawPhaseCounters
from j_file_kit.app.file_task.application.raw_pipeline.phase3 import (
    _destination_root_for_routed_kind,
    _move_routed_file,
    _video_destination_root,
    run_phase3,
)

pytestmark = pytest.mark.unit


def _make_cfg(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
) -> RawAnalyzeConfig:
    misc = tmp_path / "files_misc"
    misc.mkdir()
    return raw_analyze_config_factory(tmp_path, files_misc=misc)


# --- 内部 dispatcher 边界 ---


def test_video_destination_root_raises_on_unknown_bucket(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
) -> None:
    cfg = _make_cfg(tmp_path, raw_analyze_config_factory)
    with pytest.raises(RuntimeError, match="未知视频桶"):
        _video_destination_root("invalid_bucket", cfg)


def test_destination_root_for_routed_kind_raises_on_unknown(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
) -> None:
    cfg = _make_cfg(tmp_path, raw_analyze_config_factory)
    with pytest.raises(RuntimeError, match="不支持的路由类型"):
        _destination_root_for_routed_kind("video", cfg)


def test_video_destination_root_for_jav_buckets_does_not_use_subdir(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
) -> None:
    # jav / jav_vr / misc 桶不接受 subdir 参数（即使传入也会被忽略）
    cfg = _make_cfg(tmp_path, raw_analyze_config_factory)
    assert _video_destination_root("jav", cfg, subdir="ignored") == cfg.files_video_jav
    assert (
        _video_destination_root("jav_vr", cfg, subdir="ignored")
        == cfg.files_video_jav_vr
    )
    assert _video_destination_root("misc", cfg, subdir=None) == cfg.files_video_misc


# --- _move_routed_file 错误处理 ---


def test_move_routed_file_returns_false_on_oserror(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
    phase_context_factory: Callable[[RawAnalyzeConfig], PhaseContext],
) -> None:
    cfg = _make_cfg(tmp_path, raw_analyze_config_factory)
    src = cfg.files_misc / "x.mp4"
    src.write_text("v")

    with patch(
        "j_file_kit.app.file_task.application.raw_pipeline.phase3."
        "move_file_with_conflict_resolution",
        side_effect=OSError("disk full"),
    ):
        ok = _move_routed_file(
            phase_context_factory(cfg),
            src,
            cfg.files_video_misc,
            kind="video",
            video_bucket="misc",
            dry_run=False,
        )
    assert ok is False
    assert src.exists()


def test_move_routed_file_dry_run_returns_true_without_moving(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
    phase_context_factory: Callable[[RawAnalyzeConfig], PhaseContext],
) -> None:
    cfg = _make_cfg(tmp_path, raw_analyze_config_factory)
    src = cfg.files_misc / "x.mp4"
    src.write_text("v")

    ok = _move_routed_file(
        phase_context_factory(cfg),
        src,
        cfg.files_video_misc,
        kind="video",
        video_bucket="misc",
        dry_run=True,
    )
    assert ok is True
    assert src.exists()
    assert not (cfg.files_video_misc / "x.mp4").exists()


def test_run_phase3_increments_deferred_when_move_fails(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
    phase_context_factory: Callable[[RawAnalyzeConfig], PhaseContext],
) -> None:
    # 当移动失败时，对应文件应进入 deferred 计数（仍留在 files_misc 中）
    cfg = _make_cfg(tmp_path, raw_analyze_config_factory)
    (cfg.files_misc / "a.zip").write_text("z")
    (cfg.files_misc / "b.mp4").write_text("v")

    counters = RawPhaseCounters()
    with patch(
        "j_file_kit.app.file_task.application.raw_pipeline.phase3."
        "move_file_with_conflict_resolution",
        side_effect=OSError("io"),
    ):
        run_phase3(phase_context_factory(cfg), counters, dry_run=False)

    assert counters.phase3_seen_files_misc == 2
    assert counters.phase3_deferred_files_misc == 2
    assert counters.phase3_deferred_unknown_extension_files == 0
    assert counters.phase3_deferred_error_files == 2
    # 文件仍留在 files_misc
    assert (cfg.files_misc / "a.zip").exists()
    assert (cfg.files_misc / "b.mp4").exists()


# --- 字幕文件经视频桶路由 ---


def test_subtitle_with_jav_serial_routed_to_jav_dir(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
    phase_context_factory: Callable[[RawAnalyzeConfig], PhaseContext],
) -> None:
    # 单独存在的 .srt（无伴随 .mp4），stem 含 JAV 番号 → 走视频桶路由 → files_video_jav
    cfg = _make_cfg(tmp_path, raw_analyze_config_factory)
    (cfg.files_misc / "ABCD-001.srt").write_text("s")

    counters = RawPhaseCounters()
    run_phase3(phase_context_factory(cfg), counters, dry_run=False)

    assert counters.phase3_deferred_files_misc == 0
    assert (cfg.files_video_jav / "ABCD-001.srt").read_text() == "s"
    assert list(cfg.files_misc.iterdir()) == []


def test_subtitle_without_keyword_or_serial_routed_to_misc(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
    phase_context_factory: Callable[[RawAnalyzeConfig], PhaseContext],
) -> None:
    # stem 既不含视频桶关键词、也不含番号 → misc 桶 → files_video_misc
    cfg = _make_cfg(tmp_path, raw_analyze_config_factory)
    (cfg.files_misc / "random_subtitle.srt").write_text("s")

    counters = RawPhaseCounters()
    run_phase3(phase_context_factory(cfg), counters, dry_run=False)

    assert counters.phase3_deferred_files_misc == 0
    assert (cfg.files_video_misc / "random_subtitle.srt").read_text() == "s"
