"""JAV 文件分析器单元测试

覆盖 analyze_jav_file 各分支：收件箱预删除（InboxDeleteRules）、VIDEO/IMAGE/SUBTITLE、
ARCHIVE、MISC，以及 surrogate 文件名与 misc 删除规则校验等。
"""

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from j_file_kit.app.file_task.application.config import (
    InboxDeleteRules,
    JavAnalyzeConfig,
)
from j_file_kit.app.file_task.application.jav_analyzer import analyze_jav_file
from j_file_kit.app.file_task.domain.decisions import (
    DeleteDecision,
    MoveDecision,
    SkipDecision,
)
from j_file_kit.app.file_task.domain.models import FileType
from j_file_kit.app.file_task.domain.organizer_defaults import (
    DEFAULT_PROBABLE_JUNK_MEDIA_KEYWORDS,
)

pytestmark = pytest.mark.unit


class TestAnalyzeJavFileInboxDelete:
    """收件箱预删除（扩展名分类前）"""

    def test_exact_stem_deletes_with_unclassified(
        self,
        analyze_config_factory: Callable[..., JavAnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(
            archive_dir=tmp_path / "archive",
            inbox_delete_rules=InboxDeleteRules(exact_stems={"Thumbs"}),
        )
        path = tmp_path / "Thumbs.zip"
        path.touch()
        decision = analyze_jav_file(path, config)
        assert isinstance(decision, DeleteDecision)
        assert decision.file_type == FileType.UNCLASSIFIED
        assert "完全匹配" in decision.reason

    def test_default_keyword_in_stem_deletes(
        self,
        analyze_config_factory: Callable[..., JavAnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(
            sorted_dir=tmp_path / "sorted",
        )
        kw = DEFAULT_PROBABLE_JUNK_MEDIA_KEYWORDS[0]
        path = tmp_path / f"foo_{kw}_bar.mp4"
        path.touch()
        decision = analyze_jav_file(path, config)
        assert isinstance(decision, DeleteDecision)
        assert decision.file_type == FileType.UNCLASSIFIED

    def test_max_size_zero_deletes_empty_file(
        self,
        analyze_config_factory: Callable[..., JavAnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(
            inbox_delete_rules=InboxDeleteRules(max_size_bytes=0),
        )
        path = tmp_path / "empty.mp4"
        path.touch()
        decision = analyze_jav_file(path, config)
        assert isinstance(decision, DeleteDecision)
        assert decision.file_type == FileType.UNCLASSIFIED
        assert "0" in decision.reason

    def test_empty_inbox_rules_does_not_delete(
        self,
        analyze_config_factory: Callable[..., JavAnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(sorted_dir=tmp_path / "sorted")
        path = tmp_path / "ABC-100.mp4"
        path.touch()
        decision = analyze_jav_file(path, config)
        assert isinstance(decision, MoveDecision)

    def test_size_rule_skips_when_stat_fails(
        self,
        analyze_config_factory: Callable[..., JavAnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(
            unsorted_dir=tmp_path / "unsorted",
            inbox_delete_rules=InboxDeleteRules(max_size_bytes=0),
        )
        path = tmp_path / "no_serial.mp4"
        path.touch()

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
        assert decision.file_type == FileType.VIDEO


class TestAnalyzeJavFileVideoSmallDelete:
    """视频小体积直接删除（不看文件名）"""

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
        """stat 失败时不按小体积删除，继续走番号/无番号逻辑。"""
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


class TestAnalyzeJavFileVideoImage:
    """视频/图片文件分析"""

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


class TestAnalyzeJavFileSubtitle:
    """字幕文件分析：与视频/图片使用相同的媒体规则"""

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


class TestAnalyzeJavFileArchive:
    """压缩文件分析"""

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
    """Misc 文件分析"""

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
            misc_file_delete_rules={
                "max_size": 1024,
            },
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
    """含 surrogate escape 文件名的处理测试

    验证目标路径中的文件名已被安全化（不含代理字符），
    同时源路径保持原样（供实际 OS rename 调用使用）。
    """

    def test_surrogate_name_image_without_serial_deleted(
        self,
        analyze_config_factory: Callable[..., JavAnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(unsorted_dir=tmp_path / "unsorted")
        # 模拟 Linux surrogateescape 产生的含代理字符路径；无番号图片走删除
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
        # 有番号但文件名含代理字符，验证 sorted 分支目标路径同样安全
        path = tmp_path / "ABC-123\udcfe.mp4"
        decision = analyze_jav_file(path, config)
        assert isinstance(decision, MoveDecision)
        assert decision.serial_id is not None
        target_name = decision.target_path.name
        target_name.encode("utf-8")  # 不抛出则通过
        assert "\udcfe" not in target_name

    def test_source_path_preserved_with_surrogates(
        self,
        analyze_config_factory: Callable[..., JavAnalyzeConfig],
        tmp_path: Path,
    ) -> None:
        config = analyze_config_factory(unsorted_dir=tmp_path / "unsorted")
        # 无番号视频走 unsorted，源路径保持原样（OS rename 需要原始字节）
        surrogate_name = "file\udcfe.mp4"
        path = tmp_path / surrogate_name
        decision = analyze_jav_file(path, config)
        assert isinstance(decision, MoveDecision)
        assert decision.source_path == path


class TestAnalyzeJavFileMiscDeleteRulesMaxSizeValidation:
    """_check_misc_delete_rules max_size 类型验证（通过 analyze_jav_file 间接）"""

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
