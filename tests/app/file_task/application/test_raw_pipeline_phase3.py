"""RawFilePipeline 阶段 3（files_misc 分流）单元测试。"""

from collections.abc import Callable
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from j_file_kit.app.file_task.application.file_ops import (
    JFK_CONFLICT_STEM_SUFFIX_BYTES,
    MAX_FILENAME_BYTES,
)
from j_file_kit.app.file_task.application.raw_analyze_config import RawAnalyzeConfig
from j_file_kit.app.file_task.application.raw_pipeline.context import PhaseContext
from j_file_kit.app.file_task.application.raw_pipeline.counters import RawPhaseCounters
from j_file_kit.app.file_task.application.raw_pipeline.phase3 import (
    classify_phase34_video_bucket,
    run_phase3,
)
from j_file_kit.shared.utils.name_keyword_match import name_contains_keyword

pytestmark = pytest.mark.unit


def _ctx(tmp_path: Path, cfg: RawAnalyzeConfig) -> PhaseContext:
    return PhaseContext(
        run_id=1,
        run_name="raw_file_organizer",
        scan_root=tmp_path / "inbox",
        analyze_config=cfg,
        file_result_repository=MagicMock(),
    )


def test_phase3_moves_archive_image_audio(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
) -> None:
    misc = tmp_path / "files_misc"
    fc = tmp_path / "files_compressed"
    fp = tmp_path / "files_pic"
    fa = tmp_path / "files_audio"
    misc.mkdir()
    cfg = raw_analyze_config_factory(
        tmp_path,
        files_misc=misc,
        files_compressed=fc,
        files_pic=fp,
        files_audio=fa,
    )
    (misc / "a.zip").write_text("zip")
    (misc / "b.jpg").write_text("img")
    (misc / "c.mp3").write_text("snd")

    counters = RawPhaseCounters()
    run_phase3(_ctx(tmp_path, cfg), counters, dry_run=False)

    assert counters.phase3_seen_files_misc == 3
    assert counters.phase3_deleted_junk_misc == 0
    assert counters.phase3_deferred_files_misc == 0
    assert (fc / "a.zip").read_text() == "zip"
    assert (fp / "b.jpg").read_text() == "img"
    assert (fa / "c.mp3").read_text() == "snd"
    assert list(misc.iterdir()) == []


def test_phase3_routes_video_misc_and_defers_unknown_non_video(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
) -> None:
    misc = tmp_path / "files_misc"
    misc.mkdir()
    cfg = raw_analyze_config_factory(
        tmp_path,
        files_misc=misc,
        files_compressed=tmp_path / "files_compressed",
        files_pic=tmp_path / "files_pic",
        files_audio=tmp_path / "files_audio",
    )
    (misc / "v.mp4").write_text("v")
    (misc / "u.txt").write_text("u")

    counters = RawPhaseCounters()
    run_phase3(_ctx(tmp_path, cfg), counters, dry_run=False)

    assert counters.phase3_seen_files_misc == 2
    assert counters.phase3_deleted_junk_misc == 0
    assert counters.phase3_deferred_files_misc == 1
    files_video_misc = tmp_path / "files_video_misc"
    assert (files_video_misc / "v.mp4").read_text() == "v"
    assert (misc / "u.txt").exists()


def test_phase3_conflict_resolution(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
) -> None:
    misc = tmp_path / "files_misc"
    fc = tmp_path / "files_compressed"
    misc.mkdir()
    cfg = raw_analyze_config_factory(
        tmp_path,
        files_misc=misc,
        files_compressed=fc,
        files_pic=tmp_path / "files_pic",
        files_audio=tmp_path / "files_audio",
    )
    (fc / "dup.zip").write_text("old")
    (misc / "dup.zip").write_text("new")

    counters = RawPhaseCounters()
    run_phase3(_ctx(tmp_path, cfg), counters, dry_run=False)

    assert counters.phase3_deleted_junk_misc == 0
    assert counters.phase3_deferred_files_misc == 0
    assert not (misc / "dup.zip").exists()
    in_fc = list(fc.glob("dup*.zip"))
    assert len(in_fc) == 2
    assert {p.read_text() for p in in_fc} == {"old", "new"}


def test_phase3_truncates_long_basename(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
) -> None:
    misc = tmp_path / "files_misc"
    fc = tmp_path / "files_compressed"
    misc.mkdir()
    cfg = raw_analyze_config_factory(
        tmp_path,
        files_misc=misc,
        files_compressed=fc,
        files_pic=tmp_path / "files_pic",
        files_audio=tmp_path / "files_audio",
    )
    long_name = "y" * 240 + ".zip"
    assert len(long_name.encode()) == 244
    (misc / long_name).write_text("x")

    counters = RawPhaseCounters()
    run_phase3(_ctx(tmp_path, cfg), counters, dry_run=False)

    assert counters.phase3_deleted_junk_misc == 0
    assert counters.phase3_deferred_files_misc == 0
    moved = list(fc.iterdir())
    assert len(moved) == 1
    assert (
        len(moved[0].name.encode())
        <= MAX_FILENAME_BYTES - JFK_CONFLICT_STEM_SUFFIX_BYTES
    )


def test_phase3_dry_run_does_not_move(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
) -> None:
    misc = tmp_path / "files_misc"
    fc = tmp_path / "files_compressed"
    misc.mkdir()
    cfg = raw_analyze_config_factory(
        tmp_path,
        files_misc=misc,
        files_compressed=fc,
        files_pic=tmp_path / "files_pic",
        files_audio=tmp_path / "files_audio",
    )
    (misc / "a.zip").write_text("z")
    (misc / "b.mp4").write_text("v")

    counters = RawPhaseCounters()
    run_phase3(_ctx(tmp_path, cfg), counters, dry_run=True)

    assert counters.phase3_seen_files_misc == 2
    assert counters.phase3_deleted_junk_misc == 0
    assert counters.phase3_deferred_files_misc == 0
    assert (misc / "a.zip").exists()
    assert (misc / "b.mp4").exists()
    assert list(fc.iterdir()) == []


def test_phase3_skips_when_misc_missing(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
) -> None:
    misc = tmp_path / "files_misc"
    cfg = raw_analyze_config_factory(
        tmp_path,
        files_misc=misc,
        files_compressed=tmp_path / "files_compressed",
        files_pic=tmp_path / "files_pic",
        files_audio=tmp_path / "files_audio",
    )
    counters = RawPhaseCounters()
    run_phase3(_ctx(tmp_path, cfg), counters, dry_run=False)
    assert counters.phase3_seen_files_misc == 0
    assert counters.phase3_deleted_junk_misc == 0
    assert counters.phase3_deferred_files_misc == 0


def test_phase3_preclean_moves_junk_stem_to_files_to_delete_then_routes_archive(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
) -> None:
    misc = tmp_path / "files_misc"
    fc = tmp_path / "files_compressed"
    fdel = tmp_path / "files_to_delete"
    misc.mkdir()
    cfg = raw_analyze_config_factory(
        tmp_path,
        files_misc=misc,
        files_compressed=fc,
        files_pic=tmp_path / "files_pic",
        files_audio=tmp_path / "files_audio",
        files_to_delete=fdel,
    )
    (misc / "ad_FC2-PPV.txt").write_text("junk")
    (misc / "a.zip").write_text("z")

    counters = RawPhaseCounters()
    run_phase3(_ctx(tmp_path, cfg), counters, dry_run=False)

    assert counters.phase3_deleted_junk_misc == 1
    assert counters.phase3_seen_files_misc == 1
    assert (fc / "a.zip").read_text() == "z"
    assert not (misc / "ad_FC2-PPV.txt").exists()
    moved = list(fdel.glob("*.txt"))
    assert len(moved) == 1
    assert moved[0].read_text() == "junk"


def test_phase3_preclean_moves_large_junk_stem_to_files_to_delete(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
) -> None:
    misc = tmp_path / "files_misc"
    fdel = tmp_path / "files_to_delete"
    misc.mkdir()
    cfg = raw_analyze_config_factory(
        tmp_path,
        files_misc=misc,
        files_compressed=tmp_path / "files_compressed",
        files_pic=tmp_path / "files_pic",
        files_audio=tmp_path / "files_audio",
        files_to_delete=fdel,
    )
    p = misc / "big_FC2-PPV.bin"
    p.write_bytes(b"z" * (1024 * 1024 + 1))

    counters = RawPhaseCounters()
    run_phase3(_ctx(tmp_path, cfg), counters, dry_run=False)

    assert counters.phase3_deleted_junk_misc == 1
    assert counters.phase3_seen_files_misc == 0
    assert not p.exists()
    moved = list(fdel.glob("*.bin"))
    assert len(moved) == 1
    assert moved[0].stat().st_size == 1024 * 1024 + 1


def test_phase3_only_junk_archive_preclean_does_not_require_files_compressed(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
) -> None:
    """唯余 zip 也因 stem junk 迁入 files_to_delete 时，不因缺压缩归宿而报错。"""
    misc = tmp_path / "files_misc"
    fdel = tmp_path / "files_to_delete"
    misc.mkdir()
    cfg = raw_analyze_config_factory(
        tmp_path,
        files_misc=misc,
        files_to_delete=fdel,
    )
    (misc / "junk_FC2-PPV.zip").write_bytes(b"x")

    counters = RawPhaseCounters()
    run_phase3(_ctx(tmp_path, cfg), counters, dry_run=False)

    assert counters.phase3_deleted_junk_misc == 1
    assert counters.phase3_seen_files_misc == 0
    assert list(misc.iterdir()) == []
    assert (fdel / "junk_FC2-PPV.zip").read_bytes() == b"x"


def test_phase3_dry_run_preclean_counts_without_unlink(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
) -> None:
    misc = tmp_path / "files_misc"
    fc = tmp_path / "files_compressed"
    misc.mkdir()
    cfg = raw_analyze_config_factory(
        tmp_path,
        files_misc=misc,
        files_compressed=fc,
        files_pic=tmp_path / "files_pic",
        files_audio=tmp_path / "files_audio",
    )
    (misc / "promo_FC2-PPV.jpg").write_text("pic")

    counters = RawPhaseCounters()
    run_phase3(_ctx(tmp_path, cfg), counters, dry_run=True)

    assert counters.phase3_deleted_junk_misc == 1
    assert counters.phase3_seen_files_misc == 0
    assert counters.phase3_deferred_files_misc == 0
    assert (misc / "promo_FC2-PPV.jpg").exists()


def test_name_contains_keyword_case_insensitive() -> None:
    assert name_contains_keyword("Foo_AMZN_bar", "amzn")


def test_classify_phase34_movie_wins_over_us_vr() -> None:
    assert classify_phase34_video_bucket("AMZN_VirtualTaboo_x") == "movie"


def test_classify_phase34_jav_empty_keywords_goes_misc() -> None:
    assert classify_phase34_video_bucket("jav_only_stem") == "misc"


def test_phase34_routes_each_keyword_bucket(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
) -> None:
    misc = tmp_path / "files_misc"
    misc.mkdir()
    cfg = raw_analyze_config_factory(
        tmp_path,
        files_misc=misc,
        files_compressed=tmp_path / "files_compressed",
        files_pic=tmp_path / "files_pic",
        files_audio=tmp_path / "files_audio",
    )
    (misc / "m_AMZN.mp4").write_text("a")
    (misc / "v_VirtualTaboo.mp4").write_text("b")
    (misc / "u_HardCoreGangbang.mp4").write_text("c")
    (misc / "jv_JAV-VR.mp4").write_text("d")

    counters = RawPhaseCounters()
    run_phase3(_ctx(tmp_path, cfg), counters, dry_run=False)

    assert counters.phase3_deferred_files_misc == 0
    assert list(misc.iterdir()) == []
    assert (tmp_path / "files_video_movie" / "m_AMZN.mp4").read_text() == "a"
    assert (tmp_path / "files_video_us_vr" / "v_VirtualTaboo.mp4").read_text() == "b"
    assert (tmp_path / "files_video_us" / "u_HardCoreGangbang.mp4").read_text() == "c"
    assert (tmp_path / "files_video_jav_vr" / "jv_JAV-VR.mp4").read_text() == "d"


def test_phase34_amzn_only_routes_to_movie_bucket(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
) -> None:
    misc = tmp_path / "files_misc"
    misc.mkdir()
    cfg = raw_analyze_config_factory(
        tmp_path,
        files_misc=misc,
        files_compressed=tmp_path / "files_compressed",
        files_pic=tmp_path / "files_pic",
        files_audio=tmp_path / "files_audio",
    )
    (misc / "x_AMZN.mp4").write_text("m")

    counters = RawPhaseCounters()
    run_phase3(_ctx(tmp_path, cfg), counters, dry_run=False)

    assert (tmp_path / "files_video_movie" / "x_AMZN.mp4").read_text() == "m"
    assert counters.phase3_deferred_files_misc == 0


def test_phase34_video_conflict_resolution(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
) -> None:
    misc = tmp_path / "files_misc"
    misc.mkdir()
    vmisc = tmp_path / "files_video_misc"
    vmisc.mkdir(parents=True, exist_ok=True)
    (vmisc / "dup.mp4").write_text("old")
    cfg = raw_analyze_config_factory(
        tmp_path,
        files_misc=misc,
        files_compressed=tmp_path / "files_compressed",
        files_pic=tmp_path / "files_pic",
        files_audio=tmp_path / "files_audio",
        files_video_misc=vmisc,
    )
    (misc / "dup.mp4").write_text("new")

    counters = RawPhaseCounters()
    run_phase3(_ctx(tmp_path, cfg), counters, dry_run=False)

    assert counters.phase3_deferred_files_misc == 0
    assert not (misc / "dup.mp4").exists()
    in_misc_bucket = list(vmisc.glob("dup*.mp4"))
    assert len(in_misc_bucket) == 2
    assert {p.read_text() for p in in_misc_bucket} == {"old", "new"}


def test_phase34_truncates_long_video_basename(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
) -> None:
    misc = tmp_path / "files_misc"
    misc.mkdir()
    vmisc = tmp_path / "files_video_misc"
    cfg = raw_analyze_config_factory(
        tmp_path,
        files_misc=misc,
        files_compressed=tmp_path / "files_compressed",
        files_pic=tmp_path / "files_pic",
        files_audio=tmp_path / "files_audio",
        files_video_misc=vmisc,
    )
    long_name = "y" * 240 + ".mp4"
    assert len(long_name.encode()) == 244
    (misc / long_name).write_text("x")

    counters = RawPhaseCounters()
    run_phase3(_ctx(tmp_path, cfg), counters, dry_run=False)

    assert counters.phase3_deferred_files_misc == 0
    moved = list(vmisc.iterdir())
    assert len(moved) == 1
    assert (
        len(moved[0].name.encode())
        <= MAX_FILENAME_BYTES - JFK_CONFLICT_STEM_SUFFIX_BYTES
    )


def test_phase34_preclean_removes_junk_video_before_keyword_routing(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
) -> None:
    misc = tmp_path / "files_misc"
    fdel = tmp_path / "files_to_delete"
    misc.mkdir()
    cfg = raw_analyze_config_factory(
        tmp_path,
        files_misc=misc,
        files_compressed=tmp_path / "files_compressed",
        files_pic=tmp_path / "files_pic",
        files_audio=tmp_path / "files_audio",
        files_to_delete=fdel,
    )
    (misc / "junk_FC2-PPV.mp4").write_bytes(b"v")

    counters = RawPhaseCounters()
    run_phase3(_ctx(tmp_path, cfg), counters, dry_run=False)

    assert counters.phase3_deleted_junk_misc == 1
    assert counters.phase3_seen_files_misc == 0
    assert list(misc.iterdir()) == []
    moved = list(fdel.glob("*.mp4"))
    assert len(moved) == 1
    assert moved[0].read_bytes() == b"v"
