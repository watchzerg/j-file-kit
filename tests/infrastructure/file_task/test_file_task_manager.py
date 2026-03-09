import threading
from datetime import datetime

import pytest

from j_file_kit.app.file_task.domain.constants import TASK_TYPE_JAV_VIDEO_ORGANIZER
from j_file_kit.app.file_task.domain.models import (
    FileTaskAlreadyRunningError,
    FileTaskCancelledError,
    FileTaskNotFoundError,
    FileTaskRecord,
    FileTaskStatistics,
    FileTaskStatus,
    FileTaskTriggerType,
)
from j_file_kit.app.file_task.domain.ports import FileTaskRepository
from j_file_kit.infrastructure.file_task.file_task_manager import FileTaskManager

pytestmark = pytest.mark.unit


class _FileTaskRepositoryStub(FileTaskRepository):
    def __init__(self) -> None:
        self._next_id = 1
        self.tasks: dict[int, FileTaskRecord] = {}
        self.statistics_by_task: dict[int, dict[str, float | int]] = {}
        self.update_calls: list[dict[str, object]] = []

    def create_task(
        self,
        task_name: str,
        task_type: str,
        trigger_type: FileTaskTriggerType,
        status: FileTaskStatus,
        start_time: datetime,
    ) -> int:
        task_id = self._next_id
        self._next_id += 1
        self.tasks[task_id] = FileTaskRecord(
            task_id=task_id,
            task_name=task_name,
            task_type=task_type,
            trigger_type=trigger_type,
            status=status,
            start_time=start_time,
            end_time=None,
            error_message=None,
        )
        return task_id

    def update_task(
        self,
        task_id: int,
        status: FileTaskStatus | None = None,
        end_time: datetime | None = None,
        error_message: str | None = None,
        statistics: dict[str, float | int] | None = None,
    ) -> None:
        self.update_calls.append(
            {
                "task_id": task_id,
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
            self.tasks[task_id] = self.tasks[task_id].model_copy(update=updates)
        if statistics is not None:
            self.statistics_by_task[task_id] = statistics

    def get_task(self, task_id: int) -> FileTaskRecord | None:
        return self.tasks.get(task_id)

    def list_tasks(self) -> list[FileTaskRecord]:
        return list(self.tasks.values())

    def get_running_task(self) -> FileTaskRecord | None:
        for task in self.tasks.values():
            if task.status == FileTaskStatus.RUNNING:
                return task
        return None

    def get_pending_or_running_tasks(self) -> list[FileTaskRecord]:
        return [
            task
            for task in self.tasks.values()
            if task.status in (FileTaskStatus.PENDING, FileTaskStatus.RUNNING)
        ]


class _FileTaskRunnerSuccess:
    def __init__(self, stats: FileTaskStatistics) -> None:
        self._stats = stats

    @property
    def task_type(self) -> str:
        return TASK_TYPE_JAV_VIDEO_ORGANIZER

    def run(
        self,
        task_id: int,
        dry_run: bool = False,
        cancellation_event: threading.Event | None = None,
    ) -> FileTaskStatistics:
        return self._stats


class _FileTaskRunnerFailure:
    @property
    def task_type(self) -> str:
        return TASK_TYPE_JAV_VIDEO_ORGANIZER

    def run(
        self,
        task_id: int,
        dry_run: bool = False,
        cancellation_event: threading.Event | None = None,
    ) -> FileTaskStatistics:
        raise RuntimeError("boom")


def test_execute_task_sets_running_and_completed_with_stats() -> None:
    repo = _FileTaskRepositoryStub()
    manager = FileTaskManager(repo)
    task_id = repo.create_task(
        task_name="task",
        task_type=TASK_TYPE_JAV_VIDEO_ORGANIZER,
        trigger_type=FileTaskTriggerType.MANUAL,
        status=FileTaskStatus.PENDING,
        start_time=datetime.now(),
    )
    stats = FileTaskStatistics(
        total_items=3,
        success_items=2,
        error_items=1,
        skipped_items=0,
        warning_items=0,
        total_duration_ms=123.0,
    )

    manager._execute_task(
        task_id=task_id,
        task=_FileTaskRunnerSuccess(stats),
        dry_run=True,
        cancellation_event=threading.Event(),
    )

    assert repo.tasks[task_id].status == FileTaskStatus.COMPLETED
    assert repo.statistics_by_task[task_id] == stats.model_dump()
    assert repo.update_calls[0]["status"] == FileTaskStatus.RUNNING
    assert repo.update_calls[-1]["status"] == FileTaskStatus.COMPLETED


def test_execute_task_sets_failed_on_exception() -> None:
    repo = _FileTaskRepositoryStub()
    manager = FileTaskManager(repo)
    task_id = repo.create_task(
        task_name="task",
        task_type=TASK_TYPE_JAV_VIDEO_ORGANIZER,
        trigger_type=FileTaskTriggerType.MANUAL,
        status=FileTaskStatus.PENDING,
        start_time=datetime.now(),
    )

    manager._execute_task(
        task_id=task_id,
        task=_FileTaskRunnerFailure(),
        dry_run=False,
        cancellation_event=threading.Event(),
    )

    assert repo.tasks[task_id].status == FileTaskStatus.FAILED
    assert repo.update_calls[-1]["error_message"] == "boom"


def test_start_task_raises_when_running_task_exists() -> None:
    repo = _FileTaskRepositoryStub()
    manager = FileTaskManager(repo)
    repo.create_task(
        task_name="running",
        task_type=TASK_TYPE_JAV_VIDEO_ORGANIZER,
        trigger_type=FileTaskTriggerType.MANUAL,
        status=FileTaskStatus.RUNNING,
        start_time=datetime.now(),
    )

    with pytest.raises(FileTaskAlreadyRunningError):
        manager.start_task(
            _FileTaskRunnerSuccess(
                FileTaskStatistics(
                    total_items=0,
                    success_items=0,
                    error_items=0,
                    skipped_items=0,
                    warning_items=0,
                    total_duration_ms=0.0,
                ),
            ),
        )


def test_cancel_task_marks_pending_as_cancelled() -> None:
    repo = _FileTaskRepositoryStub()
    manager = FileTaskManager(repo)
    task_id = repo.create_task(
        task_name="pending",
        task_type=TASK_TYPE_JAV_VIDEO_ORGANIZER,
        trigger_type=FileTaskTriggerType.MANUAL,
        status=FileTaskStatus.PENDING,
        start_time=datetime.now(),
    )

    manager.cancel_task(task_id)

    assert repo.tasks[task_id].status == FileTaskStatus.CANCELLED


def test_cancel_task_marks_running_as_cancelled_and_sets_event() -> None:
    repo = _FileTaskRepositoryStub()
    manager = FileTaskManager(repo)
    task_id = repo.create_task(
        task_name="running",
        task_type=TASK_TYPE_JAV_VIDEO_ORGANIZER,
        trigger_type=FileTaskTriggerType.MANUAL,
        status=FileTaskStatus.RUNNING,
        start_time=datetime.now(),
    )
    cancellation_event = threading.Event()
    manager._cancellation_event = cancellation_event

    manager.cancel_task(task_id)

    assert cancellation_event.is_set()
    assert repo.tasks[task_id].status == FileTaskStatus.CANCELLED


def test_cancel_task_raises_when_missing() -> None:
    repo = _FileTaskRepositoryStub()
    manager = FileTaskManager(repo)

    with pytest.raises(FileTaskNotFoundError):
        manager.cancel_task(999)


def test_cancel_task_raises_when_already_done() -> None:
    repo = _FileTaskRepositoryStub()
    manager = FileTaskManager(repo)
    task_id = repo.create_task(
        task_name="done",
        task_type=TASK_TYPE_JAV_VIDEO_ORGANIZER,
        trigger_type=FileTaskTriggerType.MANUAL,
        status=FileTaskStatus.COMPLETED,
        start_time=datetime.now(),
    )

    with pytest.raises(FileTaskCancelledError):
        manager.cancel_task(task_id)
