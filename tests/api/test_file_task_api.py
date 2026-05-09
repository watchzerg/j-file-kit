"""任务 API 集成测试

覆盖 POST start、GET status、POST cancel、GET list 端点。
"""

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import pytest

from j_file_kit.app.file_task.domain.constants import (
    TASK_TYPE_JAV_VIDEO_ORGANIZER,
    TASK_TYPE_RAW_FILE_ORGANIZER,
)
from j_file_kit.app.file_task.domain.task_run import (
    FileTaskRunStatus,
    FileTaskTriggerType,
)

pytestmark = pytest.mark.integration


class TestStartTask:
    """POST /api/tasks/{task_type}/start"""

    @pytest.mark.parametrize(
        "task_type",
        [TASK_TYPE_JAV_VIDEO_ORGANIZER, TASK_TYPE_RAW_FILE_ORGANIZER],
        ids=["jav", "raw"],
    )
    def test_start_task_success(self, client, task_type: str) -> None:
        """启动任务返回 run_id、run_name、status（JAV / Raw）。"""
        response = client.post(
            f"/api/tasks/{task_type}/start",
            json={"dry_run": False},
        )
        assert response.status_code == 200
        data = response.json()
        assert "run_id" in data
        assert data["run_id"] > 0
        assert "run_name" in data
        assert "status" in data
        assert data["dry_run"] is False

    def test_start_task_invalid_task_type(self, client) -> None:
        """未知任务类型返回 404"""
        response = client.post(
            "/api/tasks/unknown_task/start",
            json={"dry_run": False},
        )
        assert response.status_code == 404
        assert "任务不存在" in response.json()["detail"]

    @pytest.mark.parametrize(
        "task_type",
        [TASK_TYPE_JAV_VIDEO_ORGANIZER, TASK_TYPE_RAW_FILE_ORGANIZER],
        ids=["jav", "raw"],
    )
    def test_start_task_invalid_trigger_type(self, client, task_type: str) -> None:
        """无效触发类型返回 400（JAV / Raw）。"""
        response = client.post(
            f"/api/tasks/{task_type}/start",
            json={"dry_run": False, "trigger_type": "invalid"},
        )
        assert response.status_code == 400
        assert "无效的触发类型" in response.json()["detail"]


class TestGetRunStatus:
    """GET /api/tasks/{run_id}"""

    @pytest.mark.parametrize(
        "task_type",
        [TASK_TYPE_JAV_VIDEO_ORGANIZER, TASK_TYPE_RAW_FILE_ORGANIZER],
        ids=["jav", "raw"],
    )
    def test_get_run_status_success(self, client, task_type: str) -> None:
        """查询执行实例状态（JAV / Raw）。"""
        start_resp = client.post(
            f"/api/tasks/{task_type}/start",
            json={"dry_run": False},
        )
        assert start_resp.status_code == 200
        run_id = start_resp.json()["run_id"]

        response = client.get(f"/api/tasks/{run_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == run_id
        assert "run_name" in data
        assert "status" in data
        assert "start_time" in data
        assert data["task_type"] == task_type
        assert data["trigger_type"] == "manual"
        assert data["dry_run"] is False
        assert "duration_ms" in data
        assert data["statistics"]["total_items"] >= 0

    def test_get_run_status_returns_detail_statistics(self, client) -> None:
        """详情接口返回 dry_run、耗时和完整统计快照。"""
        app_state = client.app.state.app_state
        start_time = datetime(2024, 1, 1, 12, 0, 0)
        end_time = datetime(2024, 1, 1, 12, 0, 1)
        run_id = app_state.file_task_run_repository.create_run(
            run_name="raw-detail",
            task_type=TASK_TYPE_RAW_FILE_ORGANIZER,
            trigger_type=FileTaskTriggerType.MANUAL,
            status=FileTaskRunStatus.PENDING,
            start_time=start_time,
            dry_run=True,
        )
        app_state.file_task_run_repository.update_run(
            run_id,
            status=FileTaskRunStatus.COMPLETED,
            end_time=end_time,
            statistics={
                "total_items": 3,
                "success_items": 2,
                "error_items": 1,
                "phase1_seen_files": 7,
                "phase3_deferred_files_misc": 4,
            },
        )

        response = client.get(f"/api/tasks/{run_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == run_id
        assert data["task_type"] == TASK_TYPE_RAW_FILE_ORGANIZER
        assert data["trigger_type"] == "manual"
        assert data["dry_run"] is True
        assert data["duration_ms"] == 1000
        assert data["statistics"]["total_items"] == 3
        assert data["statistics"]["success_items"] == 2
        assert data["statistics"]["error_items"] == 1
        assert data["statistics"]["phase1_seen_files"] == 7
        assert data["statistics"]["phase3_deferred_files_misc"] == 4

    def test_get_run_status_not_found(self, client) -> None:
        """不存在的 run_id 返回 404"""
        response = client.get("/api/tasks/99999")
        assert response.status_code == 404
        assert response.json()["code"] == "TASK_NOT_FOUND"

    def test_get_run_status_invalid_run_id(self, client) -> None:
        """无效 run_id 格式返回 400"""
        response = client.get("/api/tasks/abc")
        assert response.status_code == 400
        assert "无效的执行实例ID格式" in response.json()["detail"]


class TestCancelRun:
    """POST /api/tasks/{run_id}/cancel"""

    @pytest.mark.parametrize(
        (
            "task_type",
            "media_root_module_attr",
            "config_url",
            "workspace_dir",
            "inbox_parent_dir",
        ),
        [
            (
                TASK_TYPE_JAV_VIDEO_ORGANIZER,
                "JAV_MEDIA_ROOT",
                "/api/file-task/config/jav-video-organizer",
                lambda p: p,
                lambda p: p,
            ),
            (
                TASK_TYPE_RAW_FILE_ORGANIZER,
                "RAW_MEDIA_ROOT",
                "/api/file-task/config/raw-file-organizer",
                lambda p: p / "raw_ws",
                lambda p: p / "raw_ws",
            ),
        ],
        ids=["jav", "raw"],
    )
    def test_cancel_run_success(
        self,
        monkeypatch: pytest.MonkeyPatch,
        client,
        tmp_path: Path,
        task_type: str,
        media_root_module_attr: str,
        config_url: str,
        workspace_dir: Callable[[Path], Path],
        inbox_parent_dir: Callable[[Path], Path],
    ) -> None:
        """取消执行实例（JAV / Raw）：扩大 inbox 工作量以便有机会在运行中 cancel。"""
        monkeypatch.setattr(
            f"j_file_kit.app.file_task.application.config_common.{media_root_module_attr}",
            tmp_path,
        )
        ws = workspace_dir(tmp_path)
        ws.mkdir(parents=True, exist_ok=True)
        inbox = inbox_parent_dir(tmp_path) / "inbox"
        inbox.mkdir(parents=True, exist_ok=True)
        for i in range(100):
            (inbox / f"file_{i}.mp4").touch()

        config_resp = client.patch(
            config_url,
            json={
                "config": {
                    "workspace_root": str(ws),
                },
            },
        )
        assert config_resp.status_code == 200

        start_resp = client.post(
            f"/api/tasks/{task_type}/start",
            json={"dry_run": False},
        )
        assert start_resp.status_code == 200
        run_id = start_resp.json()["run_id"]

        response = client.post(f"/api/tasks/{run_id}/cancel")
        assert response.status_code == 200
        assert "任务已取消" in response.json()["message"]

    def test_cancel_run_not_found(self, client) -> None:
        """不存在的 run_id 返回 404"""
        response = client.post("/api/tasks/99999/cancel")
        assert response.status_code == 404
        assert response.json()["code"] == "TASK_NOT_FOUND"

    def test_cancel_run_invalid_run_id(self, client) -> None:
        """无效 run_id 格式返回 400"""
        response = client.post("/api/tasks/xyz/cancel")
        assert response.status_code == 400
        assert "无效的执行实例ID格式" in response.json()["detail"]

    @pytest.mark.parametrize(
        "task_type",
        [TASK_TYPE_JAV_VIDEO_ORGANIZER, TASK_TYPE_RAW_FILE_ORGANIZER],
        ids=["jav", "raw"],
    )
    def test_cancel_run_already_completed(self, client, task_type: str) -> None:
        """对已完成的 run 再次取消返回 400（JAV / Raw）。"""
        start_resp = client.post(
            f"/api/tasks/{task_type}/start",
            json={"dry_run": False},
        )
        assert start_resp.status_code == 200
        run_id = start_resp.json()["run_id"]

        client.post(f"/api/tasks/{run_id}/cancel")
        response = client.post(f"/api/tasks/{run_id}/cancel")
        assert response.status_code == 400
        assert response.json()["code"] == "TASK_CANCELLED"


class TestListRuns:
    """GET /api/tasks"""

    def test_list_runs_empty(self, client) -> None:
        """无执行记录时返回空列表"""
        response = client.get("/api/tasks")
        assert response.status_code == 200
        assert response.json()["runs"] == []

    @pytest.mark.parametrize(
        "task_type",
        [TASK_TYPE_JAV_VIDEO_ORGANIZER, TASK_TYPE_RAW_FILE_ORGANIZER],
        ids=["jav", "raw"],
    )
    def test_list_runs_with_items(self, client, task_type: str) -> None:
        """有执行记录时返回列表（JAV / Raw）。"""
        client.post(
            f"/api/tasks/{task_type}/start",
            json={"dry_run": False},
        )
        response = client.get("/api/tasks")
        assert response.status_code == 200
        runs = response.json()["runs"]
        assert len(runs) >= 1
        assert "run_id" in runs[0]
        assert "run_name" in runs[0]
        assert "status" in runs[0]


class TestGetActiveRun:
    """GET /api/tasks/active"""

    def test_get_active_run_empty(self, client) -> None:
        """无活跃 run 时返回 null。"""
        response = client.get("/api/tasks/active")
        assert response.status_code == 200
        assert response.json() is None

    def test_get_active_run_returns_pending_or_running(self, client) -> None:
        """pending/running run 会作为活跃 run 返回。"""
        app_state = client.app.state.app_state
        app_state.file_task_run_repository.create_run(
            run_name="completed",
            task_type=TASK_TYPE_JAV_VIDEO_ORGANIZER,
            trigger_type=FileTaskTriggerType.MANUAL,
            status=FileTaskRunStatus.COMPLETED,
            start_time=datetime(2024, 1, 1),
        )
        run_id = app_state.file_task_run_repository.create_run(
            run_name="pending",
            task_type=TASK_TYPE_RAW_FILE_ORGANIZER,
            trigger_type=FileTaskTriggerType.MANUAL,
            status=FileTaskRunStatus.PENDING,
            start_time=datetime(2024, 1, 2),
        )

        response = client.get("/api/tasks/active")

        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == run_id
        assert data["run_name"] == "pending"
        assert data["task_type"] == TASK_TYPE_RAW_FILE_ORGANIZER
        assert data["trigger_type"] == "manual"
        assert data["status"] == "pending"

    def test_get_active_run_ignores_terminal_runs(self, client) -> None:
        """只有终态 run 时返回 null。"""
        app_state = client.app.state.app_state
        app_state.file_task_run_repository.create_run(
            run_name="completed",
            task_type=TASK_TYPE_JAV_VIDEO_ORGANIZER,
            trigger_type=FileTaskTriggerType.MANUAL,
            status=FileTaskRunStatus.COMPLETED,
            start_time=datetime(2024, 1, 1),
        )

        response = client.get("/api/tasks/active")

        assert response.status_code == 200
        assert response.json() is None
