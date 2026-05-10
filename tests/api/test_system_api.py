"""System metadata API integration tests."""

from pathlib import Path

import pytest

import j_file_kit.app.file_task.application.config_common as config_common
import j_file_kit.app.system.api as system_api

pytestmark = pytest.mark.integration


def test_get_system_info(
    client,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    media_root = tmp_path / "media"
    jav_root = media_root / "jav_workspace"
    raw_root = media_root / "raw_workspace"
    monkeypatch.setattr(system_api, "MEDIA_ROOT", media_root)
    monkeypatch.setattr(config_common, "JAV_MEDIA_ROOT", jav_root)
    monkeypatch.setattr(config_common, "RAW_MEDIA_ROOT", raw_root)
    monkeypatch.setattr(system_api.os.path, "ismount", lambda path: path == media_root)

    response = client.get("/api/system/info")

    assert response.status_code == 200
    data = response.json()
    assert data["app_version"] == "dev"
    assert data["env"] == "development"
    assert data["base_dir"] == str(tmp_path)
    assert data["media_root"] == str(media_root)
    assert data["jav_media_root"] == str(jav_root)
    assert data["raw_media_root"] == str(raw_root)
    assert data["media_mounted"] is True
