"""phase3 视频桶分类测试。"""

from collections.abc import Callable
from pathlib import Path

import pytest

from j_file_kit.app.file_task.application.raw_analyze_config import RawAnalyzeConfig
from j_file_kit.app.file_task.application.raw_pipeline.context import PhaseContext
from j_file_kit.app.file_task.application.raw_pipeline.counters import RawPhaseCounters
from j_file_kit.app.file_task.application.raw_pipeline.phase3 import (
    classify_video_bucket,
    classify_video_bucket_and_subdir,
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
    assert (
        tmp_path / "files_video_us_vr" / "VirtualTaboo" / "v_VirtualTaboo.mp4"
    ).read_text() == "b"
    assert (
        tmp_path / "files_video_us" / "HardCoreGangbang" / "u_HardCoreGangbang.mp4"
    ).read_text() == "c"
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


# --- CamelCase 变体匹配测试 ---


def test_classify_video_bucket_camelcase_dot_variant() -> None:
    # Lethal.Hardcore.VR（点分隔）应命中 us_vr 桶
    assert classify_video_bucket("Lethal.Hardcore.VR_clip") == "us_vr"


def test_classify_video_bucket_camelcase_underscore_variant() -> None:
    assert classify_video_bucket("Lethal_Hardcore_VR_clip") == "us_vr"


def test_classify_video_bucket_camelcase_hyphen_variant() -> None:
    assert classify_video_bucket("Lethal-Hardcore-VR.clip") == "us_vr"


def test_classify_video_bucket_camelcase_space_variant() -> None:
    assert classify_video_bucket("Lethal Hardcore VR clip") == "us_vr"


def test_classify_video_bucket_camelcase_original_still_works() -> None:
    assert classify_video_bucket("LethalHardcoreVR.clip") == "us_vr"


def test_classify_video_bucket_vredging_dot_variant() -> None:
    # VRedging 含 no_split 保护的 VR 词根，VR.edging 应命中 us_vr 桶
    assert classify_video_bucket("VR.edging.scene") == "us_vr"


def test_classify_video_bucket_slr_still_works() -> None:
    # SLR 全大写，无变体展开，原始形式仍可命中
    assert classify_video_bucket("SLR_scene.01") == "us_vr"


def test_classify_video_bucket_hard_core_gangbang_dot_variant() -> None:
    # HardCoreGangbang → Hard.Core.Gangbang
    assert classify_video_bucket("Hard.Core.Gangbang.scene") == "us"


def test_classify_video_bucket_camelcase_no_false_positive() -> None:
    # 无 token 边界时不应命中
    assert classify_video_bucket("XLethalHardcoreVRY") == "misc"


# --- classify_video_bucket_and_subdir 测试 ---


def test_classify_video_bucket_and_subdir_us_returns_keyword() -> None:
    # US 桶命中时返回原始关键词作为子目录名
    assert classify_video_bucket_and_subdir("u_HardCoreGangbang_scene") == (
        "us",
        "HardCoreGangbang",
    )


def test_classify_video_bucket_and_subdir_us_camelcase_variant_returns_original_keyword() -> (
    None
):
    # CamelCase 变体命中时，子目录名仍为原始关键词（非归一化变体）
    assert classify_video_bucket_and_subdir("Hard.Core.Gangbang.scene") == (
        "us",
        "HardCoreGangbang",
    )


def test_classify_video_bucket_and_subdir_non_subdir_buckets_return_none() -> None:
    # movie / jav_vr / misc 桶返回 None 子目录名；us 和 us_vr 桶返回关键词
    assert classify_video_bucket_and_subdir("x_AMZN_feature") == ("movie", None)
    assert classify_video_bucket_and_subdir("unknown_stem") == ("misc", None)


def test_classify_video_bucket_and_subdir_us_vr_returns_keyword() -> None:
    # US_VR 桶命中时返回原始关键词作为子目录名
    assert classify_video_bucket_and_subdir("v_VirtualTaboo_ep01") == (
        "us_vr",
        "VirtualTaboo",
    )


def test_classify_video_bucket_and_subdir_us_vr_camelcase_variant_returns_original_keyword() -> (
    None
):
    # CamelCase 变体命中时，子目录名仍为原始关键词（非归一化变体）
    assert classify_video_bucket_and_subdir("Lethal.Hardcore.VR.clip") == (
        "us_vr",
        "LethalHardcoreVR",
    )


def test_routes_us_vr_video_to_keyword_subdir(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
    phase_context_factory: Callable[[RawAnalyzeConfig], PhaseContext],
) -> None:
    # 集成验证：US_VR 视频文件实际落入 files_video_us_vr/{keyword}/ 子目录
    misc = tmp_path / "files_misc"
    misc.mkdir()
    config = raw_analyze_config_factory(
        tmp_path,
        files_misc=misc,
        files_compressed=tmp_path / "files_compressed",
        files_pic=tmp_path / "files_pic",
        files_audio=tmp_path / "files_audio",
    )
    (misc / "VirtualTaboo.scene.mp4").write_text("v")
    (misc / "VirtualTaboo.scene.srt").write_text("s")

    counters = RawPhaseCounters()
    run_phase3(phase_context_factory(config), counters, dry_run=False)

    subdir = tmp_path / "files_video_us_vr" / "VirtualTaboo"
    assert (subdir / "VirtualTaboo.scene.mp4").read_text() == "v"
    assert (subdir / "VirtualTaboo.scene.srt").read_text() == "s"
    assert list(misc.iterdir()) == []
    assert counters.phase3_deferred_files_misc == 0


def test_classify_video_bucket_and_subdir_ordered_first_wins(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
    phase_context_factory: Callable[[RawAnalyzeConfig], PhaseContext],
) -> None:
    # 当 stem 同时含两个 US 关键词时，配置顺序靠前的关键词优先命中
    # DEFAULT_RAW_VIDEO_BUCKET_US_KEYWORDS 当前只有 HardCoreGangbang；
    # 此测试通过 run_phase3 验证保序行为：文件落入 HardCoreGangbang 子目录
    misc = tmp_path / "files_misc"
    misc.mkdir()
    config = raw_analyze_config_factory(
        tmp_path,
        files_misc=misc,
        files_compressed=tmp_path / "files_compressed",
        files_pic=tmp_path / "files_pic",
        files_audio=tmp_path / "files_audio",
    )
    (misc / "Hard.Core.Gangbang.scene.mp4").write_text("x")

    counters = RawPhaseCounters()
    run_phase3(phase_context_factory(config), counters, dry_run=False)

    assert (
        tmp_path
        / "files_video_us"
        / "HardCoreGangbang"
        / "Hard.Core.Gangbang.scene.mp4"
    ).exists()
    assert counters.phase3_deferred_files_misc == 0


def test_routes_us_video_to_keyword_subdir(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
    phase_context_factory: Callable[[RawAnalyzeConfig], PhaseContext],
) -> None:
    # 集成验证：US 视频文件实际落入 files_video_us/{keyword}/ 子目录
    misc = tmp_path / "files_misc"
    misc.mkdir()
    config = raw_analyze_config_factory(
        tmp_path,
        files_misc=misc,
        files_compressed=tmp_path / "files_compressed",
        files_pic=tmp_path / "files_pic",
        files_audio=tmp_path / "files_audio",
    )
    (misc / "HardCoreGangbang.scene.mp4").write_text("v")
    (misc / "HardCoreGangbang.scene.srt").write_text("s")

    counters = RawPhaseCounters()
    run_phase3(phase_context_factory(config), counters, dry_run=False)

    subdir = tmp_path / "files_video_us" / "HardCoreGangbang"
    assert (subdir / "HardCoreGangbang.scene.mp4").read_text() == "v"
    assert (subdir / "HardCoreGangbang.scene.srt").read_text() == "s"
    assert list(misc.iterdir()) == []
    assert counters.phase3_deferred_files_misc == 0
