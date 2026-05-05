"""RawFileOrganizer 单元测试。"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from j_file_kit.app.file_task.application.raw_file_organizer import RawFileOrganizer
from j_file_kit.app.file_task.domain.constants import TASK_TYPE_RAW_FILE_ORGANIZER
from j_file_kit.app.file_task.domain.task_config import TaskConfig
from j_file_kit.app.file_task.domain.task_run import FileTaskRunStatistics

pytestmark = pytest.mark.unit


def test_task_type(tmp_path: Path) -> None:
    tc = TaskConfig(
        type=TASK_TYPE_RAW_FILE_ORGANIZER,
        enabled=True,
        config={
            "inbox_dir": "/media/raw_workspace/inbox",
        },
    )
    org = RawFileOrganizer(
        task_config=tc,
        log_dir=tmp_path / "logs",
        file_result_repository=MagicMock(),
    )
    assert org.task_type == TASK_TYPE_RAW_FILE_ORGANIZER


def test_run_requires_inbox(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "j_file_kit.app.file_task.application.config_common.RAW_MEDIA_ROOT",
        tmp_path,
    )
    tc = TaskConfig(
        type=TASK_TYPE_RAW_FILE_ORGANIZER,
        enabled=True,
        config={"inbox_dir": None},
    )
    org = RawFileOrganizer(
        task_config=tc,
        log_dir=tmp_path / "logs",
        file_result_repository=MagicMock(),
    )
    with pytest.raises(ValueError, match="inbox_dir"):
        org.run(run_id=1)


def test_run_returns_empty_statistics(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "j_file_kit.app.file_task.application.config_common.RAW_MEDIA_ROOT",
        tmp_path,
    )
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    tc = TaskConfig(
        type=TASK_TYPE_RAW_FILE_ORGANIZER,
        enabled=True,
        config={"inbox_dir": str(inbox)},
    )
    repo = MagicMock()
    repo.get_statistics.return_value = {
        "total_items": 0,
        "success_items": 0,
        "error_items": 0,
        "skipped_items": 0,
        "warning_items": 0,
        "total_duration_ms": 0.0,
    }
    org = RawFileOrganizer(
        task_config=tc,
        log_dir=tmp_path / "logs",
        file_result_repository=repo,
    )
    assert org.run(run_id=1) == FileTaskRunStatistics()
