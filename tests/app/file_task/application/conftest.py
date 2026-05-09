"""file_task application 层测试 fixtures

适合放置：临时 YAML 配置文件路径、具体任务配置对象构造器。
Pipeline 集成测试需真实 SQLite 和 FileResultRepository。
"""

from collections.abc import Callable
from dataclasses import fields
from pathlib import Path
from typing import Any

import pytest

from j_file_kit.app.file_task.application.config_common import (
    InboxDeleteRules,
    RawWorkspacePaths,
    raw_workspace_paths,
)
from j_file_kit.app.file_task.application.jav_analyze_config import JavAnalyzeConfig
from j_file_kit.app.file_task.application.jav_pipeline.pipeline import FilePipeline
from j_file_kit.app.file_task.application.jav_task_config import JavVideoOrganizeConfig
from j_file_kit.app.file_task.application.raw_analyze_config import RawAnalyzeConfig
from j_file_kit.app.file_task.application.raw_pipeline.pipeline import RawFilePipeline
from j_file_kit.app.file_task.application.raw_task_config import RawFileOrganizeConfig
from j_file_kit.app.file_task.domain.organizer_defaults import (
    DEFAULT_ARCHIVE_EXTENSIONS,
    DEFAULT_IMAGE_EXTENSIONS,
    DEFAULT_MUSIC_EXTENSIONS,
    DEFAULT_SUBTITLE_EXTENSIONS,
    DEFAULT_VIDEO_EXTENSIONS,
)
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
        workspace_root: Path | None = None,
        **overrides: object,
    ) -> JavVideoOrganizeConfig:
        config: dict[str, object] = {
            "workspace_root": workspace_root or Path("/media/jav_workspace"),
            "misc_file_delete_rules": {},
        }
        config.update(overrides)
        return JavVideoOrganizeConfig.model_validate(config)

    return _create


@pytest.fixture
def raw_file_organize_config_factory() -> Callable[..., RawFileOrganizeConfig]:
    """构造 `RawFileOrganizeConfig`，用于 raw 校验单测。"""

    def _create(
        workspace_root: Path | None = None,
        **overrides: object,
    ) -> RawFileOrganizeConfig:
        config: dict[str, object] = {
            "workspace_root": workspace_root or Path("/media/raw_workspace"),
        }
        config.update(overrides)
        return RawFileOrganizeConfig.model_validate(config)

    return _create


@pytest.fixture
def analyze_config_factory(
    tmp_path: Path,
    base_extensions: dict[str, list[str]],
) -> Callable[..., JavAnalyzeConfig]:
    """构造 `JavAnalyzeConfig`，用于 analyzer/pipeline 单测（不经 `JavVideoOrganizer`）。

    未显式传入的归宿目录默认为 ``tmp_path`` 下同名子目录。
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
            sorted_dir=sorted_dir or tmp_path / "sorted",
            unsorted_dir=unsorted_dir or tmp_path / "unsorted",
            archive_dir=archive_dir or tmp_path / "archive",
            misc_dir=misc_dir or tmp_path / "misc",
            misc_file_delete_rules=misc_file_delete_rules or {},
            video_small_delete_bytes=video_small_delete_bytes,
            inbox_delete_rules=inbox_delete_rules or InboxDeleteRules(),
            jav_filename_strip_substrings=(),
        )

    return _create


@pytest.fixture
def raw_analyze_config_factory() -> Callable[..., RawAnalyzeConfig]:
    """构造 `RawAnalyzeConfig`：路径默认按 ``raw_workspace_paths(tmp_path)``。"""

    def _create(
        tmp_path: Path,
        *,
        files_misc: Path | None = None,
        **path_overrides: Path,
    ) -> RawAnalyzeConfig:
        p = raw_workspace_paths(tmp_path)
        paths_map: dict[str, Path] = {
            "folders_to_delete": p.folders_to_delete,
            "folders_video": p.folders_video,
            "folders_compressed": p.folders_compressed,
            "folders_pic": p.folders_pic,
            "folders_audio": p.folders_audio,
            "folders_misc": p.folders_misc,
            "files_to_delete": p.files_to_delete,
            "files_video_jav": p.files_video_jav,
            "files_video_us": p.files_video_us,
            "files_video_jav_vr": p.files_video_jav_vr,
            "files_video_us_vr": p.files_video_us_vr,
            "files_video_movie": p.files_video_movie,
            "files_video_misc": p.files_video_misc,
            "files_compressed": p.files_compressed,
            "files_pic": p.files_pic,
            "files_audio": p.files_audio,
            "files_misc": files_misc if files_misc is not None else p.files_misc,
        }
        paths_map.update(path_overrides)
        for dest in paths_map.values():
            dest.mkdir(parents=True, exist_ok=True)

        return RawAnalyzeConfig(
            folders_to_delete=paths_map["folders_to_delete"],
            folders_video=paths_map["folders_video"],
            folders_compressed=paths_map["folders_compressed"],
            folders_pic=paths_map["folders_pic"],
            folders_audio=paths_map["folders_audio"],
            folders_misc=paths_map["folders_misc"],
            files_to_delete=paths_map["files_to_delete"],
            files_video_jav=paths_map["files_video_jav"],
            files_video_us=paths_map["files_video_us"],
            files_video_jav_vr=paths_map["files_video_jav_vr"],
            files_video_us_vr=paths_map["files_video_us_vr"],
            files_video_movie=paths_map["files_video_movie"],
            files_video_misc=paths_map["files_video_misc"],
            files_compressed=paths_map["files_compressed"],
            files_pic=paths_map["files_pic"],
            files_audio=paths_map["files_audio"],
            files_misc=paths_map["files_misc"],
            video_extensions={".mp4"},
            image_extensions={".jpg", ".jpeg", ".png"},
            subtitle_extensions={".srt"},
            archive_extensions={".zip"},
            audio_extensions={".mp3"},
        )

    return _create


def ensure_raw_workspace_directories(workspace_root: Path) -> RawWorkspacePaths:
    """创建与生产一致的 Raw workspace 一级目录树（见 ``raw_workspace_paths``）。"""
    paths = raw_workspace_paths(workspace_root)
    for field in fields(paths):
        getattr(paths, field.name).mkdir(parents=True, exist_ok=True)
    return paths


def raw_analyze_config_matching_organizer(paths: RawWorkspacePaths) -> RawAnalyzeConfig:
    """与 ``RawFileOrganizer._create_analyze_config`` 对齐，供 Raw 集成测试使用。"""
    return RawAnalyzeConfig(
        folders_to_delete=paths.folders_to_delete,
        folders_video=paths.folders_video,
        folders_compressed=paths.folders_compressed,
        folders_pic=paths.folders_pic,
        folders_audio=paths.folders_audio,
        folders_misc=paths.folders_misc,
        files_to_delete=paths.files_to_delete,
        files_video_jav=paths.files_video_jav,
        files_video_us=paths.files_video_us,
        files_video_jav_vr=paths.files_video_jav_vr,
        files_video_us_vr=paths.files_video_us_vr,
        files_video_movie=paths.files_video_movie,
        files_video_misc=paths.files_video_misc,
        files_compressed=paths.files_compressed,
        files_pic=paths.files_pic,
        files_audio=paths.files_audio,
        files_misc=paths.files_misc,
        video_extensions=set(DEFAULT_VIDEO_EXTENSIONS),
        image_extensions=set(DEFAULT_IMAGE_EXTENSIONS),
        subtitle_extensions=set(DEFAULT_SUBTITLE_EXTENSIONS),
        archive_extensions=set(DEFAULT_ARCHIVE_EXTENSIONS),
        audio_extensions=set(DEFAULT_MUSIC_EXTENSIONS),
    )


@pytest.fixture
def raw_integration_paths(tmp_path: Path) -> RawWorkspacePaths:
    """Raw 集成测试：``tmp_path/raw_workspace`` 下完整一级目录布局。"""
    return ensure_raw_workspace_directories(tmp_path / "raw_workspace")


@pytest.fixture
def raw_pipeline_with_real_repo(
    tmp_path: Path,
    raw_integration_paths: RawWorkspacePaths,
    file_result_repository: FileResultRepositoryImpl,
) -> RawFilePipeline:
    """Raw 集成测试：``RawFilePipeline`` + 真实 ``FileResultRepository`` + 生产对齐目录。"""
    config = raw_analyze_config_matching_organizer(raw_integration_paths)
    return RawFilePipeline(
        run_id=1,
        run_name="raw_file_organizer",
        scan_root=raw_integration_paths.inbox,
        analyze_config=config,
        log_dir=tmp_path / "logs",
        file_result_repository=file_result_repository,
    )


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
