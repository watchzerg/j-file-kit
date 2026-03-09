import threading
from datetime import datetime

import pytest

from j_file_kit.app.file_task.domain.constants import TASK_TYPE_JAV_VIDEO_ORGANIZER
from j_file_kit.app.file_task.domain.models import (
    FileTaskAlreadyRunningError,
    FileTaskCancelledError,
    FileTaskNotFoundError,
    FileTaskRun,
    FileTaskRunStatistics,
    FileTaskRunStatus,
    FileTaskTriggerType,
)
from j_file_kit.app.file_task.domain.ports import FileTaskRunRepository
from j_file_kit.infrastructure.file_task.file_task_run_manager import (
    FileTaskRunManager,
)

pytestmark = pytest.mark.unit


class _FileTaskRunRepositoryStub(FileTaskRunRepository):
    def __init__(self) -> None:
        self._next_id = 1
        self.runs: dict[int, FileTaskRun] = {}
        self.statistics_by_run: dict[int, dict[str, float | int]] = {}
        self.update_calls: list[dict[str, object]] = []

    def create_run(
        self,
        run_name: str,
        task_type: str,
        trigger_type: FileTaskTriggerType,
        status: FileTaskRunStatus,
        start_time: datetime,
    ) -> int:
        run_id = self._next_id
        self._next_id += 1
        self.runs[run_id] = FileTaskRun(
            run_id=run_id,
            run_name=run_name,
            task_type=task_type,
            trigger_type=trigger_type,
            status=status,
            start_time=start_time,
            end_time=None,
            error_message=None,
        )
        return run_id

    def update_run(
        self,
        run_id: int,
        status: FileTaskRunStatus | None = None,
        end_time: datetime | None = None,
        error_message: str | None = None,
        statistics: dict[str, float | int] | None = None,
    ) -> None:
        self.update_calls.append(
            {
                "run_id": run_id,
                "status": status,
                "end_time": end_time,
                "error_message": error_message,
                "statistics": statistics,
            },
        )
        updates: dict[str, object] = {}
        if status is not None:
            updates["status"] = status
        if end_time is not None:
            updates["end_time"] = end_time
        if error_message is not None:
            updates["error_message"] = error_message
        if updates:
            self.runs[run_id] = self.runs[run_id].model_copy(update=updates)
        if statistics is not None:
            self.statistics_by_run[run_id] = statistics

    def get_run(self, run_id: int) -> FileTaskRun | None:
        return self.runs.get(run_id)

    def list_runs(self) -> list[FileTaskRun]:
        return list(self.runs.values())

    def get_running_run(self) -> FileTaskRun | None:
        for run in self.runs.values():
            if run.status == FileTaskRunStatus.RUNNING:
                return run
        return None

    def get_pending_or_running_runs(self) -> list[FileTaskRun]:
        return [
            run
            for run in self.runs.values()
            if run.status in (FileTaskRunStatus.PENDING, FileTaskRunStatus.RUNNING)
        ]


class _FileTaskRunnerSuccess:
    def __init__(self, stats: FileTaskRunStatistics) -> None:
        self._stats = stats

    @property
    def task_type(self) -> str:
        return TASK_TYPE_JAV_VIDEO_ORGANIZER

    def run(
        self,
        run_id: int,
        dry_run: bool = False,
        cancellation_event: threading.Event | None = None,
    ) -> FileTaskRunStatistics:
        return self._stats


class _FileTaskRunnerFailure:
    @property
    def task_type(self) -> str:
        return TASK_TYPE_JAV_VIDEO_ORGANIZER

    def run(
        self,
        run_id: int,
        dry_run: bool = False,
        cancellation_event: threading.Event | None = None,
    ) -> FileTaskRunStatistics:
        raise RuntimeError("boom")


def test_execute_run_sets_running_and_completed_with_stats() -> None:
    repo = _FileTaskRunRepositoryStub()
    manager = FileTaskRunManager(repo)
    run_id = repo.create_run(
        run_name="run",
        task_type=TASK_TYPE_JAV_VIDEO_ORGANIZER,
        trigger_type=FileTaskTriggerType.MANUAL,
        status=FileTaskRunStatus.PENDING,
        start_time=datetime.now(),
    )
    stats = FileTaskRunStatistics(
        total_items=3,
        success_items=2,
        error_items=1,
        skipped_items=0,
        warning_items=0,
        total_duration_ms=123.0,
    )

    manager._execute_run(
        run_id=run_id,
        task=_FileTaskRunnerSuccess(stats),
        dry_run=True,
        cancellation_event=threading.Event(),
    )

    assert repo.runs[run_id].status == FileTaskRunStatus.COMPLETED
    assert repo.statistics_by_run[run_id] == stats.model_dump()
    assert repo.update_calls[0]["status"] == FileTaskRunStatus.RUNNING
    assert repo.update_calls[-1]["status"] == FileTaskRunStatus.COMPLETED


def test_execute_run_sets_failed_on_exception() -> None:
    repo = _FileTaskRunRepositoryStub()
    manager = FileTaskRunManager(repo)
    run_id = repo.create_run(
        run_name="run",
        task_type=TASK_TYPE_JAV_VIDEO_ORGANIZER,
        trigger_type=FileTaskTriggerType.MANUAL,
        status=FileTaskRunStatus.PENDING,
        start_time=datetime.now(),
    )

    manager._execute_run(
        run_id=run_id,
        task=_FileTaskRunnerFailure(),
        dry_run=False,
        cancellation_event=threading.Event(),
    )

    assert repo.runs[run_id].status == FileTaskRunStatus.FAILED
    assert repo.update_calls[-1]["error_message"] == "boom"


def test_start_run_raises_when_running_exists() -> None:
    repo = _FileTaskRunRepositoryStub()
    manager = FileTaskRunManager(repo)
    repo.create_run(
        run_name="running",
        task_type=TASK_TYPE_JAV_VIDEO_ORGANIZER,
        trigger_type=FileTaskTriggerType.MANUAL,
        status=FileTaskRunStatus.RUNNING,
        start_time=datetime.now(),
    )

    with pytest.raises(FileTaskAlreadyRunningError):
        manager.start_run(
            _FileTaskRunnerSuccess(
                FileTaskRunStatistics(
                    total_items=0,
                    success_items=0,
                    error_items=0,
                    skipped_items=0,
                    warning_items=0,
                    total_duration_ms=0.0,
                ),
            ),
        )


def test_cancel_run_marks_pending_as_cancelled() -> None:
    repo = _FileTaskRunRepositoryStub()
    manager = FileTaskRunManager(repo)
    run_id = repo.create_run(
        run_name="pending",
        task_type=TASK_TYPE_JAV_VIDEO_ORGANIZER,
        trigger_type=FileTaskTriggerType.MANUAL,
        status=FileTaskRunStatus.PENDING,
        start_time=datetime.now(),
    )

    manager.cancel_run(run_id)

    assert repo.runs[run_id].status == FileTaskRunStatus.CANCELLED


def test_cancel_run_marks_running_as_cancelled_and_sets_event() -> None:
    repo = _FileTaskRunRepositoryStub()
    manager = FileTaskRunManager(repo)
    run_id = repo.create_run(
        run_name="running",
        task_type=TASK_TYPE_JAV_VIDEO_ORGANIZER,
        trigger_type=FileTaskTriggerType.MANUAL,
        status=FileTaskRunStatus.RUNNING,
        start_time=datetime.now(),
    )
    cancellation_event = threading.Event()
    manager._cancellation_event = cancellation_event

    manager.cancel_run(run_id)

    assert cancellation_event.is_set()
    assert repo.runs[run_id].status == FileTaskRunStatus.CANCELLED


def test_cancel_run_raises_when_missing() -> None:
    repo = _FileTaskRunRepositoryStub()
    manager = FileTaskRunManager(repo)

    with pytest.raises(FileTaskNotFoundError):
        manager.cancel_run(999)


def test_cancel_run_raises_when_already_done() -> None:
    repo = _FileTaskRunRepositoryStub()
    manager = FileTaskRunManager(repo)
    run_id = repo.create_run(
        run_name="done",
        task_type=TASK_TYPE_JAV_VIDEO_ORGANIZER,
        trigger_type=FileTaskTriggerType.MANUAL,
        status=FileTaskRunStatus.COMPLETED,
        start_time=datetime.now(),
    )

    with pytest.raises(FileTaskCancelledError):
        manager.cancel_run(run_id)
