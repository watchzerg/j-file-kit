"""配置 API 集成测试

覆盖 GET、PATCH /api/file-task/config/jav-video-organizer 端点。
"""

from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from j_file_kit.api.app import create_app

pytestmark = pytest.mark.integration


class TestGetConfig:
    """GET /api/file-task/config/jav-video-organizer"""

    def test_get_config_success(self, client) -> None:
        """获取配置返回 type、enabled、config"""
        response = client.get("/api/file-task/config/jav-video-organizer")
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "jav_video_organizer"
        assert "enabled" in data
        assert "config" in data

    def test_get_config_not_found(self, tmp_path: Path) -> None:
        """配置不存在时返回 404"""
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
        """更新配置成功"""
        monkeypatch.setattr(
            "j_file_kit.app.file_task.application.config_validator.MEDIA_ROOT",
            tmp_path,
        )
        inbox = tmp_path / "inbox"
        inbox.mkdir()
        response = client.patch(
            "/api/file-task/config/jav-video-organizer",
            json={"config": {"inbox_dir": str(inbox)}},
        )
        assert response.status_code == 200
        assert response.json()["code"] == "SUCCESS"

    def test_update_config_validation_failure(
        self,
        monkeypatch: pytest.MonkeyPatch,
        client,
        tmp_path: Path,
    ) -> None:
        """校验失败（如目录重复）时返回 400"""
        monkeypatch.setattr(
            "j_file_kit.app.file_task.application.config_validator.MEDIA_ROOT",
            tmp_path,
        )
        path = tmp_path / "shared"
        path.mkdir()
        response = client.patch(
            "/api/file-task/config/jav-video-organizer",
            json={
                "config": {
                    "inbox_dir": str(path),
                    "sorted_dir": str(path),
                    "unsorted_dir": str(path),
                },
            },
        )
        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "INVALID_CONFIG"
