from datetime import datetime

import pytest

from j_file_kit.app.file_task.domain.models import FileTaskRunReport

pytestmark = pytest.mark.unit


def test_file_task_run_report_rates_with_zero_total() -> None:
    report = FileTaskRunReport(
        run_name="demo",
        start_time=datetime(2024, 1, 1),
        end_time=datetime(2024, 1, 1),
        total_items=0,
        success_items=0,
        error_items=0,
        skipped_items=0,
        warning_items=0,
        total_duration_ms=0.0,
    )

    assert report.success_rate == 0.0
    assert report.error_rate == 0.0


def test_file_task_run_report_rates_with_items() -> None:
    report = FileTaskRunReport(
        run_name="demo",
        start_time=datetime(2024, 1, 1),
        end_time=datetime(2024, 1, 1),
        total_items=10,
        success_items=7,
        error_items=2,
        skipped_items=0,
        warning_items=1,
        total_duration_ms=0.0,
    )

    assert report.success_rate == 0.7
    assert report.error_rate == 0.2


def test_file_task_run_report_duration_seconds() -> None:
    report = FileTaskRunReport(
        run_name="demo",
        start_time=datetime(2024, 1, 1),
        end_time=datetime(2024, 1, 1),
        total_items=0,
        success_items=0,
        error_items=0,
        skipped_items=0,
        warning_items=0,
        total_duration_ms=2500.0,
    )

    assert report.duration_seconds == 2.5


def test_file_task_run_report_update_from_stats_fills_defaults() -> None:
    report = FileTaskRunReport(
        run_name="demo",
        start_time=datetime(2024, 1, 1),
        end_time=datetime(2024, 1, 1),
        total_items=0,
        success_items=0,
        error_items=0,
        skipped_items=0,
        warning_items=0,
        total_duration_ms=0.0,
    )

    report.update_from_stats({"total_items": 3, "success_items": 2})

    assert report.total_items == 3
    assert report.success_items == 2
    assert report.error_items == 0
    assert report.skipped_items == 0
    assert report.warning_items == 0
    assert report.total_duration_ms == 0.0
