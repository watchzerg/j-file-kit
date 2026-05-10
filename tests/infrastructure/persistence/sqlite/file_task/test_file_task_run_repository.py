"""文件任务执行实例仓储集成测试"""

from datetime import datetime
from pathlib import Path

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
from j_file_kit.infrastructure.persistence.sqlite.schema import SQLiteSchemaInitializer

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
        assert run.dry_run is False
        assert run.status == FileTaskRunStatus.PENDING
        assert run.statistics is None

    def test_create_and_get_dry_run(
        self,
        file_task_run_repository: FileTaskRunRepositoryImpl,
    ) -> None:
        run_id = file_task_run_repository.create_run(
            run_name="dry-run",
            task_type="raw_file_organizer",
            trigger_type=FileTaskTriggerType.MANUAL,
            status=FileTaskRunStatus.PENDING,
            start_time=datetime.now(),
            dry_run=True,
        )

        run = file_task_run_repository.get_run(run_id)

        assert run is not None
        assert run.dry_run is True

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
            statistics={"total_items": 3, "success_items": 2, "error_items": 1},
        )
        run = file_task_run_repository.get_run(run_id)
        assert run is not None
        assert run.status == FileTaskRunStatus.COMPLETED
        assert run.end_time is not None
        assert run.statistics is not None
        assert run.statistics.total_items == 3
        assert run.statistics.success_items == 2
        assert run.statistics.error_items == 1

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

    def test_list_runs_filters_and_paginates(
        self,
        file_task_run_repository: FileTaskRunRepositoryImpl,
    ) -> None:
        file_task_run_repository.create_run(
            run_name="jav-completed",
            task_type="jav_video_organizer",
            trigger_type=FileTaskTriggerType.MANUAL,
            status=FileTaskRunStatus.COMPLETED,
            start_time=datetime(2024, 1, 1),
        )
        file_task_run_repository.create_run(
            run_name="raw-failed",
            task_type="raw_file_organizer",
            trigger_type=FileTaskTriggerType.MANUAL,
            status=FileTaskRunStatus.FAILED,
            start_time=datetime(2024, 1, 2),
        )
        file_task_run_repository.create_run(
            run_name="raw-completed",
            task_type="raw_file_organizer",
            trigger_type=FileTaskTriggerType.MANUAL,
            status=FileTaskRunStatus.COMPLETED,
            start_time=datetime(2024, 1, 3),
        )

        runs = file_task_run_repository.list_runs(
            task_type="raw_file_organizer",
            status=FileTaskRunStatus.COMPLETED,
            limit=1,
            offset=0,
        )

        assert [run.run_name for run in runs] == ["raw-completed"]
        assert (
            file_task_run_repository.count_runs(
                task_type="raw_file_organizer",
                status=FileTaskRunStatus.COMPLETED,
            )
            == 1
        )

    def test_list_runs_limit_offset_keeps_sort_order(
        self,
        file_task_run_repository: FileTaskRunRepositoryImpl,
    ) -> None:
        for index in range(3):
            file_task_run_repository.create_run(
                run_name=f"run-{index}",
                task_type="raw_file_organizer",
                trigger_type=FileTaskTriggerType.MANUAL,
                status=FileTaskRunStatus.COMPLETED,
                start_time=datetime(2024, 1, index + 1),
            )

        runs = file_task_run_repository.list_runs(limit=1, offset=1)

        assert [run.run_name for run in runs] == ["run-1"]
        assert file_task_run_repository.count_runs() == 3

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

    def test_get_active_run(
        self,
        file_task_run_repository: FileTaskRunRepositoryImpl,
    ) -> None:
        assert file_task_run_repository.get_active_run() is None
        file_task_run_repository.create_run(
            run_name="completed",
            task_type="x",
            trigger_type=FileTaskTriggerType.MANUAL,
            status=FileTaskRunStatus.COMPLETED,
            start_time=datetime(2024, 1, 1),
        )
        pending_id = file_task_run_repository.create_run(
            run_name="pending",
            task_type="x",
            trigger_type=FileTaskTriggerType.MANUAL,
            status=FileTaskRunStatus.PENDING,
            start_time=datetime(2024, 1, 2),
        )
        running_id = file_task_run_repository.create_run(
            run_name="running",
            task_type="x",
            trigger_type=FileTaskTriggerType.MANUAL,
            status=FileTaskRunStatus.RUNNING,
            start_time=datetime(2024, 1, 3),
        )

        active = file_task_run_repository.get_active_run()

        assert active is not None
        assert active.run_id == running_id
        assert active.run_name == "running"
        assert active.run_id != pending_id

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

    def test_schema_initializer_adds_dry_run_to_existing_table(
        self,
        tmp_path: Path,
    ) -> None:
        manager = SQLiteConnectionManager(tmp_path / "legacy.sqlite")
        conn = manager.get_connection()
        conn.execute(
            """
            CREATE TABLE file_task_runs (
                run_id INTEGER PRIMARY KEY,
                run_name TEXT NOT NULL,
                task_type TEXT NOT NULL,
                trigger_type TEXT NOT NULL,
                status TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                error_message TEXT,
                statistics TEXT
            )
            """,
        )
        conn.commit()

        SQLiteSchemaInitializer(manager).initialize()

        columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(file_task_runs)")
        }
        assert "dry_run" in columns
        manager.close()
