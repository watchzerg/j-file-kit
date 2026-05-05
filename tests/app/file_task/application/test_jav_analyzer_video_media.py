"""analyze_jav_file：视频/图片/字幕与小体积删除规则测试。"""

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from j_file_kit.app.file_task.application.jav_analysis.runner import analyze_jav_file
from j_file_kit.app.file_task.application.jav_analyze_config import JavAnalyzeConfig
from j_file_kit.app.file_task.domain.decisions import (
    DeleteDecision,
    MoveDecision,
    SkipDecision,
)
from j_file_kit.app.file_task.domain.file_types import FileType

pytestmark = pytest.mark.unit


class TestAnalyzeJavFileVideoSmallDelete:
    def test_small_video_deleted_when_enabled(
        self,
        analyze_config_factory: Callable[..., JavAnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        threshold = 100
        config = analyze_config_factory(
            sorted_dir=tmp_path / "sorted",
            video_small_delete_bytes=threshold,
        )
        path = tmp_path / "anything.mp4"
        path.write_bytes(b"x" * (threshold - 1))
        decision = analyze_jav_file(path, config)
        assert isinstance(decision, DeleteDecision)
        assert decision.file_type == FileType.VIDEO
        assert "小体积直接删除" in decision.reason

    def test_video_size_equal_threshold_not_deleted(
        self,
        analyze_config_factory: Callable[..., JavAnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        threshold = 100
        config = analyze_config_factory(
            sorted_dir=tmp_path / "sorted",
            video_small_delete_bytes=threshold,
        )
        path = tmp_path / "ABC-100.mp4"
        path.write_bytes(b"x" * threshold)
        decision = analyze_jav_file(path, config)
        assert isinstance(decision, MoveDecision)

    def test_rule_disabled_when_none(
        self,
        analyze_config_factory: Callable[..., JavAnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(
            sorted_dir=tmp_path / "sorted",
            unsorted_dir=tmp_path / "unsorted",
            video_small_delete_bytes=None,
        )
        path = tmp_path / "tiny.mp4"
        path.write_bytes(b"x")
        decision = analyze_jav_file(path, config)
        assert isinstance(decision, MoveDecision)

    def test_video_small_delete_skips_when_stat_fails(
        self,
        analyze_config_factory: Callable[..., JavAnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(
            sorted_dir=tmp_path / "sorted",
            unsorted_dir=tmp_path / "unsorted",
            video_small_delete_bytes=1000,
        )
        path = tmp_path / "no_serial.mp4"
        path.write_bytes(b"x" * 10)
        real_stat = os.stat

        def fake_stat(
            p: str | bytes | os.PathLike[str] | int,
            *args: Any,
            **kwargs: Any,
        ) -> os.stat_result:
            if isinstance(p, int):
                return real_stat(p, *args, **kwargs)
            if os.fsdecode(p) == str(path):
                raise OSError("stat failed")
            return real_stat(p, *args, **kwargs)

        with patch("os.stat", fake_stat):
            decision = analyze_jav_file(path, config)
        assert isinstance(decision, MoveDecision)
        assert decision.target_path == tmp_path / "unsorted" / "no_serial.mp4"


class TestAnalyzeJavFileVideoImageSubtitle:
    def test_video_with_serial_moves_to_sorted(
        self,
        analyze_config_factory: Callable[..., JavAnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(sorted_dir=tmp_path / "sorted")
        path = tmp_path / "ABC-123_video.mp4"
        path.touch()
        decision = analyze_jav_file(path, config)
        assert isinstance(decision, MoveDecision)
        assert decision.serial_id is not None
        assert "sorted" in str(decision.target_path)

    def test_video_without_serial_moves_to_unsorted(
        self,
        analyze_config_factory: Callable[..., JavAnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(unsorted_dir=tmp_path / "unsorted")
        path = tmp_path / "no_serial.mp4"
        path.touch()
        decision = analyze_jav_file(path, config)
        assert isinstance(decision, MoveDecision)
        assert decision.serial_id is None
        assert decision.target_path == tmp_path / "unsorted" / "no_serial.mp4"

    def test_video_with_serial_sorted_dir_none_skips(
        self,
        analyze_config_factory: Callable[..., JavAnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(sorted_dir=None)
        path = tmp_path / "ABC-123.mp4"
        path.touch()
        decision = analyze_jav_file(path, config)
        assert isinstance(decision, SkipDecision)
        assert "sorted_dir" in decision.reason

    def test_video_without_serial_unsorted_dir_none_skips(
        self,
        analyze_config_factory: Callable[..., JavAnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(unsorted_dir=None)
        path = tmp_path / "no_serial.mp4"
        path.touch()
        decision = analyze_jav_file(path, config)
        assert isinstance(decision, SkipDecision)
        assert "unsorted_dir" in decision.reason

    def test_image_without_serial_deleted(
        self,
        analyze_config_factory: Callable[..., JavAnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(unsorted_dir=tmp_path / "unsorted")
        path = tmp_path / "no_serial.jpg"
        path.touch()
        decision = analyze_jav_file(path, config)
        assert isinstance(decision, DeleteDecision)
        assert decision.file_type == FileType.IMAGE
        assert "图片无番号" in decision.reason

    def test_image_without_serial_deleted_without_unsorted_dir(
        self,
        analyze_config_factory: Callable[..., JavAnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(unsorted_dir=None)
        path = tmp_path / "no_serial.jpg"
        path.touch()
        decision = analyze_jav_file(path, config)
        assert isinstance(decision, DeleteDecision)

    def test_image_classified_correctly(
        self,
        analyze_config_factory: Callable[..., JavAnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(
            sorted_dir=tmp_path / "sorted",
            unsorted_dir=tmp_path / "unsorted",
        )
        path = tmp_path / "ABC-100.jpg"
        path.touch()
        decision = analyze_jav_file(path, config)
        assert isinstance(decision, MoveDecision)
        assert decision.file_type == FileType.IMAGE

    def test_subtitle_with_serial_moves_to_sorted(
        self,
        analyze_config_factory: Callable[..., JavAnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(sorted_dir=tmp_path / "sorted")
        path = tmp_path / "ABC-123.srt"
        path.touch()
        decision = analyze_jav_file(path, config)
        assert isinstance(decision, MoveDecision)
        assert decision.file_type == FileType.SUBTITLE
        assert decision.serial_id is not None
        assert "sorted" in str(decision.target_path)

    def test_subtitle_without_serial_moves_to_unsorted(
        self,
        analyze_config_factory: Callable[..., JavAnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(unsorted_dir=tmp_path / "unsorted")
        path = tmp_path / "no_serial.srt"
        path.touch()
        decision = analyze_jav_file(path, config)
        assert isinstance(decision, MoveDecision)
        assert decision.file_type == FileType.SUBTITLE
        assert decision.serial_id is None
        assert decision.target_path == tmp_path / "unsorted" / "no_serial.srt"

    def test_subtitle_with_serial_sorted_dir_none_skips(
        self,
        analyze_config_factory: Callable[..., JavAnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(sorted_dir=None)
        path = tmp_path / "ABC-123.ass"
        path.touch()
        decision = analyze_jav_file(path, config)
        assert isinstance(decision, SkipDecision)
        assert "sorted_dir" in decision.reason

    def test_subtitle_without_serial_unsorted_dir_none_skips(
        self,
        analyze_config_factory: Callable[..., JavAnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(unsorted_dir=None)
        path = tmp_path / "no_serial.ass"
        path.touch()
        decision = analyze_jav_file(path, config)
        assert isinstance(decision, SkipDecision)
        assert "unsorted_dir" in decision.reason
