"""Raw 收件箱整理管道（骨架）。

设计意图：与 `FilePipeline` 解耦，便于后续实现「仅收件箱第一层」的遍历与整目录移动；
本期 `run` 不扫描、不分析、不落库，直接返回空 `FileTaskRunStatistics`，仅占位构造函数契约。
"""

import threading
from pathlib import Path

from j_file_kit.app.file_task.application.config import RawAnalyzeConfig
from j_file_kit.app.file_task.domain.models import FileTaskRunStatistics
from j_file_kit.app.file_task.domain.ports import FileResultRepository


class RawFilePipeline:
    """Raw 任务管道占位实现（后续替换为实际 walk / 决策 / 执行）。"""

    def __init__(
        self,
        run_id: int,
        run_name: str,
        scan_root: Path,
        analyze_config: RawAnalyzeConfig,
        log_dir: Path,
        file_result_repository: FileResultRepository,
    ) -> None:
        """绑定一次 run 的标识与依赖；参数与 `FilePipeline` 对齐，便于后续迁移逻辑."""
        self.run_id = run_id
        self.run_name = run_name
        self.scan_root = scan_root
        self.analyze_config = analyze_config
        self.log_dir = log_dir
        self._file_result_repository = file_result_repository

    def run(
        self,
        dry_run: bool = False,
        cancellation_event: threading.Event | None = None,
    ) -> FileTaskRunStatistics:
        """本期返回空统计；`dry_run` 与取消事件留待后续管道实现使用。"""
        _ = (dry_run, cancellation_event, self._file_result_repository)
        return FileTaskRunStatistics()
