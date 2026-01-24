import threading
from datetime import datetime

import pytest

from j_file_kit.app.task.domain.models import (
    TaskAlreadyRunningError,
    TaskCancelledError,
    TaskNotFoundError,
    TaskRecord,
    TaskStatistics,
    TaskStatus,
    TaskType,
    TriggerType,
)
from j_file_kit.app.task.domain.ports import TaskRepository
from j_file_kit.infrastructure.task.task_manager import TaskManager

pytestmark = pytest.mark.unit


class _TaskRepositoryStub(TaskRepository):
    def __init__(self) -> None:
        self._next_id = 1
        self.tasks: dict[int, TaskRecord] = {}
        self.statistics_by_task: dict[int, dict[str, float | int]] = {}
        self.update_calls: list[dict[str, object]] = []

    def create_task(
        self,
        task_name: str,
        task_type: TaskType,
        trigger_type: TriggerType,
        status: TaskStatus,
        start_time: datetime,
    ) -> int:
        task_id = self._next_id
        self._next_id += 1
        self.tasks[task_id] = TaskRecord(
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
        status: TaskStatus | None = None,
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

    def get_task(self, task_id: int) -> TaskRecord | None:
        return self.tasks.get(task_id)

    def list_tasks(self) -> list[TaskRecord]:
        return list(self.tasks.values())

    def get_running_task(self) -> TaskRecord | None:
        for task in self.tasks.values():
            if task.status == TaskStatus.RUNNING:
                return task
        return None

    def get_pending_or_running_tasks(self) -> list[TaskRecord]:
        return [
            task
            for task in self.tasks.values()
            if task.status in (TaskStatus.PENDING, TaskStatus.RUNNING)
        ]


class _TaskRunnerSuccess:
    def __init__(self, stats: TaskStatistics) -> None:
        self._stats = stats

    @property
    def task_type(self) -> TaskType:
        return TaskType.JAV_VIDEO_ORGANIZER

    def run(
        self,
        task_id: int,
        dry_run: bool = False,
        cancellation_event: threading.Event | None = None,
    ) -> TaskStatistics:
        return self._stats


class _TaskRunnerFailure:
    @property
    def task_type(self) -> TaskType:
        return TaskType.JAV_VIDEO_ORGANIZER

    def run(
        self,
        task_id: int,
        dry_run: bool = False,
        cancellation_event: threading.Event | None = None,
    ) -> TaskStatistics:
        raise RuntimeError("boom")


def test_execute_task_sets_running_and_completed_with_stats() -> None:
    repo = _TaskRepositoryStub()
    manager = TaskManager(repo)
    task_id = repo.create_task(
        task_name="task",
        task_type=TaskType.JAV_VIDEO_ORGANIZER,
        trigger_type=TriggerType.MANUAL,
        status=TaskStatus.PENDING,
        start_time=datetime.now(),
    )
    stats = TaskStatistics(
        total_items=3,
        success_items=2,
        error_items=1,
        skipped_items=0,
        warning_items=0,
        total_duration_ms=123.0,
    )

    manager._execute_task(
        task_id=task_id,
        task=_TaskRunnerSuccess(stats),
        dry_run=True,
        cancellation_event=threading.Event(),
    )

    assert repo.tasks[task_id].status == TaskStatus.COMPLETED
    assert repo.statistics_by_task[task_id] == stats.model_dump()
    assert repo.update_calls[0]["status"] == TaskStatus.RUNNING
    assert repo.update_calls[-1]["status"] == TaskStatus.COMPLETED


def test_execute_task_sets_failed_on_exception() -> None:
    repo = _TaskRepositoryStub()
    manager = TaskManager(repo)
    task_id = repo.create_task(
        task_name="task",
        task_type=TaskType.JAV_VIDEO_ORGANIZER,
        trigger_type=TriggerType.MANUAL,
        status=TaskStatus.PENDING,
        start_time=datetime.now(),
    )

    manager._execute_task(
        task_id=task_id,
        task=_TaskRunnerFailure(),
        dry_run=False,
        cancellation_event=threading.Event(),
    )

    assert repo.tasks[task_id].status == TaskStatus.FAILED
    assert repo.update_calls[-1]["error_message"] == "boom"


def test_start_task_raises_when_running_task_exists() -> None:
    repo = _TaskRepositoryStub()
    manager = TaskManager(repo)
    repo.create_task(
        task_name="running",
        task_type=TaskType.JAV_VIDEO_ORGANIZER,
        trigger_type=TriggerType.MANUAL,
        status=TaskStatus.RUNNING,
        start_time=datetime.now(),
    )

    with pytest.raises(TaskAlreadyRunningError):
        manager.start_task(
            _TaskRunnerSuccess(
                TaskStatistics(
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
    repo = _TaskRepositoryStub()
    manager = TaskManager(repo)
    task_id = repo.create_task(
        task_name="pending",
        task_type=TaskType.JAV_VIDEO_ORGANIZER,
        trigger_type=TriggerType.MANUAL,
        status=TaskStatus.PENDING,
        start_time=datetime.now(),
    )

    manager.cancel_task(task_id)

    assert repo.tasks[task_id].status == TaskStatus.CANCELLED


def test_cancel_task_marks_running_as_cancelled_and_sets_event() -> None:
    repo = _TaskRepositoryStub()
    manager = TaskManager(repo)
    task_id = repo.create_task(
        task_name="running",
        task_type=TaskType.JAV_VIDEO_ORGANIZER,
        trigger_type=TriggerType.MANUAL,
        status=TaskStatus.RUNNING,
        start_time=datetime.now(),
    )
    cancellation_event = threading.Event()
    manager._cancellation_event = cancellation_event

    manager.cancel_task(task_id)

    assert cancellation_event.is_set()
    assert repo.tasks[task_id].status == TaskStatus.CANCELLED


def test_cancel_task_raises_when_missing() -> None:
    repo = _TaskRepositoryStub()
    manager = TaskManager(repo)

    with pytest.raises(TaskNotFoundError):
        manager.cancel_task(999)


def test_cancel_task_raises_when_already_done() -> None:
    repo = _TaskRepositoryStub()
    manager = TaskManager(repo)
    task_id = repo.create_task(
        task_name="done",
        task_type=TaskType.JAV_VIDEO_ORGANIZER,
        trigger_type=TriggerType.MANUAL,
        status=TaskStatus.COMPLETED,
        start_time=datetime.now(),
    )

    with pytest.raises(TaskCancelledError):
        manager.cancel_task(task_id)
