"""配置模型单元测试

覆盖 JavVideoOrganizeConfig model_validator、create_default_jav_video_organizer_task_config。
"""

import pytest
from pydantic import ValidationError

from j_file_kit.app.file_task.application.config import (
    InboxDeleteRules,
    JavVideoOrganizeConfig,
    create_default_jav_video_organizer_task_config,
)
from j_file_kit.app.file_task.domain.constants import TASK_TYPE_JAV_VIDEO_ORGANIZER

pytestmark = pytest.mark.unit

_BASE_EXTENSIONS = {
    "video_extensions": [".mp4"],
    "image_extensions": [".jpg"],
    "subtitle_extensions": [".srt"],
    "archive_extensions": [".zip"],
}


class TestJavVideoOrganizeConfigExtensionValidator:
    """JavVideoOrganizeConfig 扩展名自动补点"""

    def test_extensions_without_dot_get_prefixed(self) -> None:
        config = JavVideoOrganizeConfig.model_validate(
            {
                **_BASE_EXTENSIONS,
                "video_extensions": ["mp4", ".mkv"],
                "image_extensions": ["jpg"],
                "subtitle_extensions": ["srt"],
                "archive_extensions": ["zip"],
            },
        )
        assert config.video_extensions == {".mp4", ".mkv"}
        assert config.image_extensions == {".jpg"}
        assert config.archive_extensions == {".zip"}

    def test_extensions_with_dot_unchanged(self) -> None:
        config = JavVideoOrganizeConfig.model_validate(
            {
                **_BASE_EXTENSIONS,
                "video_extensions": [".mp4", ".avi"],
                "image_extensions": [".jpg"],
                "subtitle_extensions": [".srt"],
                "archive_extensions": [".zip"],
            },
        )
        assert config.video_extensions == {".mp4", ".avi"}

    def test_non_media_path_raises(self) -> None:
        """非 /media 路径在 model_validate 时报错（/media 约束为模型不变量）"""
        with pytest.raises(ValidationError):
            JavVideoOrganizeConfig.model_validate(
                {**_BASE_EXTENSIONS, "inbox_dir": "/nonexistent/inbox"},
            )


class TestJavFilenameStripSubstrings:
    """jav_filename_strip_substrings：未配置或空即不启用（与模型 default_factory=tuple 一致）"""

    def test_omitted_is_empty_tuple(self) -> None:
        config = JavVideoOrganizeConfig.model_validate(dict(_BASE_EXTENSIONS))
        assert config.jav_filename_strip_substrings == ()

    def test_empty_list_is_empty_tuple(self) -> None:
        config = JavVideoOrganizeConfig.model_validate(
            {**_BASE_EXTENSIONS, "jav_filename_strip_substrings": []},
        )
        assert config.jav_filename_strip_substrings == ()


class TestInboxDeleteRules:
    """InboxDeleteRules 校验"""

    def test_drops_empty_strings(self) -> None:
        rules = InboxDeleteRules.model_validate(
            {"exact_stems": ["", "keep"], "keywords": ["", "kw"]},
        )
        assert rules.exact_stems == {"keep"}
        assert rules.keywords == ["kw"]


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
        assert "inbox_delete_rules" in config
        inbox_raw = config["inbox_delete_rules"]
        assert isinstance(inbox_raw, dict)
        assert set(inbox_raw.keys()) == {"exact_stems", "keywords", "max_size_bytes"}
        InboxDeleteRules.model_validate(inbox_raw)
        assert "serial_id_rules" not in config
        assert config["video_small_delete_bytes"] == 200 * 1024 * 1024
        assert config["jav_filename_strip_substrings"] == [
            "BBS-2048",
            "BIG-2048",
            "CHD-1080",
            "DHD-1080",
            "FUN-2048",
            "HJD-2048",
            "PP-168",
            "RH-2048",
            "XHD-1080",
            "CCTV-12306",
        ]

    def test_default_strip_round_trips_through_jav_config_model(self) -> None:
        """默认 dict 经 JavVideoOrganizeConfig 解析后 strip 为 10 项元组。"""
        raw = create_default_jav_video_organizer_task_config().config
        parsed = JavVideoOrganizeConfig.model_validate(raw)
        assert parsed.jav_filename_strip_substrings == tuple(
            raw["jav_filename_strip_substrings"],
        )

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
