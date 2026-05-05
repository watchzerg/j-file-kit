"""analyze_jav_file：压缩包、misc、surrogate 文件名相关测试。"""

from collections.abc import Callable
from pathlib import Path

import pytest

from j_file_kit.app.file_task.application.jav_analysis.runner import analyze_jav_file
from j_file_kit.app.file_task.application.jav_analyze_config import JavAnalyzeConfig
from j_file_kit.app.file_task.domain.decisions import (
    DeleteDecision,
    MoveDecision,
    SkipDecision,
)

pytestmark = pytest.mark.unit


class TestAnalyzeJavFileArchive:
    def test_archive_moves_to_archive_dir(
        self,
        analyze_config_factory: Callable[..., JavAnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(archive_dir=tmp_path / "archive")
        path = tmp_path / "data.zip"
        path.touch()
        decision = analyze_jav_file(path, config)
        assert isinstance(decision, MoveDecision)
        assert decision.target_path == tmp_path / "archive" / "data.zip"

    def test_archive_dir_none_skips(
        self,
        analyze_config_factory: Callable[..., JavAnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(archive_dir=None)
        path = tmp_path / "data.zip"
        path.touch()
        decision = analyze_jav_file(path, config)
        assert isinstance(decision, SkipDecision)
        assert "archive_dir" in decision.reason


class TestAnalyzeJavFileMisc:
    def test_misc_extension_delete_rule(
        self,
        analyze_config_factory: Callable[..., JavAnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(
            misc_dir=tmp_path / "misc",
            misc_file_delete_rules={"extensions": [".tmp", ".bak"]},
        )
        path = tmp_path / "noise_file.tmp"
        path.touch()
        decision = analyze_jav_file(path, config)
        assert isinstance(decision, DeleteDecision)
        assert "扩展名" in decision.reason

    def test_misc_size_delete_rule(
        self,
        analyze_config_factory: Callable[..., JavAnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(
            misc_dir=tmp_path / "misc",
            misc_file_delete_rules={"max_size": 1024},
        )
        path = tmp_path / "normal_name.xyz"
        path.write_bytes(b"x" * 100)
        decision = analyze_jav_file(path, config)
        assert isinstance(decision, DeleteDecision)
        assert "Misc 体积删除规则" in decision.reason

    def test_misc_no_delete_rule_moves_to_misc(
        self,
        analyze_config_factory: Callable[..., JavAnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(misc_dir=tmp_path / "misc")
        path = tmp_path / "other.xyz"
        path.touch()
        decision = analyze_jav_file(path, config)
        assert isinstance(decision, MoveDecision)
        assert decision.target_path == tmp_path / "misc" / "other.xyz"

    def test_misc_dir_none_skips(
        self,
        analyze_config_factory: Callable[..., JavAnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(misc_dir=None)
        path = tmp_path / "other.xyz"
        path.touch()
        decision = analyze_jav_file(path, config)
        assert isinstance(decision, SkipDecision)
        assert "misc_dir" in decision.reason

    def test_misc_empty_rules_no_delete(
        self,
        analyze_config_factory: Callable[..., JavAnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(
            misc_dir=tmp_path / "misc",
            misc_file_delete_rules={},
        )
        path = tmp_path / "other.xyz"
        path.touch()
        decision = analyze_jav_file(path, config)
        assert isinstance(decision, MoveDecision)


class TestAnalyzeJavFileSurrogateName:
    def test_surrogate_name_image_without_serial_deleted(
        self,
        analyze_config_factory: Callable[..., JavAnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(unsorted_dir=tmp_path / "unsorted")
        surrogate_name = "+\udcfe\udca6+\udccb.jpg"
        path = tmp_path / surrogate_name
        decision = analyze_jav_file(path, config)
        assert isinstance(decision, DeleteDecision)
        assert decision.source_path == path

    def test_surrogate_name_archive_target_is_safe(
        self,
        analyze_config_factory: Callable[..., JavAnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(archive_dir=tmp_path / "archive")
        surrogate_name = "data\udcfe.zip"
        path = tmp_path / surrogate_name
        decision = analyze_jav_file(path, config)
        assert isinstance(decision, MoveDecision)
        target_name = decision.target_path.name
        target_name.encode("utf-8")
        assert "\udcfe" not in target_name

    def test_surrogate_name_misc_target_is_safe(
        self,
        analyze_config_factory: Callable[..., JavAnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(misc_dir=tmp_path / "misc")
        surrogate_name = "file\udcfe.xyz"
        path = tmp_path / surrogate_name
        decision = analyze_jav_file(path, config)
        assert isinstance(decision, MoveDecision)
        target_name = decision.target_path.name
        target_name.encode("utf-8")
        assert "\udcfe" not in target_name

    def test_surrogate_name_sorted_video_target_is_safe(
        self,
        analyze_config_factory: Callable[..., JavAnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(sorted_dir=tmp_path / "sorted")
        path = tmp_path / "ABC-123\udcfe.mp4"
        decision = analyze_jav_file(path, config)
        assert isinstance(decision, MoveDecision)
        assert decision.serial_id is not None
        target_name = decision.target_path.name
        target_name.encode("utf-8")
        assert "\udcfe" not in target_name

    def test_source_path_preserved_with_surrogates(
        self,
        analyze_config_factory: Callable[..., JavAnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(unsorted_dir=tmp_path / "unsorted")
        surrogate_name = "file\udcfe.mp4"
        path = tmp_path / surrogate_name
        decision = analyze_jav_file(path, config)
        assert isinstance(decision, MoveDecision)
        assert decision.source_path == path


class TestAnalyzeJavFileMiscDeleteRulesMaxSizeValidation:
    def test_max_size_non_numeric_raises(
        self,
        analyze_config_factory: Callable[..., JavAnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(
            misc_dir=tmp_path / "misc",
            misc_file_delete_rules={"max_size": "invalid"},
        )
        path = tmp_path / "x.xyz"
        path.touch()
        with pytest.raises(ValueError, match="max_size 必须为数字类型"):
            analyze_jav_file(path, config)
