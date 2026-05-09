"""配置模型单元测试。"""

import pytest
from pydantic import ValidationError

from j_file_kit.app.file_task.application.config_common import InboxDeleteRules
from j_file_kit.app.file_task.application.default_task_configs import (
    create_default_jav_video_organizer_task_config,
    create_default_raw_file_organizer_task_config,
)
from j_file_kit.app.file_task.application.jav_task_config import JavVideoOrganizeConfig
from j_file_kit.app.file_task.application.raw_task_config import RawFileOrganizeConfig
from j_file_kit.app.file_task.domain.constants import (
    TASK_TYPE_JAV_VIDEO_ORGANIZER,
    TASK_TYPE_RAW_FILE_ORGANIZER,
)

pytestmark = pytest.mark.unit


class TestJavVideoOrganizeConfigDirConstraint:
    def test_non_media_workspace_raises(self) -> None:
        with pytest.raises(ValidationError):
            JavVideoOrganizeConfig.model_validate(
                {"workspace_root": "/etc/jav", "misc_file_delete_rules": {}},
            )

    def test_wrong_media_branch_raises(self) -> None:
        with pytest.raises(ValidationError):
            JavVideoOrganizeConfig.model_validate(
                {
                    "workspace_root": "/media/raw_workspace",
                    "misc_file_delete_rules": {},
                },
            )


class TestJavVideoOrganizeConfigMiscRules:
    def test_extensions_key_stripped(self) -> None:
        config = JavVideoOrganizeConfig.model_validate(
            {
                "misc_file_delete_rules": {
                    "extensions": [".tmp", ".bak"],
                    "keywords": ["sample"],
                    "max_size": 100,
                },
            },
        )
        assert "extensions" not in config.misc_file_delete_rules
        assert "keywords" not in config.misc_file_delete_rules
        assert config.misc_file_delete_rules == {
            "max_size": 100,
        }


class TestInboxDeleteRules:
    def test_drops_empty_strings(self) -> None:
        rules = InboxDeleteRules.model_validate(
            {"exact_stems": ["", "keep"]},
        )
        assert rules.exact_stems == {"keep"}


class TestCreateDefaultJavVideoOrganizerTaskConfig:
    def test_returns_task_config(self) -> None:
        result = create_default_jav_video_organizer_task_config()
        assert result.type == TASK_TYPE_JAV_VIDEO_ORGANIZER
        assert result.enabled is True

    def test_contains_expected_keys(self) -> None:
        result = create_default_jav_video_organizer_task_config()
        config = result.config
        assert config["workspace_root"] == "/media/jav_workspace"
        assert "misc_file_delete_rules" in config
        misc_raw = config["misc_file_delete_rules"]
        assert isinstance(misc_raw, dict)
        assert "extensions" not in misc_raw
        assert set(misc_raw.keys()) == {"max_size"}
        assert "inbox_delete_rules" in config
        inbox_raw = config["inbox_delete_rules"]
        assert isinstance(inbox_raw, dict)
        assert set(inbox_raw.keys()) == {"exact_stems", "max_size_bytes"}
        InboxDeleteRules.model_validate(inbox_raw)
        assert "serial_id_rules" not in config
        assert "video_extensions" not in config
        assert "jav_filename_strip_substrings" not in config
        assert config["video_small_delete_bytes"] == 200 * 1024 * 1024


class TestRawFileOrganizeConfigDirConstraint:
    def test_non_media_workspace_raises(self) -> None:
        with pytest.raises(ValidationError):
            RawFileOrganizeConfig.model_validate({"workspace_root": "/etc/raw"})

    def test_jav_workspace_raises(self) -> None:
        with pytest.raises(ValidationError):
            RawFileOrganizeConfig.model_validate(
                {"workspace_root": "/media/jav_workspace"},
            )


class TestCreateDefaultRawFileOrganizerTaskConfig:
    def test_returns_task_config(self) -> None:
        result = create_default_raw_file_organizer_task_config()
        assert result.type == TASK_TYPE_RAW_FILE_ORGANIZER
        assert result.enabled is True

    def test_workspace_under_raw_root(self) -> None:
        result = create_default_raw_file_organizer_task_config()
        assert result.config["workspace_root"] == "/media/raw_workspace"
