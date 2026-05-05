"""文件任务执行管理器集成测试

覆盖 generate_run_name、FileTaskRunManager 与 mock repository 交互。
"""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from j_file_kit.app.file_task.domain.task_errors import (
    FileTaskAlreadyRunningError,
    FileTaskCancelledError,
    FileTaskNotFoundError,
)
from j_file_kit.app.file_task.domain.task_run import (
    FileTaskRun,
    FileTaskRunStatus,
    FileTaskTriggerType,
)
from j_file_kit.infrastructure.file_task.file_task_run_manager import (
    FileTaskRunManager,
    generate_run_name,
)

pytestmark = pytest.mark.integration


class TestGenerateRunName:
    """generate_run_name 格式"""

    def test_format(self) -> None:
        dt = datetime(2024, 12, 15, 14, 30, 52, 123000)
        result = generate_run_name(
            "jav_video_organizer",
            FileTaskTriggerType.MANUAL,
            dt,
        )
        assert result == "jav_video_organizer-manual-20241215143052123"

    def test_auto_trigger(self) -> None:
        dt = datetime(2025, 1, 1, 0, 0, 0, 0)
        result = generate_run_name("task", FileTaskTriggerType.AUTO, dt)
        assert "auto" in result


class TestFileTaskRunManager:
    """FileTaskRunManager 与 repository 交互"""

    @pytest.fixture
    def mock_repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def mock_task(self) -> MagicMock:
        task = MagicMock()
        task.task_type = "jav_video_organizer"
        task.run.return_value = MagicMock(
            total_items=0,
            success_items=0,
            error_items=0,
            skipped_items=0,
            warning_items=0,
            total_duration_ms=0.0,
        )
        return task

    def test_start_run_creates_and_returns_run_id(
        self,
        mock_repo: MagicMock,
        mock_task: MagicMock,
    ) -> None:
        mock_repo.get_running_run.return_value = None
        mock_repo.get_pending_or_running_runs.return_value = []
        mock_repo.create_run.return_value = 42
        manager = FileTaskRunManager(mock_repo)
        run_id = manager.start_run(mock_task)
        assert run_id == 42
        mock_repo.create_run.assert_called_once()

    def test_start_run_when_running_raises(
        self,
        mock_repo: MagicMock,
        mock_task: MagicMock,
    ) -> None:
        mock_repo.get_running_run.return_value = FileTaskRun(
            run_id=1,
            run_name="x",
            task_type="x",
            trigger_type=FileTaskTriggerType.MANUAL,
            status=FileTaskRunStatus.RUNNING,
            start_time=datetime.now(),
            end_time=None,
            error_message=None,
        )
        mock_repo.get_pending_or_running_runs.return_value = []
        manager = FileTaskRunManager(mock_repo)
        with pytest.raises(FileTaskAlreadyRunningError):
            manager.start_run(mock_task)

    def test_get_run_not_found_raises(self, mock_repo: MagicMock) -> None:
        mock_repo.get_pending_or_running_runs.return_value = []
        mock_repo.get_run.return_value = None
        manager = FileTaskRunManager(mock_repo)
        with pytest.raises(FileTaskNotFoundError):
            manager.get_run(999)

    def test_cancel_run_not_found_raises(self, mock_repo: MagicMock) -> None:
        mock_repo.get_pending_or_running_runs.return_value = []
        mock_repo.get_run.return_value = None
        manager = FileTaskRunManager(mock_repo)
        with pytest.raises(FileTaskNotFoundError):
            manager.cancel_run(999)

    def test_cancel_run_completed_raises(self, mock_repo: MagicMock) -> None:
        mock_repo.get_pending_or_running_runs.return_value = []
        mock_repo.get_run.return_value = FileTaskRun(
            run_id=1,
            run_name="x",
            task_type="x",
            trigger_type=FileTaskTriggerType.MANUAL,
            status=FileTaskRunStatus.COMPLETED,
            start_time=datetime.now(),
            end_time=datetime.now(),
            error_message=None,
        )
        manager = FileTaskRunManager(mock_repo)
        with pytest.raises(FileTaskCancelledError):
            manager.cancel_run(1)
