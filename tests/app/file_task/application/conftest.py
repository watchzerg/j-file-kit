"""file_task application 层测试 fixtures

适合放置：临时 YAML 配置文件路径、具体任务配置对象构造器。
Pipeline 集成测试需真实 SQLite 和 FileResultRepository。
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from j_file_kit.app.file_task.application.config import (
    AnalyzeConfig,
    InboxDeleteRules,
    JavVideoOrganizeConfig,
    SerialIdRule,
    SerialPatternSpec,
)
from j_file_kit.app.file_task.application.jav_filename_util import build_serial_pattern
from j_file_kit.app.file_task.application.pipeline import FilePipeline
from j_file_kit.infrastructure.persistence.sqlite.connection import (
    SQLiteConnectionManager,
)
from j_file_kit.infrastructure.persistence.sqlite.file_task.file_result_repository import (
    FileResultRepositoryImpl,
)
from j_file_kit.infrastructure.persistence.sqlite.schema import SQLiteSchemaInitializer


def _default_analyze_serial_spec() -> SerialPatternSpec:
    """Pipeline / analyze 单测默认番号规则（与 test_jav_filename_util 常见用例一致）。"""
    return build_serial_pattern(
        [
            SerialIdRule(prefix_letters=3, digits_min=2, digits_max=5),
            SerialIdRule(prefix_letters=4, digits_min=2, digits_max=5),
        ],
    )


@pytest.fixture
def base_extensions() -> dict[str, list[str]]:
    return {
        "video_extensions": [".mp4", ".mkv"],
        "image_extensions": [".jpg", ".png"],
        "subtitle_extensions": [".srt", ".ass"],
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
            "serial_id_rules": [
                {"prefix_letters": 3, "digits_min": 3, "digits_max": 3},
            ],
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
        inbox_delete_rules: InboxDeleteRules | None = None,
        video_small_delete_bytes: int | None = None,
        serial_pattern: SerialPatternSpec | None = None,
    ) -> AnalyzeConfig:
        ext_sets = {k: set(v) for k, v in base_extensions.items()}
        sp = (
            serial_pattern
            if serial_pattern is not None
            else _default_analyze_serial_spec()
        )
        return AnalyzeConfig(
            **ext_sets,
            sorted_dir=sorted_dir,
            unsorted_dir=unsorted_dir,
            archive_dir=archive_dir,
            misc_dir=misc_dir,
            misc_file_delete_rules=misc_file_delete_rules or {},
            video_small_delete_bytes=video_small_delete_bytes,
            inbox_delete_rules=inbox_delete_rules or InboxDeleteRules(),
            serial_pattern=sp,
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
    analyze_config_factory: Callable[..., AnalyzeConfig],
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
    analyze_config_factory: Callable[..., AnalyzeConfig],
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
