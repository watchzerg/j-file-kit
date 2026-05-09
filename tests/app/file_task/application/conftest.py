"""file_task application 层测试 fixtures

适合放置：临时 YAML 配置文件路径、具体任务配置对象构造器。
Pipeline 集成测试需真实 SQLite 和 FileResultRepository。
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from j_file_kit.app.file_task.application.config_common import InboxDeleteRules
from j_file_kit.app.file_task.application.jav_analyze_config import JavAnalyzeConfig
from j_file_kit.app.file_task.application.jav_pipeline.pipeline import FilePipeline
from j_file_kit.app.file_task.application.jav_task_config import JavVideoOrganizeConfig
from j_file_kit.app.file_task.application.raw_analyze_config import RawAnalyzeConfig
from j_file_kit.app.file_task.application.raw_task_config import RawFileOrganizeConfig
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
def raw_file_organize_config_factory() -> Callable[..., RawFileOrganizeConfig]:
    """构造 `RawFileOrganizeConfig`，用于 raw 校验单测。"""

    def _create(
        inbox_dir: Path | None = None,
        **overrides: object,
    ) -> RawFileOrganizeConfig:
        config: dict[str, object] = {
            "inbox_dir": inbox_dir,
            "folders_to_delete": None,
            "folders_video": None,
            "folders_compressed": None,
            "folders_pic": None,
            "folders_audio": None,
            "folders_misc": None,
            "files_to_delete": None,
            "files_video_jav": None,
            "files_video_us": None,
            "files_video_jav_vr": None,
            "files_video_us_vr": None,
            "files_video_movie": None,
            "files_video_misc": None,
            "files_compressed": None,
            "files_pic": None,
            "files_audio": None,
            "files_misc": None,
        }
        config.update(overrides)
        return RawFileOrganizeConfig.model_validate(config)

    return _create


@pytest.fixture
def analyze_config_factory(
    base_extensions: dict[str, list[str]],
) -> Callable[..., JavAnalyzeConfig]:
    """构造 `JavAnalyzeConfig`，用于 analyzer/pipeline 单测（不经 `JavVideoOrganizer`）。

    生产路径下扩展名与 misc.extensions、站标去噪由 `organizer_defaults` 注入；此处手写字段仅为隔离测试。
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


class _UseDefaultFileBuckets:
    """Sentinel for raw test factory: use default ``files_*`` next to ``folders_*``."""


USE_DEFAULT_FILE_BUCKETS = _UseDefaultFileBuckets()


def _resolve_optional_files_bucket(
    param: Path | None | _UseDefaultFileBuckets,
    *,
    with_classification_destinations: bool,
    tmp_path: Path,
    default_name: str,
) -> Path | None:
    """Resolve ``files_*`` path for raw test configs (explicit path vs default vs unset)."""
    if isinstance(param, _UseDefaultFileBuckets):
        if with_classification_destinations:
            return tmp_path / default_name
        return None
    return param


@pytest.fixture
def raw_analyze_config_factory() -> Callable[..., RawAnalyzeConfig]:
    """构造 `RawAnalyzeConfig`，用于 raw pipeline 单测。"""

    def _create(
        tmp_path: Path,
        *,
        files_misc: Path | None,
        folders_to_delete: Path | None = None,
        with_classification_destinations: bool = True,
        files_compressed: Path
        | None
        | _UseDefaultFileBuckets = USE_DEFAULT_FILE_BUCKETS,
        files_pic: Path | None | _UseDefaultFileBuckets = USE_DEFAULT_FILE_BUCKETS,
        files_audio: Path | None | _UseDefaultFileBuckets = USE_DEFAULT_FILE_BUCKETS,
        files_to_delete: Path
        | None
        | _UseDefaultFileBuckets = USE_DEFAULT_FILE_BUCKETS,
        files_video_movie: Path
        | None
        | _UseDefaultFileBuckets = USE_DEFAULT_FILE_BUCKETS,
        files_video_us_vr: Path
        | None
        | _UseDefaultFileBuckets = USE_DEFAULT_FILE_BUCKETS,
        files_video_us: Path | None | _UseDefaultFileBuckets = USE_DEFAULT_FILE_BUCKETS,
        files_video_jav_vr: Path
        | None
        | _UseDefaultFileBuckets = USE_DEFAULT_FILE_BUCKETS,
        files_video_jav: Path
        | None
        | _UseDefaultFileBuckets = USE_DEFAULT_FILE_BUCKETS,
        files_video_misc: Path
        | None
        | _UseDefaultFileBuckets = USE_DEFAULT_FILE_BUCKETS,
    ) -> RawAnalyzeConfig:
        folders_pic = folders_audio = folders_compressed = None
        folders_video = folders_misc = None
        if with_classification_destinations:
            folders_pic = tmp_path / "folders_pic"
            folders_audio = tmp_path / "folders_audio"
            folders_compressed = tmp_path / "folders_compressed"
            folders_video = tmp_path / "folders_video"
            folders_misc = tmp_path / "folders_misc"
            for path in (
                folders_pic,
                folders_audio,
                folders_compressed,
                folders_video,
                folders_misc,
            ):
                path.mkdir(parents=True, exist_ok=True)
        files_compressed_resolved = _resolve_optional_files_bucket(
            files_compressed,
            with_classification_destinations=with_classification_destinations,
            tmp_path=tmp_path,
            default_name="files_compressed",
        )
        files_pic_resolved = _resolve_optional_files_bucket(
            files_pic,
            with_classification_destinations=with_classification_destinations,
            tmp_path=tmp_path,
            default_name="files_pic",
        )
        files_audio_resolved = _resolve_optional_files_bucket(
            files_audio,
            with_classification_destinations=with_classification_destinations,
            tmp_path=tmp_path,
            default_name="files_audio",
        )
        files_to_delete_resolved = _resolve_optional_files_bucket(
            files_to_delete,
            with_classification_destinations=with_classification_destinations,
            tmp_path=tmp_path,
            default_name="files_to_delete",
        )
        files_video_movie_resolved = _resolve_optional_files_bucket(
            files_video_movie,
            with_classification_destinations=with_classification_destinations,
            tmp_path=tmp_path,
            default_name="files_video_movie",
        )
        files_video_us_vr_resolved = _resolve_optional_files_bucket(
            files_video_us_vr,
            with_classification_destinations=with_classification_destinations,
            tmp_path=tmp_path,
            default_name="files_video_us_vr",
        )
        files_video_us_resolved = _resolve_optional_files_bucket(
            files_video_us,
            with_classification_destinations=with_classification_destinations,
            tmp_path=tmp_path,
            default_name="files_video_us",
        )
        files_video_jav_vr_resolved = _resolve_optional_files_bucket(
            files_video_jav_vr,
            with_classification_destinations=with_classification_destinations,
            tmp_path=tmp_path,
            default_name="files_video_jav_vr",
        )
        files_video_jav_resolved = _resolve_optional_files_bucket(
            files_video_jav,
            with_classification_destinations=with_classification_destinations,
            tmp_path=tmp_path,
            default_name="files_video_jav",
        )
        files_video_misc_resolved = _resolve_optional_files_bucket(
            files_video_misc,
            with_classification_destinations=with_classification_destinations,
            tmp_path=tmp_path,
            default_name="files_video_misc",
        )

        for path in (
            files_compressed_resolved,
            files_pic_resolved,
            files_audio_resolved,
            files_to_delete_resolved,
            files_video_movie_resolved,
            files_video_us_vr_resolved,
            files_video_us_resolved,
            files_video_jav_vr_resolved,
            files_video_jav_resolved,
            files_video_misc_resolved,
        ):
            if path is not None:
                path.mkdir(parents=True, exist_ok=True)
        return RawAnalyzeConfig(
            folders_to_delete=folders_to_delete,
            folders_video=folders_video,
            folders_compressed=folders_compressed,
            folders_pic=folders_pic,
            folders_audio=folders_audio,
            folders_misc=folders_misc,
            files_to_delete=files_to_delete_resolved,
            files_video_jav=files_video_jav_resolved,
            files_video_us=files_video_us_resolved,
            files_video_jav_vr=files_video_jav_vr_resolved,
            files_video_us_vr=files_video_us_vr_resolved,
            files_video_movie=files_video_movie_resolved,
            files_video_misc=files_video_misc_resolved,
            files_compressed=files_compressed_resolved,
            files_pic=files_pic_resolved,
            files_audio=files_audio_resolved,
            files_misc=files_misc,
            video_extensions={".mp4"},
            image_extensions={".jpg", ".jpeg", ".png"},
            subtitle_extensions={".srt"},
            archive_extensions={".zip"},
            audio_extensions={".mp3"},
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
