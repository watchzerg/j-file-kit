"""配置 API 集成测试。"""

from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from j_file_kit.api.app import create_app

pytestmark = pytest.mark.integration


class TestGetConfig:
    """GET /api/file-task/config/jav-video-organizer"""

    def test_get_config_success(self, client) -> None:
        response = client.get("/api/file-task/config/jav-video-organizer")
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "jav_video_organizer"
        assert "enabled" in data
        assert "config" in data

    def test_get_config_not_found(self, tmp_path: Path) -> None:
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True)
        config_path = config_dir / "task_config.yaml"
        config_path.write_text(
            yaml.dump(
                {"other_task": {"enabled": True, "config": {}}},
                allow_unicode=True,
            ),
            encoding="utf-8",
        )

        app = create_app(base_dir=tmp_path)
        with TestClient(app) as c:
            response = c.get("/api/file-task/config/jav-video-organizer")
        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "CONFIG_NOT_FOUND"


class TestUpdateConfig:
    """PATCH /api/file-task/config/jav-video-organizer"""

    def test_update_config_success(
        self,
        monkeypatch: pytest.MonkeyPatch,
        client,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setattr(
            "j_file_kit.app.file_task.application.config_common.JAV_MEDIA_ROOT",
            tmp_path,
        )
        ws = tmp_path / "jav_ws"
        response = client.patch(
            "/api/file-task/config/jav-video-organizer",
            json={"config": {"workspace_root": str(ws)}},
        )
        assert response.status_code == 200
        assert response.json()["code"] == "SUCCESS"
        assert ws.is_dir()
        assert (ws / "inbox").is_dir()

    def test_update_config_validation_failure(self, client) -> None:
        """workspace_root 不在 JAV_MEDIA_ROOT 下时合并模型失败。"""
        response = client.patch(
            "/api/file-task/config/jav-video-organizer",
            json={"config": {"workspace_root": "/etc"}},
        )
        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "INVALID_CONFIG"


class TestGetRawConfig:
    """GET /api/file-task/config/raw-file-organizer"""

    def test_get_raw_config_success(self, client) -> None:
        response = client.get("/api/file-task/config/raw-file-organizer")
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "raw_file_organizer"
        assert "enabled" in data
        assert "config" in data


class TestUpdateRawConfig:
    """PATCH /api/file-task/config/raw-file-organizer"""

    def test_update_raw_config_success(
        self,
        monkeypatch: pytest.MonkeyPatch,
        client,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setattr(
            "j_file_kit.app.file_task.application.config_common.RAW_MEDIA_ROOT",
            tmp_path,
        )
        ws = tmp_path / "raw_ws"
        response = client.patch(
            "/api/file-task/config/raw-file-organizer",
            json={"config": {"workspace_root": str(ws)}},
        )
        assert response.status_code == 200
        assert response.json()["code"] == "SUCCESS"
        assert (ws / "inbox").is_dir()
