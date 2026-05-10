"""phase3 视频桶分类测试。"""

from collections.abc import Callable
from pathlib import Path

import pytest

from j_file_kit.app.file_task.application.raw_analyze_config import RawAnalyzeConfig
from j_file_kit.app.file_task.application.raw_pipeline.context import PhaseContext
from j_file_kit.app.file_task.application.raw_pipeline.counters import RawPhaseCounters
from j_file_kit.app.file_task.application.raw_pipeline.phase3 import run_phase3
from j_file_kit.app.file_task.application.raw_pipeline.video_bucket_classifier import (
    classify_video_bucket,
    classify_video_bucket_and_subdir,
)
from j_file_kit.shared.utils.name_keyword_match import name_contains_keyword

pytestmark = pytest.mark.unit


def test_name_contains_keyword_case_insensitive() -> None:
    assert name_contains_keyword("Foo_AMZN_bar", "amzn")


def test_classify_movie_wins_over_us_vr() -> None:
    assert classify_video_bucket("AMZN_VirtualTaboo_x") == "movie"


def test_classify_no_serial_goes_misc() -> None:
    # 无可识别番号的 stem 归入 misc
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
    (misc / "u_HardcoreGangBang.mp4").write_text("c")
    (misc / "JAVR-001.mp4").write_text("d")

    counters = RawPhaseCounters()
    run_phase3(phase_context_factory(config), counters, dry_run=False)

    assert counters.phase3_deferred_files_misc == 0
    assert counters.phase3_routed_video_files == 4
    assert counters.phase3_routed_video_movie_files == 1
    assert counters.phase3_routed_video_us_vr_files == 1
    assert counters.phase3_routed_video_us_files == 1
    assert counters.phase3_routed_video_jav_vr_files == 1
    assert list(misc.iterdir()) == []
    assert (tmp_path / "files_video_movie" / "AMZN" / "m_AMZN.mp4").read_text() == "a"
    assert (
        tmp_path / "files_video_us_vr" / "VirtualTaboo" / "v_VirtualTaboo.mp4"
    ).read_text() == "b"
    assert (
        tmp_path / "files_video_us" / "HardcoreGangBang" / "u_HardcoreGangBang.mp4"
    ).read_text() == "c"
    assert (tmp_path / "files_video_jav_vr" / "JAVR-001.mp4").read_text() == "d"


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

    assert (tmp_path / "files_video_movie" / "AMZN" / "x_AMZN.mp4").read_text() == "m"
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


def test_classify_video_bucket_hardcore_gangbang_dot_variant() -> None:
    # HardcoreGangBang → Hardcore.Gang.Bang（Hardcore 为完整词根，不为 Hard.Core）
    assert classify_video_bucket("Hardcore.Gang.Bang.scene") == "us"


def test_classify_video_bucket_camelcase_no_false_positive() -> None:
    # 无 token 边界时不应命中
    assert classify_video_bucket("XLethalHardcoreVRY") == "misc"


# --- classify_video_bucket_and_subdir 测试 ---


def test_classify_video_bucket_and_subdir_us_returns_keyword() -> None:
    # US 桶命中时返回原始关键词作为子目录名
    assert classify_video_bucket_and_subdir("u_HardcoreGangBang_scene") == (
        "us",
        "HardcoreGangBang",
    )


def test_classify_video_bucket_and_subdir_us_camelcase_variant_returns_original_keyword() -> (
    None
):
    # CamelCase 变体命中时，子目录名仍为原始关键词（非归一化变体）
    assert classify_video_bucket_and_subdir("Hardcore.Gang.Bang.scene") == (
        "us",
        "HardcoreGangBang",
    )


def test_classify_video_bucket_and_subdir_non_subdir_buckets_return_none() -> None:
    # jav_vr / jav / misc 桶均返回 None 子目录名；movie / us_vr / us 桶返回关键词
    assert classify_video_bucket_and_subdir("unknown_stem") == ("misc", None)


def test_classify_video_bucket_and_subdir_movie_returns_keyword() -> None:
    # movie 桶命中时返回原始关键词作为子目录名
    assert classify_video_bucket_and_subdir("x_AMZN_feature") == ("movie", "AMZN")


def test_routes_movie_video_to_keyword_subdir(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
    phase_context_factory: Callable[[RawAnalyzeConfig], PhaseContext],
) -> None:
    # 集成验证：movie 视频文件实际落入 files_video_movie/{keyword}/ 子目录
    misc = tmp_path / "files_misc"
    misc.mkdir()
    config = raw_analyze_config_factory(
        tmp_path,
        files_misc=misc,
        files_compressed=tmp_path / "files_compressed",
        files_pic=tmp_path / "files_pic",
        files_audio=tmp_path / "files_audio",
    )
    (misc / "AMZN.movie.mp4").write_text("v")
    (misc / "AMZN.movie.srt").write_text("s")

    counters = RawPhaseCounters()
    run_phase3(phase_context_factory(config), counters, dry_run=False)

    subdir = tmp_path / "files_video_movie" / "AMZN"
    assert (subdir / "AMZN.movie.mp4").read_text() == "v"
    assert (subdir / "AMZN.movie.srt").read_text() == "s"
    assert list(misc.iterdir()) == []
    assert counters.phase3_deferred_files_misc == 0


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
    # 此处选用 HardcoreGangBang 及其点分变体验证保序：文件落入 HardcoreGangBang 子目录
    misc = tmp_path / "files_misc"
    misc.mkdir()
    config = raw_analyze_config_factory(
        tmp_path,
        files_misc=misc,
        files_compressed=tmp_path / "files_compressed",
        files_pic=tmp_path / "files_pic",
        files_audio=tmp_path / "files_audio",
    )
    (misc / "Hardcore.Gang.Bang.scene.mp4").write_text("x")

    counters = RawPhaseCounters()
    run_phase3(phase_context_factory(config), counters, dry_run=False)

    assert (
        tmp_path
        / "files_video_us"
        / "HardcoreGangBang"
        / "Hardcore.Gang.Bang.scene.mp4"
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
    (misc / "HardcoreGangBang.scene.mp4").write_text("v")
    (misc / "HardcoreGangBang.scene.srt").write_text("s")

    counters = RawPhaseCounters()
    run_phase3(phase_context_factory(config), counters, dry_run=False)

    subdir = tmp_path / "files_video_us" / "HardcoreGangBang"
    assert (subdir / "HardcoreGangBang.scene.mp4").read_text() == "v"
    assert (subdir / "HardcoreGangBang.scene.srt").read_text() == "s"
    assert list(misc.iterdir()) == []
    assert counters.phase3_deferred_files_misc == 0


# --- JAV 番号分流测试 ---


def test_classify_jav_vr_serial_prefix_goes_jav_vr() -> None:
    # JAVR 前缀番号归入 jav_vr 桶
    assert classify_video_bucket("JAVR-001") == "jav_vr"


def test_classify_jav_non_vr_serial_prefix_goes_jav() -> None:
    # 非 VR 白名单前缀的番号归入 jav 桶
    assert classify_video_bucket("ABCD-001") == "jav"


def test_classify_noise_stripped_jav_vr_serial() -> None:
    # stem 含 DEFAULT_JAV_FILENAME_STRIP_SUBSTRINGS 中的站标噪声，去噪后识别出 JAVR 番号 → jav_vr
    assert classify_video_bucket("JAVR-001-BBS-2048") == "jav_vr"


def test_routes_jav_video_to_jav_dir(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
    phase_context_factory: Callable[[RawAnalyzeConfig], PhaseContext],
) -> None:
    # 集成验证：普通 JAV 番号视频落入 files_video_jav/
    misc = tmp_path / "files_misc"
    misc.mkdir()
    config = raw_analyze_config_factory(
        tmp_path,
        files_misc=misc,
        files_compressed=tmp_path / "files_compressed",
        files_pic=tmp_path / "files_pic",
        files_audio=tmp_path / "files_audio",
    )
    (misc / "ABCD-001.mp4").write_text("v")

    counters = RawPhaseCounters()
    run_phase3(phase_context_factory(config), counters, dry_run=False)

    assert (tmp_path / "files_video_jav" / "ABCD-001.mp4").read_text() == "v"
    assert list(misc.iterdir()) == []
    assert counters.phase3_deferred_files_misc == 0


def test_routes_jav_vr_video_and_subtitle_to_jav_vr_dir(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
    phase_context_factory: Callable[[RawAnalyzeConfig], PhaseContext],
) -> None:
    # 集成验证：JAVR 番号视频与字幕均落入 files_video_jav_vr/（字幕与视频共用桶路由）
    misc = tmp_path / "files_misc"
    misc.mkdir()
    config = raw_analyze_config_factory(
        tmp_path,
        files_misc=misc,
        files_compressed=tmp_path / "files_compressed",
        files_pic=tmp_path / "files_pic",
        files_audio=tmp_path / "files_audio",
    )
    (misc / "JAVR-001.mp4").write_text("v")
    (misc / "JAVR-001.srt").write_text("s")

    counters = RawPhaseCounters()
    run_phase3(phase_context_factory(config), counters, dry_run=False)

    assert (tmp_path / "files_video_jav_vr" / "JAVR-001.mp4").read_text() == "v"
    assert (tmp_path / "files_video_jav_vr" / "JAVR-001.srt").read_text() == "s"
    assert list(misc.iterdir()) == []
    assert counters.phase3_deferred_files_misc == 0
