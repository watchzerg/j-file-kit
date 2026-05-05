"""RawFilePipeline 占位行为单元测试。"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from j_file_kit.app.file_task.application.config import RawAnalyzeConfig
from j_file_kit.app.file_task.application.raw_pipeline import RawFilePipeline
from j_file_kit.app.file_task.domain.models import FileTaskRunStatistics

pytestmark = pytest.mark.unit


def test_run_returns_empty_statistics(tmp_path: Path) -> None:
    """本期管道不处理任何项，统计全零。"""
    cfg = RawAnalyzeConfig(
        video_extensions={".mp4"},
        image_extensions={".jpg"},
        subtitle_extensions={".srt"},
        archive_extensions={".zip"},
        audio_extensions={".mp3"},
    )
    pipe = RawFilePipeline(
        run_id=1,
        run_name="raw_file_organizer",
        scan_root=tmp_path / "inbox",
        analyze_config=cfg,
        log_dir=tmp_path / "logs",
        file_result_repository=MagicMock(),
    )
    stats = pipe.run()
    assert stats == FileTaskRunStatistics()
