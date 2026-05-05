"""配置模型单元测试

覆盖 JavVideoOrganizeConfig model_validator、create_default_jav_video_organizer_task_config。
"""

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
    """JavVideoOrganizeConfig.validate_dir_paths_under_media_root"""

    def test_non_media_path_raises(self) -> None:
        """非 /media/jav_workspace 路径在 model_validate 时报错（JAV_MEDIA_ROOT 约束为模型不变量）"""
        with pytest.raises(ValidationError):
            JavVideoOrganizeConfig.model_validate(
                {"inbox_dir": "/nonexistent/inbox", "misc_file_delete_rules": {}},
            )

    def test_media_root_path_raises(self) -> None:
        """在 /media 下但不在 /media/jav_workspace 下的路径也应报错（下沉后旧路径不再合法）"""
        with pytest.raises(ValidationError):
            JavVideoOrganizeConfig.model_validate(
                {"inbox_dir": "/media/inbox", "misc_file_delete_rules": {}},
            )


class TestJavVideoOrganizeConfigMiscRules:
    """misc_file_delete_rules：YAML 中的 extensions/keywords 键须剔除（代码常量为准）"""

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
    """InboxDeleteRules 校验"""

    def test_drops_empty_strings(self) -> None:
        rules = InboxDeleteRules.model_validate(
            {"exact_stems": ["", "keep"]},
        )
        assert rules.exact_stems == {"keep"}


class TestCreateDefaultJavVideoOrganizerTaskConfig:
    """create_default_jav_video_organizer_task_config 默认配置"""

    def test_returns_task_config(self) -> None:
        result = create_default_jav_video_organizer_task_config()
        assert result.type == TASK_TYPE_JAV_VIDEO_ORGANIZER
        assert result.enabled is True

    def test_contains_expected_keys(self) -> None:
        result = create_default_jav_video_organizer_task_config()
        config = result.config
        assert "inbox_dir" in config
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

    def test_default_dirs_under_jav(self) -> None:
        """默认目录均在 /media/jav_workspace 下"""
        result = create_default_jav_video_organizer_task_config()
        config = result.config
        for key in (
            "inbox_dir",
            "sorted_dir",
            "unsorted_dir",
            "archive_dir",
            "misc_dir",
        ):
            assert config[key] is not None
            assert str(config[key]).startswith("/media/jav_workspace/"), (
                f"{key} 应在 /media/jav_workspace 下"
            )


class TestRawFileOrganizeConfigDirConstraint:
    """RawFileOrganizeConfig 路径必须在 RAW_MEDIA_ROOT 下。"""

    def test_non_media_path_raises(self) -> None:
        with pytest.raises(ValidationError):
            RawFileOrganizeConfig.model_validate({"inbox_dir": "/nonexistent/inbox"})

    def test_jav_root_path_raises(self) -> None:
        with pytest.raises(ValidationError):
            RawFileOrganizeConfig.model_validate(
                {"inbox_dir": "/media/jav_workspace/inbox"},
            )


class TestCreateDefaultRawFileOrganizerTaskConfig:
    """create_default_raw_file_organizer_task_config"""

    def test_returns_task_config(self) -> None:
        result = create_default_raw_file_organizer_task_config()
        assert result.type == TASK_TYPE_RAW_FILE_ORGANIZER
        assert result.enabled is True

    def test_all_keys_under_raw_workspace(self) -> None:
        result = create_default_raw_file_organizer_task_config()
        for key, val in result.config.items():
            assert val is not None
            assert str(val).startswith("/media/raw_workspace/"), key
