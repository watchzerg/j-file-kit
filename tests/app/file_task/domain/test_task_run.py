"""FileTaskRunReport 领域模型测试。"""

from datetime import datetime

import pytest

from j_file_kit.app.file_task.domain.task_run import FileTaskRunReport

pytestmark = pytest.mark.unit


def _new_report(
    total_items: int, success_items: int, error_items: int
) -> FileTaskRunReport:
    return FileTaskRunReport(
        run_name="test",
        start_time=datetime.now(),
        end_time=datetime.now(),
        total_items=total_items,
        success_items=success_items,
        error_items=error_items,
        skipped_items=0,
        warning_items=0,
        total_duration_ms=0.0,
    )


def test_success_rate() -> None:
    assert _new_report(0, 0, 0).success_rate == 0.0
    assert _new_report(10, 8, 0).success_rate == 0.8


def test_error_rate() -> None:
    assert _new_report(0, 0, 0).error_rate == 0.0
    assert _new_report(10, 0, 2).error_rate == 0.2


def test_duration_seconds() -> None:
    report = _new_report(0, 0, 0)
    report.total_duration_ms = 5000.0
    assert report.duration_seconds == 5.0


def test_update_from_stats() -> None:
    report = _new_report(0, 0, 0)
    report.update_from_stats(
        {
            "total_items": 5,
            "success_items": 3,
            "error_items": 1,
            "skipped_items": 1,
            "warning_items": 0,
            "total_duration_ms": 100.5,
        }
    )
    assert report.total_items == 5
    assert report.success_items == 3
    assert report.error_items == 1
    assert report.skipped_items == 1
    assert report.total_duration_ms == 100.5


def test_update_from_partial_stats_uses_default_for_missing_keys() -> None:
    report = _new_report(10, 0, 0)
    report.update_from_stats({"success_items": 7})
    assert report.success_items == 7
    assert report.total_items == 0
