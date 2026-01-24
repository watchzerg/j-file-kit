import pytest

from j_file_kit.app.file_task.application.config import JavVideoOrganizeConfig

pytestmark = pytest.mark.unit


def test_jav_video_organize_config_normalizes_extensions() -> None:
    config = JavVideoOrganizeConfig(
        video_extensions={"mp4", ".mkv"},
        image_extensions={"jpg", ".png"},
        archive_extensions={"zip", ".7z"},
    )

    assert config.video_extensions == {".mp4", ".mkv"}
    assert config.image_extensions == {".jpg", ".png"}
    assert config.archive_extensions == {".zip", ".7z"}
