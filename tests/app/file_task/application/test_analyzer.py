"""文件分析器单元测试

覆盖 analyze_file 各分支：VIDEO/IMAGE/SUBTITLE、ARCHIVE、MISC。
"""

from collections.abc import Callable
from pathlib import Path

import pytest

from j_file_kit.app.file_task.application.analyzer import analyze_file
from j_file_kit.app.file_task.application.config import AnalyzeConfig
from j_file_kit.app.file_task.domain.decisions import (
    DeleteDecision,
    MoveDecision,
    SkipDecision,
)
from j_file_kit.app.file_task.domain.models import FileType

pytestmark = pytest.mark.unit


class TestAnalyzeFileVideoImage:
    """视频/图片文件分析"""

    def test_video_with_serial_moves_to_sorted(
        self,
        analyze_config_factory: Callable[..., AnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(sorted_dir=tmp_path / "sorted")
        path = tmp_path / "ABC-123_video.mp4"
        path.touch()
        decision = analyze_file(path, config)
        assert isinstance(decision, MoveDecision)
        assert decision.serial_id is not None
        assert "sorted" in str(decision.target_path)

    def test_video_without_serial_moves_to_unsorted(
        self,
        analyze_config_factory: Callable[..., AnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(unsorted_dir=tmp_path / "unsorted")
        path = tmp_path / "no_serial.mp4"
        path.touch()
        decision = analyze_file(path, config)
        assert isinstance(decision, MoveDecision)
        assert decision.serial_id is None
        assert decision.target_path == tmp_path / "unsorted" / "no_serial.mp4"

    def test_video_with_serial_sorted_dir_none_skips(
        self,
        analyze_config_factory: Callable[..., AnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(sorted_dir=None)
        path = tmp_path / "ABC-123.mp4"
        path.touch()
        decision = analyze_file(path, config)
        assert isinstance(decision, SkipDecision)
        assert "sorted_dir" in decision.reason

    def test_video_without_serial_unsorted_dir_none_skips(
        self,
        analyze_config_factory: Callable[..., AnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(unsorted_dir=None)
        path = tmp_path / "no_serial.mp4"
        path.touch()
        decision = analyze_file(path, config)
        assert isinstance(decision, SkipDecision)
        assert "unsorted_dir" in decision.reason

    def test_image_classified_correctly(
        self,
        analyze_config_factory: Callable[..., AnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(
            sorted_dir=tmp_path / "sorted",
            unsorted_dir=tmp_path / "unsorted",
        )
        path = tmp_path / "ABC-001.jpg"
        path.touch()
        decision = analyze_file(path, config)
        assert isinstance(decision, MoveDecision)
        assert decision.file_type == FileType.IMAGE


class TestAnalyzeFileSubtitle:
    """字幕文件分析：与视频/图片使用相同的媒体规则"""

    def test_subtitle_with_serial_moves_to_sorted(
        self,
        analyze_config_factory: Callable[..., AnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(sorted_dir=tmp_path / "sorted")
        path = tmp_path / "ABC-123.srt"
        path.touch()
        decision = analyze_file(path, config)
        assert isinstance(decision, MoveDecision)
        assert decision.file_type == FileType.SUBTITLE
        assert decision.serial_id is not None
        assert "sorted" in str(decision.target_path)

    def test_subtitle_without_serial_moves_to_unsorted(
        self,
        analyze_config_factory: Callable[..., AnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(unsorted_dir=tmp_path / "unsorted")
        path = tmp_path / "no_serial.srt"
        path.touch()
        decision = analyze_file(path, config)
        assert isinstance(decision, MoveDecision)
        assert decision.file_type == FileType.SUBTITLE
        assert decision.serial_id is None
        assert decision.target_path == tmp_path / "unsorted" / "no_serial.srt"

    def test_subtitle_with_serial_sorted_dir_none_skips(
        self,
        analyze_config_factory: Callable[..., AnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(sorted_dir=None)
        path = tmp_path / "ABC-123.ass"
        path.touch()
        decision = analyze_file(path, config)
        assert isinstance(decision, SkipDecision)
        assert "sorted_dir" in decision.reason

    def test_subtitle_without_serial_unsorted_dir_none_skips(
        self,
        analyze_config_factory: Callable[..., AnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(unsorted_dir=None)
        path = tmp_path / "no_serial.ass"
        path.touch()
        decision = analyze_file(path, config)
        assert isinstance(decision, SkipDecision)
        assert "unsorted_dir" in decision.reason


class TestAnalyzeFileArchive:
    """压缩文件分析"""

    def test_archive_moves_to_archive_dir(
        self,
        analyze_config_factory: Callable[..., AnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(archive_dir=tmp_path / "archive")
        path = tmp_path / "data.zip"
        path.touch()
        decision = analyze_file(path, config)
        assert isinstance(decision, MoveDecision)
        assert decision.target_path == tmp_path / "archive" / "data.zip"

    def test_archive_dir_none_skips(
        self,
        analyze_config_factory: Callable[..., AnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(archive_dir=None)
        path = tmp_path / "data.zip"
        path.touch()
        decision = analyze_file(path, config)
        assert isinstance(decision, SkipDecision)
        assert "archive_dir" in decision.reason


class TestAnalyzeFileMisc:
    """Misc 文件分析"""

    def test_misc_extension_delete_rule(
        self,
        analyze_config_factory: Callable[..., AnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(
            misc_dir=tmp_path / "misc",
            misc_file_delete_rules={"extensions": [".tmp", ".bak"]},
        )
        path = tmp_path / "temp.tmp"
        path.touch()
        decision = analyze_file(path, config)
        assert isinstance(decision, DeleteDecision)
        assert "扩展名" in decision.reason

    def test_misc_size_keyword_delete_rule(
        self,
        analyze_config_factory: Callable[..., AnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(
            misc_dir=tmp_path / "misc",
            misc_file_delete_rules={
                "keywords": ["sample"],
                "max_size": 1024,
            },
        )
        path = tmp_path / "sample_preview.xyz"
        path.write_bytes(b"x" * 100)
        decision = analyze_file(path, config)
        assert isinstance(decision, DeleteDecision)
        assert "文件大小" in decision.reason

    def test_misc_no_delete_rule_moves_to_misc(
        self,
        analyze_config_factory: Callable[..., AnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(misc_dir=tmp_path / "misc")
        path = tmp_path / "other.xyz"
        path.touch()
        decision = analyze_file(path, config)
        assert isinstance(decision, MoveDecision)
        assert decision.target_path == tmp_path / "misc" / "other.xyz"

    def test_misc_dir_none_skips(
        self,
        analyze_config_factory: Callable[..., AnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(misc_dir=None)
        path = tmp_path / "other.xyz"
        path.touch()
        decision = analyze_file(path, config)
        assert isinstance(decision, SkipDecision)
        assert "misc_dir" in decision.reason

    def test_misc_empty_rules_no_delete(
        self,
        analyze_config_factory: Callable[..., AnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(
            misc_dir=tmp_path / "misc",
            misc_file_delete_rules={},
        )
        path = tmp_path / "other.xyz"
        path.touch()
        decision = analyze_file(path, config)
        assert isinstance(decision, MoveDecision)


class TestAnalyzeFileSurrogateName:
    """含 surrogate escape 文件名的处理测试

    验证目标路径中的文件名已被安全化（不含代理字符），
    同时源路径保持原样（供实际 OS rename 调用使用）。
    """

    def test_surrogate_name_image_unsorted_target_is_safe(
        self,
        analyze_config_factory: Callable[..., AnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(unsorted_dir=tmp_path / "unsorted")
        # 模拟 Linux surrogateescape 产生的含代理字符路径
        surrogate_name = "+\udcfe\udca6+\udccb.jpg"
        path = tmp_path / surrogate_name
        decision = analyze_file(path, config)
        assert isinstance(decision, MoveDecision)
        # 目标文件名不含代理字符，可安全编码为 UTF-8
        target_name = decision.target_path.name
        target_name.encode("utf-8")  # 不抛出则通过
        assert "\udcfe" not in target_name

    def test_surrogate_name_archive_target_is_safe(
        self,
        analyze_config_factory: Callable[..., AnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(archive_dir=tmp_path / "archive")
        surrogate_name = "data\udcfe.zip"
        path = tmp_path / surrogate_name
        decision = analyze_file(path, config)
        assert isinstance(decision, MoveDecision)
        target_name = decision.target_path.name
        target_name.encode("utf-8")
        assert "\udcfe" not in target_name

    def test_surrogate_name_misc_target_is_safe(
        self,
        analyze_config_factory: Callable[..., AnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(misc_dir=tmp_path / "misc")
        surrogate_name = "file\udcfe.xyz"
        path = tmp_path / surrogate_name
        decision = analyze_file(path, config)
        assert isinstance(decision, MoveDecision)
        target_name = decision.target_path.name
        target_name.encode("utf-8")
        assert "\udcfe" not in target_name

    def test_surrogate_name_sorted_video_target_is_safe(
        self,
        analyze_config_factory: Callable[..., AnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(sorted_dir=tmp_path / "sorted")
        # 有番号但文件名含代理字符，验证 sorted 分支目标路径同样安全
        path = tmp_path / "ABC-123\udcfe.mp4"
        decision = analyze_file(path, config)
        assert isinstance(decision, MoveDecision)
        assert decision.serial_id is not None
        target_name = decision.target_path.name
        target_name.encode("utf-8")  # 不抛出则通过
        assert "\udcfe" not in target_name

    def test_source_path_preserved_with_surrogates(
        self,
        analyze_config_factory: Callable[..., AnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(unsorted_dir=tmp_path / "unsorted")
        surrogate_name = "file\udcfe.jpg"
        path = tmp_path / surrogate_name
        decision = analyze_file(path, config)
        assert isinstance(decision, MoveDecision)
        # 源路径保持原样（OS rename 需要原始字节）
        assert decision.source_path == path


class TestAnalyzeFileMiscDeleteRulesMaxSizeValidation:
    """_check_misc_delete_rules max_size 类型验证（通过 analyze_file 间接）"""

    def test_max_size_non_numeric_raises(
        self,
        analyze_config_factory: Callable[..., AnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(
            misc_dir=tmp_path / "misc",
            misc_file_delete_rules={"keywords": ["x"], "max_size": "invalid"},
        )
        path = tmp_path / "x.xyz"
        path.touch()
        with pytest.raises(ValueError, match="max_size 必须为数字类型"):
            analyze_file(path, config)
