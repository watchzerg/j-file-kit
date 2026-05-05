"""analyze_jav_file：收件箱预删除规则与异常回退测试。"""

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from j_file_kit.app.file_task.application.config_common import InboxDeleteRules
from j_file_kit.app.file_task.application.jav_analysis.runner import analyze_jav_file
from j_file_kit.app.file_task.application.jav_analyze_config import JavAnalyzeConfig
from j_file_kit.app.file_task.domain.decisions import DeleteDecision, MoveDecision
from j_file_kit.app.file_task.domain.file_types import FileType
from j_file_kit.app.file_task.domain.organizer_defaults import (
    DEFAULT_PROBABLE_JUNK_MEDIA_KEYWORDS,
)

pytestmark = pytest.mark.unit


class TestAnalyzeJavFileInboxDelete:
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
        config = analyze_config_factory(sorted_dir=tmp_path / "sorted")
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
