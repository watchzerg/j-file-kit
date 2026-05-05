"""文件任务执行实例仓储集成测试"""

from datetime import datetime

import pytest

from j_file_kit.app.file_task.domain.task_run import (
    FileTaskRunStatus,
    FileTaskTriggerType,
)
from j_file_kit.infrastructure.persistence.sqlite.connection import (
    SQLiteConnectionManager,
)
from j_file_kit.infrastructure.persistence.sqlite.file_task.file_task_run_repository import (
    FileTaskRunRepositoryImpl,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def file_task_run_repository(
    sqlite_connection_manager: SQLiteConnectionManager,
) -> FileTaskRunRepositoryImpl:
    return FileTaskRunRepositoryImpl(sqlite_connection_manager)


class TestFileTaskRunRepository:
    """FileTaskRunRepositoryImpl CRUD"""

    def test_create_and_get_run(
        self,
        file_task_run_repository: FileTaskRunRepositoryImpl,
    ) -> None:
        start_time = datetime.now()
        run_id = file_task_run_repository.create_run(
            run_name="test-run",
            task_type="jav_video_organizer",
            trigger_type=FileTaskTriggerType.MANUAL,
            status=FileTaskRunStatus.PENDING,
            start_time=start_time,
        )
        assert run_id > 0
        run = file_task_run_repository.get_run(run_id)
        assert run is not None
        assert run.run_id == run_id
        assert run.run_name == "test-run"
        assert run.task_type == "jav_video_organizer"
        assert run.trigger_type == FileTaskTriggerType.MANUAL
        assert run.status == FileTaskRunStatus.PENDING

    def test_get_run_nonexistent(
        self,
        file_task_run_repository: FileTaskRunRepositoryImpl,
    ) -> None:
        assert file_task_run_repository.get_run(999) is None

    def test_update_run(
        self,
        file_task_run_repository: FileTaskRunRepositoryImpl,
    ) -> None:
        run_id = file_task_run_repository.create_run(
            run_name="x",
            task_type="x",
            trigger_type=FileTaskTriggerType.MANUAL,
            status=FileTaskRunStatus.PENDING,
            start_time=datetime.now(),
        )
        end_time = datetime.now()
        file_task_run_repository.update_run(
            run_id,
            status=FileTaskRunStatus.COMPLETED,
            end_time=end_time,
        )
        run = file_task_run_repository.get_run(run_id)
        assert run is not None
        assert run.status == FileTaskRunStatus.COMPLETED
        assert run.end_time is not None

    def test_list_runs_ordered_by_start_time(
        self,
        file_task_run_repository: FileTaskRunRepositoryImpl,
    ) -> None:
        file_task_run_repository.create_run(
            run_name="first",
            task_type="x",
            trigger_type=FileTaskTriggerType.MANUAL,
            status=FileTaskRunStatus.COMPLETED,
            start_time=datetime(2024, 1, 1),
        )
        file_task_run_repository.create_run(
            run_name="second",
            task_type="x",
            trigger_type=FileTaskTriggerType.MANUAL,
            status=FileTaskRunStatus.COMPLETED,
            start_time=datetime(2024, 1, 2),
        )
        runs = file_task_run_repository.list_runs()
        assert len(runs) == 2
        assert runs[0].run_name == "second"

    def test_get_running_run(
        self,
        file_task_run_repository: FileTaskRunRepositoryImpl,
    ) -> None:
        assert file_task_run_repository.get_running_run() is None
        run_id = file_task_run_repository.create_run(
            run_name="x",
            task_type="x",
            trigger_type=FileTaskTriggerType.MANUAL,
            status=FileTaskRunStatus.RUNNING,
            start_time=datetime.now(),
        )
        run = file_task_run_repository.get_running_run()
        assert run is not None
        assert run.run_id == run_id

    def test_get_pending_or_running_runs(
        self,
        file_task_run_repository: FileTaskRunRepositoryImpl,
    ) -> None:
        file_task_run_repository.create_run(
            run_name="pending",
            task_type="x",
            trigger_type=FileTaskTriggerType.MANUAL,
            status=FileTaskRunStatus.PENDING,
            start_time=datetime.now(),
        )
        file_task_run_repository.create_run(
            run_name="running",
            task_type="x",
            trigger_type=FileTaskTriggerType.MANUAL,
            status=FileTaskRunStatus.RUNNING,
            start_time=datetime.now(),
        )
        file_task_run_repository.create_run(
            run_name="completed",
            task_type="x",
            trigger_type=FileTaskTriggerType.MANUAL,
            status=FileTaskRunStatus.COMPLETED,
            start_time=datetime.now(),
        )
        incomplete = file_task_run_repository.get_pending_or_running_runs()
        assert len(incomplete) == 2
        names = {r.run_name for r in incomplete}
        assert "pending" in names
        assert "running" in names
        assert "completed" not in names
