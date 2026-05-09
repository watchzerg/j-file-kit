"""phase3 视频桶分类测试。"""

from collections.abc import Callable
from pathlib import Path

import pytest

from j_file_kit.app.file_task.application.raw_analyze_config import RawAnalyzeConfig
from j_file_kit.app.file_task.application.raw_pipeline.context import PhaseContext
from j_file_kit.app.file_task.application.raw_pipeline.counters import RawPhaseCounters
from j_file_kit.app.file_task.application.raw_pipeline.phase3 import (
    classify_video_bucket,
    run_phase3,
)
from j_file_kit.shared.utils.name_keyword_match import name_contains_keyword

pytestmark = pytest.mark.unit


def test_name_contains_keyword_case_insensitive() -> None:
    assert name_contains_keyword("Foo_AMZN_bar", "amzn")


def test_classify_movie_wins_over_us_vr() -> None:
    assert classify_video_bucket("AMZN_VirtualTaboo_x") == "movie"


def test_classify_jav_empty_keywords_goes_misc() -> None:
    assert classify_video_bucket("jav_only_stem") == "misc"


def test_routes_each_video_keyword(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
    phase_context_factory: Callable[[RawAnalyzeConfig], PhaseContext],
) -> None:
    misc = tmp_path / "files_misc"
    misc.mkdir()
    config = raw_analyze_config_factory(
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
    run_phase3(phase_context_factory(config), counters, dry_run=False)

    assert counters.phase3_deferred_files_misc == 0
    assert list(misc.iterdir()) == []
    assert (tmp_path / "files_video_movie" / "m_AMZN.mp4").read_text() == "a"
    assert (tmp_path / "files_video_us_vr" / "v_VirtualTaboo.mp4").read_text() == "b"
    assert (tmp_path / "files_video_us" / "u_HardCoreGangbang.mp4").read_text() == "c"
    assert (tmp_path / "files_video_jav_vr" / "jv_JAV-VR.mp4").read_text() == "d"


def test_amzn_only_routes_to_movie(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
    phase_context_factory: Callable[[RawAnalyzeConfig], PhaseContext],
) -> None:
    misc = tmp_path / "files_misc"
    misc.mkdir()
    config = raw_analyze_config_factory(
        tmp_path,
        files_misc=misc,
        files_compressed=tmp_path / "files_compressed",
        files_pic=tmp_path / "files_pic",
        files_audio=tmp_path / "files_audio",
    )
    (misc / "x_AMZN.mp4").write_text("m")

    counters = RawPhaseCounters()
    run_phase3(phase_context_factory(config), counters, dry_run=False)

    assert (tmp_path / "files_video_movie" / "x_AMZN.mp4").read_text() == "m"
    assert counters.phase3_deferred_files_misc == 0
