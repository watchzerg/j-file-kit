"""System metadata API integration tests."""

from pathlib import Path

import pytest

import j_file_kit.app.system.api as system_api

pytestmark = pytest.mark.integration


def test_get_system_info(
    client,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    media_root = tmp_path / "media"
    monkeypatch.setattr(system_api, "MEDIA_ROOT", media_root)
    monkeypatch.setattr(system_api.os.path, "ismount", lambda path: path == media_root)

    response = client.get("/api/system/info")

    assert response.status_code == 200
    data = response.json()
    assert data["app_version"] == "dev"
    assert data["env"] == "development"
    assert data["base_dir"] == str(tmp_path)
    assert data["media_root"] == str(media_root)
    assert data["jav_media_root"] == str(media_root / "jav_workspace")
    assert data["raw_media_root"] == str(media_root / "raw_workspace")
    assert data["media_mounted"] is True


def test_get_file_type_defaults(client) -> None:
    response = client.get("/api/system/file-type-defaults")

    assert response.status_code == 200
    data = response.json()
    assert data["extensions"]["video"] == sorted(
        data["extensions"]["video"],
        key=str.casefold,
    )
    assert ".mp4" in data["extensions"]["video"]
    assert ".jpg" in data["extensions"]["image"]
    assert ".rar" in data["extensions"]["archive"]
    assert ".mp3" in data["extensions"]["music"]
    assert ".nfo" in data["extensions"]["misc_delete"]
    assert data["raw"]["cleanup_junk_max_bytes"] == 100 * 1024 * 1024
    assert "FC2-PPV" in data["raw"]["junk_keywords"]
    assert "VR" in data["raw"]["camelcase_no_split_words"]
    assert "3DSVR" in data["jav"]["vr_serial_prefixes"]
    assert "BBS-2048" in data["jav"]["filename_strip_substrings"]
