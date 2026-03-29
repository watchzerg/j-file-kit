"""配置模型单元测试

覆盖 JavVideoOrganizeConfig model_validator、create_default_jav_video_organizer_task_config。
"""

import pytest

from j_file_kit.app.file_task.application.config import (
    JavVideoOrganizeConfig,
    create_default_jav_video_organizer_task_config,
)
from j_file_kit.app.file_task.domain.constants import TASK_TYPE_JAV_VIDEO_ORGANIZER

pytestmark = pytest.mark.unit

_BASE_EXTENSIONS = {
    "video_extensions": [".mp4"],
    "image_extensions": [".jpg"],
    "archive_extensions": [".zip"],
}


class TestJavVideoOrganizeConfigExtensionValidator:
    """JavVideoOrganizeConfig 扩展名自动补点"""

    def test_extensions_without_dot_get_prefixed(self) -> None:
        config = JavVideoOrganizeConfig.model_validate(
            {
                "video_extensions": ["mp4", ".mkv"],
                "image_extensions": ["jpg"],
                "archive_extensions": ["zip"],
            },
        )
        assert config.video_extensions == {".mp4", ".mkv"}
        assert config.image_extensions == {".jpg"}
        assert config.archive_extensions == {".zip"}

    def test_extensions_with_dot_unchanged(self) -> None:
        config = JavVideoOrganizeConfig.model_validate(
            {
                "video_extensions": [".mp4", ".avi"],
                "image_extensions": [".jpg"],
                "archive_extensions": [".zip"],
            },
        )
        assert config.video_extensions == {".mp4", ".avi"}

    def test_non_media_path_loads_without_error(self) -> None:
        """非 /media 路径在 model_validate 时不报错（容错加载，不在模型层校验 /media 前缀）"""
        config = JavVideoOrganizeConfig.model_validate(
            {**_BASE_EXTENSIONS, "inbox_dir": "/nonexistent/inbox"},
        )
        assert str(config.inbox_dir) == "/nonexistent/inbox"


class TestCreateDefaultJavVideoOrganizerTaskConfig:
    """create_default_jav_video_organizer_task_config 默认配置"""

    def test_returns_task_config(self) -> None:
        result = create_default_jav_video_organizer_task_config()
        assert result.type == TASK_TYPE_JAV_VIDEO_ORGANIZER
        assert result.enabled is True

    def test_contains_expected_keys(self) -> None:
        result = create_default_jav_video_organizer_task_config()
        config = result.config
        assert "video_extensions" in config
        assert "image_extensions" in config
        assert "archive_extensions" in config
        assert "inbox_dir" in config
        assert "misc_file_delete_rules" in config

    def test_video_extensions_non_empty(self) -> None:
        result = create_default_jav_video_organizer_task_config()
        assert len(result.config["video_extensions"]) > 0

    def test_default_dirs_under_media(self) -> None:
        """默认目录均在 /media 下"""
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
            assert str(config[key]).startswith("/media/"), f"{key} 应在 /media 下"
