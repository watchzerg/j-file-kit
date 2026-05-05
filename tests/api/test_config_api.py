"""配置 API 集成测试

覆盖 GET、PATCH /api/file-task/config/jav-video-organizer 端点。
"""

from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from j_file_kit.api.app import create_app
from j_file_kit.app.file_task.application.config import (
    RAW_FILE_ORGANIZE_PATH_FIELD_NAMES,
)

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
            "j_file_kit.app.file_task.application.config.JAV_MEDIA_ROOT",
            tmp_path,
        )
        for name in ("inbox", "sorted", "unsorted", "archive", "misc"):
            (tmp_path / name).mkdir()
        response = client.patch(
            "/api/file-task/config/jav-video-organizer",
            json={
                "config": {
                    "inbox_dir": str(tmp_path / "inbox"),
                    "sorted_dir": str(tmp_path / "sorted"),
                    "unsorted_dir": str(tmp_path / "unsorted"),
                    "archive_dir": str(tmp_path / "archive"),
                    "misc_dir": str(tmp_path / "misc"),
                },
            },
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
            "j_file_kit.app.file_task.application.config.JAV_MEDIA_ROOT",
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
                    "archive_dir": None,
                    "misc_dir": None,
                },
            },
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
            "j_file_kit.app.file_task.application.config.RAW_MEDIA_ROOT",
            tmp_path,
        )
        for name in RAW_FILE_ORGANIZE_PATH_FIELD_NAMES:
            (tmp_path / name).mkdir()
        cfg = {
            name: str(tmp_path / name) for name in RAW_FILE_ORGANIZE_PATH_FIELD_NAMES
        }
        response = client.patch(
            "/api/file-task/config/raw-file-organizer",
            json={"config": cfg},
        )
        assert response.status_code == 200
        assert response.json()["code"] == "SUCCESS"
