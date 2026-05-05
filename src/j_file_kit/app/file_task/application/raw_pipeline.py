"""Raw 收件箱整理管道。

设计意图：与 `FilePipeline` 解耦，采用 inbox **第一层** 文件与目录的三阶段编排：
阶段 1 将散落文件收入 `files_misc`；阶段 2 / 3 本期占位，为后续目录分析与分流预留钩子。
"""

import threading
import time
from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from j_file_kit.app.file_task.application.config import RawAnalyzeConfig
from j_file_kit.app.file_task.application.executor import (
    ExecutionResult,
    ExecutionStatus,
    execute_decision,
)
from j_file_kit.app.file_task.application.file_ops import normalize_move_basename
from j_file_kit.app.file_task.domain.decisions import FileItemData, MoveDecision
from j_file_kit.app.file_task.domain.models import FileTaskRunStatistics, FileType
from j_file_kit.app.file_task.domain.ports import FileResultRepository
from j_file_kit.shared.utils.file_utils import sanitize_surrogate_str
from j_file_kit.shared.utils.logging import configure_task_logger, remove_task_logger


@dataclass
class _RawPhaseCounters:
    """单次 run 内阶段计数（并入返回统计；不落目录明细表）。"""

    phase1_seen_files: int = 0
    phase1_moved_files: int = 0
    phase1_error_files: int = 0
    phase2_seen_dirs: int = 0
    phase2_deferred_dirs: int = 0
    phase3_seen_files_misc: int = 0
    phase3_deferred_files_misc: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "phase1_seen_files": self.phase1_seen_files,
            "phase1_moved_files": self.phase1_moved_files,
            "phase1_error_files": self.phase1_error_files,
            "phase2_seen_dirs": self.phase2_seen_dirs,
            "phase2_deferred_dirs": self.phase2_deferred_dirs,
            "phase3_seen_files_misc": self.phase3_seen_files_misc,
            "phase3_deferred_files_misc": self.phase3_deferred_files_misc,
        }


class RawFilePipeline:
    """Raw 任务专用管道：只遍历 `scan_root` 第一层条目并按阶段编排。"""

    def __init__(
        self,
        run_id: int,
        run_name: str,
        scan_root: Path,
        analyze_config: RawAnalyzeConfig,
        log_dir: Path,
        file_result_repository: FileResultRepository,
    ) -> None:
        """绑定一次 run 的标识与依赖；参数形状与 `FilePipeline` 对齐。"""
        self.run_id = run_id
        self.run_name = run_name
        self.scan_root = scan_root
        self.analyze_config = analyze_config
        self.log_dir = log_dir
        self._file_result_repository = file_result_repository
        self._log_handler_id: int | None = None

    def list_inbox_level1_files(self) -> list[Path]:
        """返回 `scan_root` 下第一层普通文件（确定性排序）。"""
        if not self.scan_root.exists():
            raise FileNotFoundError(f"扫描目录不存在: {self.scan_root}")
        if not self.scan_root.is_dir():
            raise NotADirectoryError(f"路径不是目录: {self.scan_root}")
        return sorted(p for p in self.scan_root.iterdir() if p.is_file())

    def list_inbox_level1_dirs(self) -> list[Path]:
        """返回 `scan_root` 下第一层子目录（确定性排序）。"""
        if not self.scan_root.exists():
            raise FileNotFoundError(f"扫描目录不存在: {self.scan_root}")
        if not self.scan_root.is_dir():
            raise NotADirectoryError(f"路径不是目录: {self.scan_root}")
        return sorted(p for p in self.scan_root.iterdir() if p.is_dir())

    def run(
        self,
        dry_run: bool = False,
        cancellation_event: threading.Event | None = None,
    ) -> FileTaskRunStatistics:
        """执行三阶段编排；阶段 2/3 本期仅占位，阶段 1 将第一层文件移入 `files_misc`。"""
        phases = _RawPhaseCounters()
        try:
            self._start_task(dry_run)

            cancelled = self._phase1_level1_files_to_misc(
                phases,
                dry_run=dry_run,
                cancellation_event=cancellation_event,
            )
            if cancelled:
                return self._finish_task(dry_run, phases)

            cancelled = self._phase2_level1_dirs_placeholder(
                phases,
                cancellation_event=cancellation_event,
            )
            if cancelled:
                return self._finish_task(dry_run, phases)

            self._phase3_files_misc_placeholder(phases)

            return self._finish_task(dry_run, phases)

        except Exception as e:
            logger.bind(
                run_id=str(self.run_id),
                run_name=self.run_name,
            ).error(f"Raw 管道执行失败: {e!s}")
            raise
        finally:
            if self._log_handler_id is not None:
                remove_task_logger(self._log_handler_id)

    def _start_task(self, dry_run: bool) -> None:
        """注册按 run 隔离的 loguru sink，并写 TASK_START。"""
        self._log_handler_id = configure_task_logger(
            self.log_dir,
            self.run_name,
            self.run_id,
        )

        scan_root_str = str(self.scan_root) if self.scan_root else "未设置"
        logger.bind(
            run_id=str(self.run_id),
            run_name=self.run_name,
            scan_root=scan_root_str,
            level="TASK_START",
        ).info(f"开始任务: {self.run_name}")

        if dry_run:
            logger.bind(
                run_id=str(self.run_id),
                run_name=self.run_name,
            ).info("运行在预览模式（dry_run）")

    def _finish_task(
        self,
        dry_run: bool,
        phases: _RawPhaseCounters,
    ) -> FileTaskRunStatistics:
        """合并仓储聚合与阶段计数，写 TASK_END。"""
        repo_stats = self._file_result_repository.get_statistics(self.run_id)
        merged = {**repo_stats, **phases.as_dict()}

        logger.bind(
            run_id=str(self.run_id),
            run_name=self.run_name,
            level="TASK_END",
            total_items=merged.get("total_items", 0),
            success_items=merged.get("success_items", 0),
            error_items=merged.get("error_items", 0),
            skipped_items=merged.get("skipped_items", 0),
            **phases.as_dict(),
        ).info(f"任务完成: {self.run_name}")

        if dry_run:
            logger.bind(
                run_id=str(self.run_id),
                run_name=self.run_name,
            ).info("预览模式执行完成")

        return FileTaskRunStatistics.model_validate(merged)

    def _phase1_level1_files_to_misc(
        self,
        phases: _RawPhaseCounters,
        *,
        dry_run: bool,
        cancellation_event: threading.Event | None,
    ) -> bool:
        """阶段 1：收件箱第一层文件 -> `files_misc`。"""
        dest = self.analyze_config.files_misc
        level1_files = self.list_inbox_level1_files()
        phases.phase1_seen_files = len(level1_files)

        if dest is None:
            if level1_files:
                raise ValueError("files_misc 未设置")
            return False

        logger.bind(
            run_id=str(self.run_id),
            run_name=self.run_name,
            level="RAW_PHASE",
            phase=1,
        ).info(f"阶段1：处理 inbox 第一层文件 {len(level1_files)} 个")

        for path in level1_files:
            if cancellation_event and cancellation_event.is_set():
                logger.bind(
                    run_id=str(self.run_id),
                    run_name=self.run_name,
                ).info("任务已被取消（阶段1）")
                return True

            start_time = time.time()
            try:
                basename = normalize_move_basename(sanitize_surrogate_str(path.name))
                target = dest / basename
                decision = MoveDecision(
                    source_path=path,
                    target_path=target,
                    file_type=FileType.MISC,
                    serial_id=None,
                )
                result = execute_decision(decision, dry_run=dry_run)
                duration_ms = (time.time() - start_time) * 1000

                item = self._item_data_from_move(path, decision, result, duration_ms)
                self._file_result_repository.save_result(self.run_id, item)

                if result.status in (
                    ExecutionStatus.SUCCESS,
                    ExecutionStatus.PREVIEW,
                ):
                    phases.phase1_moved_files += 1
                elif result.status == ExecutionStatus.ERROR:
                    phases.phase1_error_files += 1

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                safe_path = sanitize_surrogate_str(str(path))
                logger.bind(
                    run_id=str(self.run_id),
                    run_name=self.run_name,
                    error=str(e),
                ).error(f"阶段1 处理文件失败: {safe_path}")
                error_data = FileItemData(
                    path=path,
                    stem=path.stem,
                    file_type=FileType.MISC,
                    serial_id=None,
                    decision_type="error",
                    target_path=None,
                    success=False,
                    error_message=str(e),
                    duration_ms=duration_ms,
                )
                self._file_result_repository.save_result(self.run_id, error_data)
                phases.phase1_error_files += 1

        return False

    def _phase2_level1_dirs_placeholder(
        self,
        phases: _RawPhaseCounters,
        *,
        cancellation_event: threading.Event | None,
    ) -> bool:
        """阶段 2 占位：仅枚举第一层目录并计数（目录内规则后续迭代）。"""
        if cancellation_event and cancellation_event.is_set():
            logger.bind(
                run_id=str(self.run_id),
                run_name=self.run_name,
            ).info("任务已被取消（阶段2 前）")
            return True

        dirs = self.list_inbox_level1_dirs()
        phases.phase2_seen_dirs = len(dirs)
        phases.phase2_deferred_dirs = len(dirs)

        logger.bind(
            run_id=str(self.run_id),
            run_name=self.run_name,
            level="RAW_PHASE",
            phase=2,
        ).info(
            f"阶段2（占位）：第一层目录 {len(dirs)} 个，暂未执行目录级整理",
        )
        return False

    def _phase3_files_misc_placeholder(self, phases: _RawPhaseCounters) -> None:
        """阶段 3 占位：统计 `files_misc` 第一层文件，分流规则后续迭代。"""
        misc = self.analyze_config.files_misc
        if misc is None or not misc.exists() or not misc.is_dir():
            phases.phase3_seen_files_misc = 0
            phases.phase3_deferred_files_misc = 0
            logger.bind(
                run_id=str(self.run_id),
                run_name=self.run_name,
                level="RAW_PHASE",
                phase=3,
            ).info("阶段3（占位）：files_misc 不可用或不存在，跳过计数")
            return

        seen = sum(1 for p in misc.iterdir() if p.is_file())
        phases.phase3_seen_files_misc = seen
        phases.phase3_deferred_files_misc = seen

        logger.bind(
            run_id=str(self.run_id),
            run_name=self.run_name,
            level="RAW_PHASE",
            phase=3,
        ).info(
            f"阶段3（占位）：files_misc 第一层文件 {seen} 个，暂未分流到 files_*",
        )

    def _item_data_from_move(
        self,
        path: Path,
        decision: MoveDecision,
        result: ExecutionResult,
        duration_ms: float,
    ) -> FileItemData:
        """折叠 Move + ExecutionResult 为入库模型。"""
        success = result.status in (
            ExecutionStatus.SUCCESS,
            ExecutionStatus.PREVIEW,
        )
        err_msg = result.message if result.status == ExecutionStatus.ERROR else None
        return FileItemData(
            path=path,
            stem=path.stem,
            file_type=decision.file_type,
            serial_id=decision.serial_id,
            decision_type="move",
            target_path=result.target_path,
            success=success,
            error_message=err_msg,
            duration_ms=duration_ms,
        )
