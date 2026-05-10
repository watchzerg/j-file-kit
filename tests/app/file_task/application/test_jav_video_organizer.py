"""JAV 视频整理任务单元测试。"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from j_file_kit.app.file_task.application.config_common import (
    InboxDeleteRules,
    jav_workspace_paths,
)
from j_file_kit.app.file_task.application.jav_video_organizer import JavVideoOrganizer
from j_file_kit.app.file_task.domain.constants import TASK_TYPE_JAV_VIDEO_ORGANIZER
from j_file_kit.app.file_task.domain.jav_defaults import (
    DEFAULT_JAV_FILENAME_STRIP_SUBSTRINGS,
)
from j_file_kit.app.file_task.domain.organizer_defaults import (
    DEFAULT_ARCHIVE_EXTENSIONS,
    DEFAULT_IMAGE_EXTENSIONS,
    DEFAULT_MISC_FILE_DELETE_EXTENSIONS,
    DEFAULT_SUBTITLE_EXTENSIONS,
    DEFAULT_VIDEO_EXTENSIONS,
)
from j_file_kit.app.file_task.domain.task_config import TaskConfig

pytestmark = pytest.mark.unit


@pytest.fixture
def task_config_with_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> TaskConfig:
    monkeypatch.setattr(
        "j_file_kit.app.file_task.application.config_common.JAV_MEDIA_ROOT",
        tmp_path,
    )
    monkeypatch.setattr(
        "j_file_kit.app.file_task.application.jav_task_config.MEDIA_ROOT",
        tmp_path,
    )
    ws = tmp_path / "jav_ws"
    ws.mkdir()
    (ws / "inbox").mkdir()
    return TaskConfig(
        type=TASK_TYPE_JAV_VIDEO_ORGANIZER,
        enabled=True,
        config={
            "workspace_root": str(ws),
            "misc_file_delete_rules": {"max_size": 100},
            "inbox_delete_rules": {
                "exact_stems": ["Thumbs"],
                "max_size_bytes": 0,
            },
        },
    )


@pytest.fixture
def organizer(
    task_config_with_workspace: TaskConfig,
    tmp_path: Path,
) -> JavVideoOrganizer:
    return JavVideoOrganizer(
        task_config=task_config_with_workspace,
        log_dir=tmp_path,
        file_result_repository=MagicMock(),
    )


class TestJavVideoOrganizerTaskType:
    def test_returns_constant(self, organizer: JavVideoOrganizer) -> None:
        assert organizer.task_type == TASK_TYPE_JAV_VIDEO_ORGANIZER


class TestJavVideoOrganizerRun:
    def test_missing_inbox_raises(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setattr(
            "j_file_kit.app.file_task.application.config_common.JAV_MEDIA_ROOT",
            tmp_path,
        )
        monkeypatch.setattr(
            "j_file_kit.app.file_task.application.jav_task_config.MEDIA_ROOT",
            tmp_path,
        )
        ws = tmp_path / "jav_ws"
        ws.mkdir()
        config = TaskConfig(
            type=TASK_TYPE_JAV_VIDEO_ORGANIZER,
            enabled=True,
            config={
                "workspace_root": str(ws),
                "misc_file_delete_rules": {},
            },
        )
        organizer = JavVideoOrganizer(
            task_config=config,
            log_dir=tmp_path,
            file_result_repository=MagicMock(),
        )
        with pytest.raises(ValueError, match="收件箱目录不存在"):
            organizer.run(run_id=1)


class TestJavVideoOrganizerCreateAnalyzeConfig:
    def test_maps_all_fields(self, organizer: JavVideoOrganizer) -> None:
        paths = jav_workspace_paths(organizer.file_config.workspace_root)
        config = organizer._create_analyze_config()
        assert config.video_extensions == set(DEFAULT_VIDEO_EXTENSIONS)
        assert config.image_extensions == set(DEFAULT_IMAGE_EXTENSIONS)
        assert config.subtitle_extensions == set(DEFAULT_SUBTITLE_EXTENSIONS)
        assert config.archive_extensions == set(DEFAULT_ARCHIVE_EXTENSIONS)
        assert config.sorted_dir == paths.sorted_dir
        assert config.unsorted_dir == paths.unsorted_dir
        assert config.archive_dir == paths.archive_dir
        assert config.misc_dir == paths.misc_dir
        assert config.misc_file_delete_rules["max_size"] == 100
        assert config.misc_file_delete_rules["extensions"] == sorted(
            DEFAULT_MISC_FILE_DELETE_EXTENSIONS,
        )
        assert config.inbox_delete_rules == InboxDeleteRules(
            exact_stems={"Thumbs"},
            max_size_bytes=0,
        )
        assert config.video_small_delete_bytes is None
        assert (
            config.jav_filename_strip_substrings
            == DEFAULT_JAV_FILENAME_STRIP_SUBSTRINGS
        )

    def test_strip_misc_extensions_from_yaml_also_removes_keywords(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        # YAML 中即使写了 misc_file_delete_rules.{extensions, keywords}，
        # JavVideoOrganizeConfig.model_validator 也会剔除这两个非可调键，
        # 之后 _create_analyze_config 注入的 extensions 仅来自 organizer_defaults。
        monkeypatch.setattr(
            "j_file_kit.app.file_task.application.config_common.JAV_MEDIA_ROOT",
            tmp_path,
        )
        monkeypatch.setattr(
            "j_file_kit.app.file_task.application.jav_task_config.MEDIA_ROOT",
            tmp_path,
        )
        ws = tmp_path / "jav_ws"
        ws.mkdir()
        (ws / "inbox").mkdir()
        tc = TaskConfig(
            type=TASK_TYPE_JAV_VIDEO_ORGANIZER,
            enabled=True,
            config={
                "workspace_root": str(ws),
                "misc_file_delete_rules": {
                    "max_size": 200,
                    "extensions": [".legacy"],
                    "keywords": ["legacy_keyword"],
                },
            },
        )
        organizer = JavVideoOrganizer(
            task_config=tc,
            log_dir=tmp_path,
            file_result_repository=MagicMock(),
        )
        # 模型层已剔除 extensions / keywords
        assert "extensions" not in organizer.file_config.misc_file_delete_rules
        assert "keywords" not in organizer.file_config.misc_file_delete_rules

        config = organizer._create_analyze_config()
        # _create_analyze_config 用 organizer_defaults 重新注入 extensions
        assert config.misc_file_delete_rules["extensions"] == sorted(
            DEFAULT_MISC_FILE_DELETE_EXTENSIONS,
        )
        # max_size 透传保留
        assert config.misc_file_delete_rules["max_size"] == 200
        # keywords 不应出现在 analyze 配置中
        assert "keywords" not in config.misc_file_delete_rules

    def test_video_small_delete_bytes_propagated(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setattr(
            "j_file_kit.app.file_task.application.config_common.JAV_MEDIA_ROOT",
            tmp_path,
        )
        monkeypatch.setattr(
            "j_file_kit.app.file_task.application.jav_task_config.MEDIA_ROOT",
            tmp_path,
        )
        ws = tmp_path / "jav_ws"
        ws.mkdir()
        (ws / "inbox").mkdir()
        tc = TaskConfig(
            type=TASK_TYPE_JAV_VIDEO_ORGANIZER,
            enabled=True,
            config={
                "workspace_root": str(ws),
                "misc_file_delete_rules": {},
                "video_small_delete_bytes": 2048,
            },
        )
        organizer = JavVideoOrganizer(
            task_config=tc,
            log_dir=tmp_path,
            file_result_repository=MagicMock(),
        )
        config = organizer._create_analyze_config()
        assert config.video_small_delete_bytes == 2048
