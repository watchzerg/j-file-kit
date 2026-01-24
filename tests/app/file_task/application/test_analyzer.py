from pathlib import Path

import pytest

from j_file_kit.app.file_task.application.analyzer import analyze_file
from j_file_kit.app.file_task.application.config import AnalyzeConfig
from j_file_kit.app.file_task.application.jav_filename_util import (
    generate_jav_filename,
    generate_sorted_dir,
)
from j_file_kit.app.file_task.domain.decisions import (
    DeleteDecision,
    MoveDecision,
    SkipDecision,
)
from j_file_kit.app.file_task.domain.models import FileType

pytestmark = pytest.mark.unit


def _config(tmp_path: Path) -> AnalyzeConfig:
    return AnalyzeConfig(
        video_extensions={".mp4"},
        image_extensions={".jpg"},
        archive_extensions={".zip"},
        sorted_dir=tmp_path / "sorted",
        unsorted_dir=tmp_path / "unsorted",
        archive_dir=tmp_path / "archive",
        misc_dir=tmp_path / "misc",
        misc_file_delete_rules={},
    )


def test_analyze_file_misc_delete_by_extension(tmp_path: Path) -> None:
    config = _config(tmp_path)
    config.misc_file_delete_rules = {"extensions": [".tmp"]}
    path = tmp_path / "trash.tmp"

    decision = analyze_file(path, config)

    assert isinstance(decision, DeleteDecision)
    assert decision.file_type == FileType.MISC
    assert "扩展名" in decision.reason


def test_analyze_file_misc_delete_by_size_and_keyword(tmp_path: Path) -> None:
    config = _config(tmp_path)
    config.misc_file_delete_rules = {"keywords": ["sample"], "max_size": 10}
    path = tmp_path / "sample.txt"
    path.write_text("x")

    decision = analyze_file(path, config)

    assert isinstance(decision, DeleteDecision)
    assert "文件大小" in decision.reason


def test_analyze_file_misc_skip_when_no_misc_dir(tmp_path: Path) -> None:
    config = _config(tmp_path)
    config.misc_dir = None
    path = tmp_path / "note.txt"

    decision = analyze_file(path, config)

    assert isinstance(decision, SkipDecision)
    assert "misc_dir 未设置" in decision.reason


def test_analyze_file_misc_moves_to_misc_dir(tmp_path: Path) -> None:
    config = _config(tmp_path)
    path = tmp_path / "note.txt"

    decision = analyze_file(path, config)

    assert isinstance(decision, MoveDecision)
    assert decision.file_type == FileType.MISC
    assert config.misc_dir is not None
    assert decision.target_path == config.misc_dir / path.name


def test_analyze_file_archive_moves_to_archive_dir(tmp_path: Path) -> None:
    config = _config(tmp_path)
    path = tmp_path / "archive.zip"

    decision = analyze_file(path, config)

    assert isinstance(decision, MoveDecision)
    assert config.archive_dir is not None
    assert decision.target_path == config.archive_dir / path.name


def test_analyze_file_archive_skips_without_archive_dir(tmp_path: Path) -> None:
    config = _config(tmp_path)
    config.archive_dir = None
    path = tmp_path / "archive.zip"

    decision = analyze_file(path, config)

    assert isinstance(decision, SkipDecision)
    assert "archive_dir 未设置" in decision.reason


def test_analyze_file_media_with_serial_moves_sorted(tmp_path: Path) -> None:
    config = _config(tmp_path)
    path = tmp_path / "ABC-123_video.mp4"
    new_filename, serial_id = generate_jav_filename(path.name)

    decision = analyze_file(path, config)

    assert isinstance(decision, MoveDecision)
    assert decision.serial_id == serial_id
    assert config.sorted_dir is not None
    assert serial_id is not None
    assert (
        decision.target_path
        == config.sorted_dir / generate_sorted_dir(serial_id) / new_filename
    )


def test_analyze_file_media_without_serial_moves_unsorted(tmp_path: Path) -> None:
    config = _config(tmp_path)
    path = tmp_path / "no_serial.mp4"

    decision = analyze_file(path, config)

    assert isinstance(decision, MoveDecision)
    assert decision.serial_id is None
    assert config.unsorted_dir is not None
    assert decision.target_path == config.unsorted_dir / path.name


def test_analyze_file_media_skips_without_unsorted_dir(tmp_path: Path) -> None:
    config = _config(tmp_path)
    config.unsorted_dir = None
    path = tmp_path / "no_serial.mp4"

    decision = analyze_file(path, config)

    assert isinstance(decision, SkipDecision)
    assert "unsorted_dir 未设置" in decision.reason


def test_analyze_file_media_skips_without_sorted_dir(tmp_path: Path) -> None:
    config = _config(tmp_path)
    config.sorted_dir = None
    path = tmp_path / "ABC-123_video.mp4"

    decision = analyze_file(path, config)

    assert isinstance(decision, SkipDecision)
    assert "sorted_dir 未设置" in decision.reason
