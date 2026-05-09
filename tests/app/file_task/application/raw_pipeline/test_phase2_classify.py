"""phase2_classify：拆解判定等纯逻辑单元测试。"""

import tempfile
from collections.abc import Callable
from pathlib import Path

import pytest

from j_file_kit.app.file_task.application.config_common import raw_workspace_paths
from j_file_kit.app.file_task.application.raw_analyze_config import RawAnalyzeConfig
from j_file_kit.app.file_task.application.raw_pipeline.phase2_classify import (
    _collect_descendant_file_media_kinds,
    _flatten_kinds_allowed,
    should_flatten_small_dir,
)

pytestmark = pytest.mark.unit


def _cfg() -> RawAnalyzeConfig:
    p = raw_workspace_paths(Path(tempfile.gettempdir()) / "jfk-phase2-classify")
    return RawAnalyzeConfig(
        folders_to_delete=p.folders_to_delete,
        folders_video=p.folders_video,
        folders_compressed=p.folders_compressed,
        folders_pic=p.folders_pic,
        folders_audio=p.folders_audio,
        folders_misc=p.folders_misc,
        files_to_delete=p.files_to_delete,
        files_video_jav=p.files_video_jav,
        files_video_us=p.files_video_us,
        files_video_jav_vr=p.files_video_jav_vr,
        files_video_us_vr=p.files_video_us_vr,
        files_video_movie=p.files_video_movie,
        files_video_misc=p.files_video_misc,
        files_compressed=p.files_compressed,
        files_pic=p.files_pic,
        files_audio=p.files_audio,
        files_misc=p.files_misc,
        video_extensions={".mp4"},
        image_extensions={".jpg"},
        subtitle_extensions={".srt"},
        archive_extensions={".zip"},
        audio_extensions={".mp3"},
    )


def test_should_flatten_single_video_type() -> None:
    files = [Path("a.mp4"), Path("b.mp4")]
    assert should_flatten_small_dir(files, _cfg()) is True


def test_should_flatten_video_plus_cover_jpg() -> None:
    files = [Path("a.mp4"), Path("cover.jpg")]
    assert should_flatten_small_dir(files, _cfg()) is True


def test_should_flatten_rejects_unknown_extension() -> None:
    files = [Path("a.mp4"), Path("b.xyz")]
    assert should_flatten_small_dir(files, _cfg()) is False


def test_should_flatten_rejects_too_many_files() -> None:
    files = [Path(f"{i}.mp4") for i in range(6)]
    assert should_flatten_small_dir(files, _cfg()) is False


# --- _flatten_kinds_allowed 组合逻辑 ---


def test_flatten_allowed_single_image() -> None:
    assert _flatten_kinds_allowed({"image"}) is True


def test_flatten_allowed_single_audio() -> None:
    assert _flatten_kinds_allowed({"audio"}) is True


def test_flatten_allowed_single_archive() -> None:
    assert _flatten_kinds_allowed({"archive"}) is True


def test_flatten_allowed_video_plus_subtitle() -> None:
    # 字幕是视频的伴随类型
    assert _flatten_kinds_allowed({"video", "subtitle"}) is True


def test_flatten_allowed_video_plus_image_plus_subtitle() -> None:
    # video + 字幕 + cover 图同时存在
    assert _flatten_kinds_allowed({"video", "image", "subtitle"}) is True


def test_flatten_allowed_video_plus_image() -> None:
    # 二元组合中 image 总允许（如 cover.jpg + 视频）
    assert _flatten_kinds_allowed({"video", "image"}) is True


def test_flatten_allowed_audio_plus_image() -> None:
    # 二元组合中 image 总允许
    assert _flatten_kinds_allowed({"audio", "image"}) is True


def test_flatten_rejected_video_plus_audio() -> None:
    # video + audio 既不属于「单一 kind」也不属于「二元含 image」也不属于「video 伴随类型」
    assert _flatten_kinds_allowed({"video", "audio"}) is False


def test_flatten_rejected_multi_without_image_or_video() -> None:
    # 多类型且既无 image 也无 video 包裹
    assert _flatten_kinds_allowed({"audio", "archive"}) is False


def test_flatten_rejected_three_kinds_without_video() -> None:
    # 三元 kind 但不以 video 为骨架
    assert _flatten_kinds_allowed({"audio", "archive", "image"}) is False


# --- should_flatten_small_dir 扩展场景 ---


def test_should_flatten_video_plus_subtitle_and_cover() -> None:
    files = [Path("a.mp4"), Path("a.srt"), Path("cover.jpg")]
    assert should_flatten_small_dir(files, _cfg()) is True


def test_should_flatten_empty_files_rejected() -> None:
    assert should_flatten_small_dir([], _cfg()) is False


def test_should_flatten_exactly_five_allowed() -> None:
    files = [Path(f"{i}.mp4") for i in range(5)]
    assert should_flatten_small_dir(files, _cfg()) is True


# --- _collect_descendant_file_media_kinds 异常处理 ---


def test_collect_kinds_returns_empty_when_directory_missing(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
) -> None:
    # FileNotFoundError → 空 set（防止整目录分类崩溃）
    config = raw_analyze_config_factory(tmp_path)
    result = _collect_descendant_file_media_kinds(
        tmp_path / "does_not_exist",
        config,
    )
    assert result == set()


def test_collect_kinds_returns_empty_when_path_is_file(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
) -> None:
    # NotADirectoryError → 空 set（仍按 misc 分类继续）
    config = raw_analyze_config_factory(tmp_path)
    plain_file = tmp_path / "regular.txt"
    plain_file.write_text("x")
    result = _collect_descendant_file_media_kinds(plain_file, config)
    assert result == set()


def test_collect_kinds_aggregates_descendant_kinds(
    tmp_path: Path,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
) -> None:
    # 多层嵌套时返回所有出现过的 kind（包括 unknown）
    config = raw_analyze_config_factory(tmp_path)
    root = tmp_path / "tree"
    root.mkdir()
    (root / "a.mp4").write_text("v")
    (root / "sub").mkdir()
    (root / "sub" / "b.jpg").write_text("i")
    (root / "sub" / "c.xyz").write_text("u")

    result = _collect_descendant_file_media_kinds(root, config)
    assert result == {"video", "image", "unknown"}
