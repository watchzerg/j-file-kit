"""file_task application 层测试 fixtures

适合放置：临时 YAML 配置文件路径、具体任务配置对象构造器。
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from j_file_kit.app.file_task.application.config import (
    AnalyzeConfig,
    JavVideoOrganizeConfig,
)


@pytest.fixture
def base_extensions() -> dict[str, list[str]]:
    return {
        "video_extensions": [".mp4", ".mkv"],
        "image_extensions": [".jpg", ".png"],
        "archive_extensions": [".zip"],
    }


@pytest.fixture
def jav_video_organize_config_factory(
    base_extensions: dict[str, list[str]],
) -> Callable[..., JavVideoOrganizeConfig]:
    def _create(
        inbox_dir: Path | None = None,
        sorted_dir: Path | None = None,
        unsorted_dir: Path | None = None,
        archive_dir: Path | None = None,
        misc_dir: Path | None = None,
        **overrides: object,
    ) -> JavVideoOrganizeConfig:
        config = {
            "inbox_dir": inbox_dir,
            "sorted_dir": sorted_dir,
            "unsorted_dir": unsorted_dir,
            "archive_dir": archive_dir,
            "misc_dir": misc_dir,
            **base_extensions,
            "misc_file_delete_rules": {},
            **overrides,
        }
        return JavVideoOrganizeConfig.model_validate(config)

    return _create


@pytest.fixture
def analyze_config_factory(
    base_extensions: dict[str, list[str]],
) -> Callable[..., AnalyzeConfig]:
    def _create(
        sorted_dir: Path | None = None,
        unsorted_dir: Path | None = None,
        archive_dir: Path | None = None,
        misc_dir: Path | None = None,
        misc_file_delete_rules: dict[str, Any] | None = None,
    ) -> AnalyzeConfig:
        ext_sets = {k: set(v) for k, v in base_extensions.items()}
        return AnalyzeConfig(
            **ext_sets,
            sorted_dir=sorted_dir,
            unsorted_dir=unsorted_dir,
            archive_dir=archive_dir,
            misc_dir=misc_dir,
            misc_file_delete_rules=misc_file_delete_rules or {},
        )

    return _create
