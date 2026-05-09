"""配置验证单元测试：workspace_root + inbox 就绪校验。"""

from pathlib import Path

import pytest

from j_file_kit.app.file_task.application import config_common as config_common_module
from j_file_kit.app.file_task.application.config_validator import (
    validate_jav_video_organizer_config,
    validate_raw_file_organizer_config,
)
from j_file_kit.app.file_task.application.jav_task_config import JavVideoOrganizeConfig
from j_file_kit.app.file_task.application.raw_task_config import RawFileOrganizeConfig

pytestmark = pytest.mark.unit


class TestJavVideoOrganizeModelPaths:
    def test_workspace_outside_jav_media_root_raises(self) -> None:
        with pytest.raises(ValueError, match="workspace_root"):
            JavVideoOrganizeConfig.model_validate(
                {"workspace_root": "/media/other/jav"},
            )


class TestValidateJavVideoOrganizerConfig:
    def test_missing_root_reports_errors(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setattr(config_common_module, "JAV_MEDIA_ROOT", tmp_path)
        ws = tmp_path / "ws"
        cfg = JavVideoOrganizeConfig.model_validate({"workspace_root": str(ws)})
        errs = validate_jav_video_organizer_config(cfg)
        assert errs

    def test_existing_workspace_and_inbox_empty_list(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setattr(config_common_module, "JAV_MEDIA_ROOT", tmp_path)
        ws = tmp_path / "ws"
        inbox = ws / "inbox"
        ws.mkdir()
        inbox.mkdir()
        cfg = JavVideoOrganizeConfig.model_validate({"workspace_root": str(ws)})
        assert validate_jav_video_organizer_config(cfg) == []


class TestValidateRawFileOrganizerConfig:
    def test_missing_dirs_reports_errors(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setattr(config_common_module, "RAW_MEDIA_ROOT", tmp_path)
        ws = tmp_path / "raw_ws"
        cfg = RawFileOrganizeConfig.model_validate({"workspace_root": str(ws)})
        errs = validate_raw_file_organizer_config(cfg)
        assert errs

    def test_ready_workspace_empty_list(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setattr(config_common_module, "RAW_MEDIA_ROOT", tmp_path)
        ws = tmp_path / "raw_ws"
        ws.mkdir()
        (ws / "inbox").mkdir()
        cfg = RawFileOrganizeConfig.model_validate({"workspace_root": str(ws)})
        assert validate_raw_file_organizer_config(cfg) == []
