"""Raw 收件箱整理任务入口（`FileTaskRunner` 实现）。

与 `JavVideoOrganizer` 对称：`TaskConfig` → `RawFileOrganizeConfig` → `RawAnalyzeConfig` → `RawFilePipeline`。
`RawFilePipeline`：阶段 1 将散落文件移入 `files_misc` 并落库；阶段 2 处理第一层目录（编排见
`raw_pipeline/phase2.py`，规则见同包 `phase2_*`：关键字迁至 `folders_to_delete` / 清洗 / 单链折叠 / 分类）；
阶段 3：`files_misc` 第一层 3.0 junk→`files_to_delete`，再分流至 `files_compressed` / `files_pic` / `files_audio`，视频按关键字至各 `files_video_*`（否则 `files_video_misc`）。
独立的 `analyze_raw_*` 纯函数与目录内深度规则由后续迭代填充。
"""

import threading
from pathlib import Path

from j_file_kit.app.file_task.application.config_common import raw_workspace_paths
from j_file_kit.app.file_task.application.raw_analyze_config import RawAnalyzeConfig
from j_file_kit.app.file_task.application.raw_pipeline.pipeline import RawFilePipeline
from j_file_kit.app.file_task.application.raw_task_config import RawFileOrganizeConfig
from j_file_kit.app.file_task.domain.constants import TASK_TYPE_RAW_FILE_ORGANIZER
from j_file_kit.app.file_task.domain.organizer_defaults import (
    DEFAULT_ARCHIVE_EXTENSIONS,
    DEFAULT_IMAGE_EXTENSIONS,
    DEFAULT_MUSIC_EXTENSIONS,
    DEFAULT_SUBTITLE_EXTENSIONS,
    DEFAULT_VIDEO_EXTENSIONS,
)
from j_file_kit.app.file_task.domain.ports import FileResultRepository
from j_file_kit.app.file_task.domain.task_config import TaskConfig
from j_file_kit.app.file_task.domain.task_run import FileTaskRunStatistics


class RawFileOrganizer:
    """Raw 收件箱整理用例（`FileTaskRunner`）。"""

    def __init__(
        self,
        task_config: TaskConfig,
        log_dir: Path,
        file_result_repository: FileResultRepository,
    ) -> None:
        self._task_config = task_config
        self.log_dir = log_dir
        self._file_result_repository = file_result_repository

        self.file_config: RawFileOrganizeConfig = self._task_config.get_config(
            RawFileOrganizeConfig,
        )

    @property
    def task_type(self) -> str:
        return TASK_TYPE_RAW_FILE_ORGANIZER

    def _create_analyze_config(self) -> RawAnalyzeConfig:
        """从 ``workspace_root`` 派生分析 DTO；扩展名来自 `organizer_defaults`。"""
        p = raw_workspace_paths(self.file_config.workspace_root)
        return RawAnalyzeConfig(
            folders_to_delete=p.folders_to_delete,
            folders_video=p.folders_video,
            folders_compressed=p.folders_compressed,
            folders_pic=p.folders_pic,
            folders_audio=p.folders_audio,
            folders_misc=p.folders_misc,
            files_to_delete=p.files_to_delete,
            files_video_jav=p.files_video_jav,
            files_video_us=p.files_video_us,
            files_video_jav_vr=p.files_video_jav_vr,
            files_video_us_vr=p.files_video_us_vr,
            files_video_movie=p.files_video_movie,
            files_video_misc=p.files_video_misc,
            files_compressed=p.files_compressed,
            files_pic=p.files_pic,
            files_audio=p.files_audio,
            files_misc=p.files_misc,
            video_extensions=set(DEFAULT_VIDEO_EXTENSIONS),
            image_extensions=set(DEFAULT_IMAGE_EXTENSIONS),
            subtitle_extensions=set(DEFAULT_SUBTITLE_EXTENSIONS),
            archive_extensions=set(DEFAULT_ARCHIVE_EXTENSIONS),
            audio_extensions=set(DEFAULT_MUSIC_EXTENSIONS),
        )

    def run(
        self,
        run_id: int,
        dry_run: bool = False,
        cancellation_event: threading.Event | None = None,
    ) -> FileTaskRunStatistics:
        """组装 `RawFilePipeline` 并委托执行（见 `RawFilePipeline.run` 三阶段语义）。"""
        paths = raw_workspace_paths(self.file_config.workspace_root)
        if not paths.inbox.exists() or not paths.inbox.is_dir():
            msg = f"收件箱目录不存在或不是目录: {paths.inbox}"
            raise ValueError(msg)

        analyze_config = self._create_analyze_config()
        pipeline = RawFilePipeline(
            run_id=run_id,
            run_name=self.task_type,
            scan_root=paths.inbox,
            analyze_config=analyze_config,
            log_dir=self.log_dir,
            file_result_repository=self._file_result_repository,
        )
        return pipeline.run(dry_run=dry_run, cancellation_event=cancellation_event)
