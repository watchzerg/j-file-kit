"""RawFileOrganizer 单元测试。"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from j_file_kit.app.file_task.application.config_common import raw_workspace_paths
from j_file_kit.app.file_task.application.raw_file_organizer import RawFileOrganizer
from j_file_kit.app.file_task.domain.constants import TASK_TYPE_RAW_FILE_ORGANIZER
from j_file_kit.app.file_task.domain.organizer_defaults import (
    DEFAULT_ARCHIVE_EXTENSIONS,
    DEFAULT_IMAGE_EXTENSIONS,
    DEFAULT_MUSIC_EXTENSIONS,
    DEFAULT_SUBTITLE_EXTENSIONS,
    DEFAULT_VIDEO_EXTENSIONS,
)
from j_file_kit.app.file_task.domain.task_config import TaskConfig
from j_file_kit.app.file_task.domain.task_run import FileTaskRunStatistics

pytestmark = pytest.mark.unit


def test_task_type(tmp_path: Path) -> None:
    tc = TaskConfig(
        type=TASK_TYPE_RAW_FILE_ORGANIZER,
        enabled=True,
        config={
            "workspace_root": "/media/raw_workspace",
        },
    )
    org = RawFileOrganizer(
        task_config=tc,
        log_dir=tmp_path / "logs",
        file_result_repository=MagicMock(),
    )
    assert org.task_type == TASK_TYPE_RAW_FILE_ORGANIZER


def test_run_requires_existing_inbox(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "j_file_kit.app.file_task.application.config_common.RAW_MEDIA_ROOT",
        tmp_path,
    )
    monkeypatch.setattr(
        "j_file_kit.app.file_task.application.raw_task_config.MEDIA_ROOT",
        tmp_path,
    )
    ws = tmp_path / "raw_ws"
    ws.mkdir()
    tc = TaskConfig(
        type=TASK_TYPE_RAW_FILE_ORGANIZER,
        enabled=True,
        config={"workspace_root": str(ws)},
    )
    org = RawFileOrganizer(
        task_config=tc,
        log_dir=tmp_path / "logs",
        file_result_repository=MagicMock(),
    )
    with pytest.raises(ValueError, match="收件箱目录不存在"):
        org.run(run_id=1)


def test_run_returns_empty_statistics(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "j_file_kit.app.file_task.application.config_common.RAW_MEDIA_ROOT",
        tmp_path,
    )
    monkeypatch.setattr(
        "j_file_kit.app.file_task.application.raw_task_config.MEDIA_ROOT",
        tmp_path,
    )
    ws = tmp_path / "raw_ws"
    ws.mkdir()
    (ws / "inbox").mkdir()
    tc = TaskConfig(
        type=TASK_TYPE_RAW_FILE_ORGANIZER,
        enabled=True,
        config={"workspace_root": str(ws)},
    )
    repo = MagicMock()
    repo.get_statistics.return_value = {
        "total_items": 0,
        "success_items": 0,
        "error_items": 0,
        "skipped_items": 0,
        "warning_items": 0,
        "total_duration_ms": 0.0,
    }
    org = RawFileOrganizer(
        task_config=tc,
        log_dir=tmp_path / "logs",
        file_result_repository=repo,
    )
    assert org.run(run_id=1) == FileTaskRunStatistics()


class TestRawFileOrganizerCreateAnalyzeConfig:
    """与 JAV 对称：验证 ``_create_analyze_config`` 的字段映射完整性。"""

    @pytest.fixture
    def organizer(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> RawFileOrganizer:
        monkeypatch.setattr(
            "j_file_kit.app.file_task.application.config_common.RAW_MEDIA_ROOT",
            tmp_path,
        )
        monkeypatch.setattr(
            "j_file_kit.app.file_task.application.raw_task_config.MEDIA_ROOT",
            tmp_path,
        )
        ws = tmp_path / "raw_ws"
        ws.mkdir()
        tc = TaskConfig(
            type=TASK_TYPE_RAW_FILE_ORGANIZER,
            enabled=True,
            config={"workspace_root": str(ws)},
        )
        return RawFileOrganizer(
            task_config=tc,
            log_dir=tmp_path / "logs",
            file_result_repository=MagicMock(),
        )

    def test_maps_all_path_fields(self, organizer: RawFileOrganizer) -> None:
        paths = raw_workspace_paths(organizer.file_config.workspace_root)
        config = organizer._create_analyze_config()
        assert config.folders_to_delete == paths.folders_to_delete
        assert config.folders_video == paths.folders_video
        assert config.folders_compressed == paths.folders_compressed
        assert config.folders_pic == paths.folders_pic
        assert config.folders_audio == paths.folders_audio
        assert config.folders_misc == paths.folders_misc
        assert config.files_to_delete == paths.files_to_delete
        assert config.files_video_jav == paths.files_video_jav
        assert config.files_video_us == paths.files_video_us
        assert config.files_video_jav_vr == paths.files_video_jav_vr
        assert config.files_video_us_vr == paths.files_video_us_vr
        assert config.files_video_movie == paths.files_video_movie
        assert config.files_video_misc == paths.files_video_misc
        assert config.files_compressed == paths.files_compressed
        assert config.files_pic == paths.files_pic
        assert config.files_audio == paths.files_audio
        assert config.files_misc == paths.files_misc

    def test_maps_all_extension_sets(self, organizer: RawFileOrganizer) -> None:
        config = organizer._create_analyze_config()
        assert config.video_extensions == set(DEFAULT_VIDEO_EXTENSIONS)
        assert config.image_extensions == set(DEFAULT_IMAGE_EXTENSIONS)
        assert config.subtitle_extensions == set(DEFAULT_SUBTITLE_EXTENSIONS)
        assert config.archive_extensions == set(DEFAULT_ARCHIVE_EXTENSIONS)
        # audio_extensions 直接来自 DEFAULT_MUSIC_EXTENSIONS（音乐扩展名作为 Raw 音频扩展名）
        assert config.audio_extensions == set(DEFAULT_MUSIC_EXTENSIONS)
