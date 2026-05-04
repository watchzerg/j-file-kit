"""任务 API 集成测试

覆盖 POST start、GET status、POST cancel、GET list 端点。
"""

import pytest

from j_file_kit.app.file_task.domain.constants import TASK_TYPE_JAV_VIDEO_ORGANIZER

pytestmark = pytest.mark.integration


class TestStartTask:
    """POST /api/tasks/{task_type}/start"""

    def test_start_task_success(self, client) -> None:
        """启动任务返回 run_id、run_name、status"""
        response = client.post(
            f"/api/tasks/{TASK_TYPE_JAV_VIDEO_ORGANIZER}/start",
            json={"dry_run": False},
        )
        assert response.status_code == 200
        data = response.json()
        assert "run_id" in data
        assert data["run_id"] > 0
        assert "run_name" in data
        assert "status" in data

    def test_start_task_invalid_task_type(self, client) -> None:
        """未知任务类型返回 404"""
        response = client.post(
            "/api/tasks/unknown_task/start",
            json={"dry_run": False},
        )
        assert response.status_code == 404
        assert "任务不存在" in response.json()["detail"]

    def test_start_task_invalid_trigger_type(self, client) -> None:
        """无效触发类型返回 400"""
        response = client.post(
            f"/api/tasks/{TASK_TYPE_JAV_VIDEO_ORGANIZER}/start",
            json={"dry_run": False, "trigger_type": "invalid"},
        )
        assert response.status_code == 400
        assert "无效的触发类型" in response.json()["detail"]


class TestGetRunStatus:
    """GET /api/tasks/{run_id}"""

    def test_get_run_status_success(self, client) -> None:
        """查询执行实例状态"""
        start_resp = client.post(
            f"/api/tasks/{TASK_TYPE_JAV_VIDEO_ORGANIZER}/start",
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

    def test_cancel_run_success(
        self,
        monkeypatch: pytest.MonkeyPatch,
        client,
        tmp_path,
    ) -> None:
        """取消执行实例

        需配置有效 inbox_dir 使任务运行足够久以便取消。
        创建多文件以延长扫描时间。
        """
        monkeypatch.setattr(
            "j_file_kit.app.file_task.application.config.JAV_MEDIA_ROOT",
            tmp_path,
        )
        inbox = tmp_path / "inbox"
        inbox.mkdir()
        for i in range(100):
            (inbox / f"file_{i}.mp4").touch()

        config_resp = client.patch(
            "/api/file-task/config/jav-video-organizer",
            json={
                "config": {
                    "inbox_dir": str(inbox),
                    "sorted_dir": None,
                    "unsorted_dir": None,
                    "archive_dir": None,
                    "misc_dir": None,
                },
            },
        )
        assert config_resp.status_code == 200

        start_resp = client.post(
            f"/api/tasks/{TASK_TYPE_JAV_VIDEO_ORGANIZER}/start",
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

    def test_cancel_run_already_completed(self, client) -> None:
        """对已完成的 run 取消返回 400"""
        start_resp = client.post(
            f"/api/tasks/{TASK_TYPE_JAV_VIDEO_ORGANIZER}/start",
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

    def test_list_runs_with_items(self, client) -> None:
        """有执行记录时返回列表"""
        client.post(
            f"/api/tasks/{TASK_TYPE_JAV_VIDEO_ORGANIZER}/start",
            json={"dry_run": False},
        )
        response = client.get("/api/tasks")
        assert response.status_code == 200
        runs = response.json()["runs"]
        assert len(runs) >= 1
        assert "run_id" in runs[0]
        assert "run_name" in runs[0]
        assert "status" in runs[0]
