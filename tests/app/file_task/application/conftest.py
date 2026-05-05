"""file_task application 层测试 fixtures

适合放置：临时 YAML 配置文件路径、具体任务配置对象构造器。
Pipeline 集成测试需真实 SQLite 和 FileResultRepository。
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from j_file_kit.app.file_task.application.config import (
    InboxDeleteRules,
    JavAnalyzeConfig,
    JavVideoOrganizeConfig,
)
from j_file_kit.app.file_task.application.pipeline import FilePipeline
from j_file_kit.infrastructure.persistence.sqlite.connection import (
    SQLiteConnectionManager,
)
from j_file_kit.infrastructure.persistence.sqlite.file_task.file_result_repository import (
    FileResultRepositoryImpl,
)
from j_file_kit.infrastructure.persistence.sqlite.schema import SQLiteSchemaInitializer


@pytest.fixture
def base_extensions() -> dict[str, list[str]]:
    return {
        "video_extensions": [".mp4", ".mkv"],
        "image_extensions": [".jpg", ".png"],
        "subtitle_extensions": [".srt", ".ass"],
        "archive_extensions": [".zip"],
    }


@pytest.fixture
def jav_video_organize_config_factory() -> Callable[..., JavVideoOrganizeConfig]:
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
            "misc_file_delete_rules": {},
            **overrides,
        }
        return JavVideoOrganizeConfig.model_validate(config)

    return _create


@pytest.fixture
def analyze_config_factory(
    base_extensions: dict[str, list[str]],
) -> Callable[..., JavAnalyzeConfig]:
    """构造 `JavAnalyzeConfig`，用于 analyzer/pipeline 单测（不经 `JavVideoOrganizer`）。

    生产路径下扩展名与 misc.extensions、站标去噪由 `jav_organizer_defaults` 注入；此处手写字段仅为隔离测试。
    """

    def _create(
        sorted_dir: Path | None = None,
        unsorted_dir: Path | None = None,
        archive_dir: Path | None = None,
        misc_dir: Path | None = None,
        misc_file_delete_rules: dict[str, Any] | None = None,
        inbox_delete_rules: InboxDeleteRules | None = None,
        video_small_delete_bytes: int | None = None,
    ) -> JavAnalyzeConfig:
        ext_sets = {k: set(v) for k, v in base_extensions.items()}
        return JavAnalyzeConfig(
            video_extensions=ext_sets["video_extensions"],
            image_extensions=ext_sets["image_extensions"],
            subtitle_extensions=ext_sets["subtitle_extensions"],
            archive_extensions=ext_sets["archive_extensions"],
            sorted_dir=sorted_dir,
            unsorted_dir=unsorted_dir,
            archive_dir=archive_dir,
            misc_dir=misc_dir,
            misc_file_delete_rules=misc_file_delete_rules or {},
            video_small_delete_bytes=video_small_delete_bytes,
            inbox_delete_rules=inbox_delete_rules or InboxDeleteRules(),
            jav_filename_strip_substrings=(),
        )

    return _create


@pytest.fixture
def sqlite_connection_manager() -> SQLiteConnectionManager:
    """Pipeline 集成测试用：内存 SQLite 连接"""
    manager = SQLiteConnectionManager(Path(":memory:"))
    SQLiteSchemaInitializer(manager).initialize()
    return manager


@pytest.fixture
def file_result_repository(sqlite_connection_manager: SQLiteConnectionManager):
    """Pipeline 集成测试用：真实 FileResultRepository"""
    return FileResultRepositoryImpl(sqlite_connection_manager)


@pytest.fixture
def pipeline_with_real_repo(
    tmp_path: Path,
    analyze_config_factory: Callable[..., JavAnalyzeConfig],
    file_result_repository: FileResultRepositoryImpl,
) -> FilePipeline:
    """Pipeline 集成测试用：带真实仓储的 FilePipeline"""
    config = analyze_config_factory(
        sorted_dir=tmp_path / "sorted",
        unsorted_dir=tmp_path / "unsorted",
        archive_dir=tmp_path / "archive",
        misc_dir=tmp_path / "misc",
        misc_file_delete_rules={
            "keywords": ["rarbg", "sample"],
            "extensions": [".tmp", ".temp"],
            "max_size": 1048576,
        },
    )
    return FilePipeline(
        run_id=1,
        run_name="test",
        scan_root=tmp_path / "inbox",
        analyze_config=config,
        log_dir=tmp_path / "logs",
        file_result_repository=file_result_repository,
    )


@pytest.fixture
def pipeline_with_inbox_delete_repo(
    tmp_path: Path,
    analyze_config_factory: Callable[..., JavAnalyzeConfig],
    file_result_repository: FileResultRepositoryImpl,
) -> FilePipeline:
    """Pipeline 集成测试：收件箱预删除规则（stem 完全匹配）"""
    config = analyze_config_factory(
        sorted_dir=tmp_path / "sorted",
        unsorted_dir=tmp_path / "unsorted",
        archive_dir=tmp_path / "archive",
        misc_dir=tmp_path / "misc",
        misc_file_delete_rules={
            "keywords": ["rarbg", "sample"],
            "extensions": [".tmp", ".temp"],
            "max_size": 1048576,
        },
        inbox_delete_rules=InboxDeleteRules(exact_stems={"junk"}),
    )
    return FilePipeline(
        run_id=1,
        run_name="test",
        scan_root=tmp_path / "inbox",
        analyze_config=config,
        log_dir=tmp_path / "logs",
        file_result_repository=file_result_repository,
    )
