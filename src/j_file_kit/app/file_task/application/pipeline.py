"""文件处理管道

协调 scan → analyze → execute 流程，管理任务生命周期。

设计意图：
- 简化的 Pipeline 设计，不使用 ProcessorChain
- 直接调用 analyze_file 和 execute_decision 函数
- 管理任务统计信息和日志
"""

import threading
import time
from datetime import datetime
from pathlib import Path

from loguru import logger

from j_file_kit.app.file_task.application.analyzer import analyze_file
from j_file_kit.app.file_task.application.config import AnalyzeConfig
from j_file_kit.app.file_task.application.executor import (
    ExecutionResult,
    ExecutionStatus,
    execute_decision,
)
from j_file_kit.app.file_task.application.file_ops import scan_directory_items
from j_file_kit.app.file_task.domain.decisions import (
    DeleteDecision,
    FileDecision,
    FileItemData,
    MoveDecision,
    SkipDecision,
)
from j_file_kit.app.file_task.domain.models import PathEntryType
from j_file_kit.app.file_task.domain.ports import (
    FileItemRepository,
    FileProcessorRepository,
)
from j_file_kit.app.task.domain.models import TaskStatus
from j_file_kit.app.task.domain.ports import TaskRepository
from j_file_kit.shared.utils.file_utils import delete_directory_if_empty
from j_file_kit.shared.utils.logging import (
    configure_task_logger,
    remove_task_logger,
)


class FilePipeline:
    """文件处理管道

    设计意图：协调 scan → analyze → execute 流程，管理任务生命周期。

    职责：
    - 协调处理流程（扫描 → 分析 → 执行）
    - 管理任务生命周期（开始 → 处理 → 结束）
    - 统计信息跟踪
    - 日志记录
    """

    def __init__(
        self,
        task_id: int,
        task_name: str,
        scan_root: Path,
        analyze_config: AnalyzeConfig,
        log_dir: Path,
        task_repository: TaskRepository,
        file_processor_repository: FileProcessorRepository,
        file_item_repository: FileItemRepository,
    ) -> None:
        """初始化文件处理管道

        Args:
            task_id: 任务ID
            task_name: 任务名称
            scan_root: 扫描根目录
            analyze_config: 分析配置
            log_dir: 日志目录
            task_repository: 任务仓储
            file_processor_repository: 文件处理操作仓储
            file_item_repository: 文件处理结果仓储
        """
        self.task_id = task_id
        self.task_name = task_name
        self.scan_root = scan_root
        self.analyze_config = analyze_config
        self.log_dir = log_dir
        self.task_repository = task_repository
        self.file_processor_repository = file_processor_repository
        self.file_item_repository = file_item_repository

        # 统计信息
        self.total_items = 0
        self.success_items = 0
        self.error_items = 0
        self.skipped_items = 0
        self.total_duration_ms = 0.0

        # 日志 handler
        self._log_handler_id: int | None = None

    def run(
        self,
        dry_run: bool = False,
        cancellation_event: threading.Event | None = None,
    ) -> None:
        """运行管道

        协调文件处理流程：扫描 → 分析 → 执行。

        Args:
            dry_run: 是否为预览模式
            cancellation_event: 取消事件
        """
        try:
            self._start_task(dry_run)

            for path, item_type in scan_directory_items(self.scan_root):
                # 检查是否被取消
                if cancellation_event and cancellation_event.is_set():
                    logger.bind(
                        task_id=str(self.task_id),
                        task_name=self.task_name,
                    ).info("任务已被取消")
                    break

                if item_type == PathEntryType.FILE:
                    self._process_file(path, dry_run)
                else:
                    # 目录清理（辅助功能）
                    self._cleanup_empty_directory(path, dry_run)

            self._finish_task(dry_run)

        except Exception as e:
            logger.bind(
                task_id=str(self.task_id),
                task_name=self.task_name,
            ).error(f"管道执行失败: {e!s}")
            raise
        finally:
            # 清理任务级别的日志 handler
            if self._log_handler_id is not None:
                remove_task_logger(self._log_handler_id)

    def _start_task(self, dry_run: bool) -> None:
        """任务开始处理"""
        # 配置任务日志
        self._log_handler_id = configure_task_logger(
            self.log_dir,
            self.task_name,
            self.task_id,
        )

        scan_root_str = str(self.scan_root) if self.scan_root else "未设置"
        logger.bind(
            task_id=str(self.task_id),
            task_name=self.task_name,
            scan_root=scan_root_str,
            level="TASK_START",
        ).info(f"开始任务: {self.task_name}")

        if dry_run:
            logger.bind(
                task_id=str(self.task_id),
                task_name=self.task_name,
            ).info("运行在预览模式（dry_run）")
            return

        self.task_repository.update_task(
            self.task_id,
            status=TaskStatus.RUNNING,
        )

    def _finish_task(self, dry_run: bool) -> None:
        """任务结束处理"""
        # 从数据库获取最终统计信息
        stats = self.file_item_repository.get_statistics(self.task_id)

        # 记录任务结束
        logger.bind(
            task_id=str(self.task_id),
            task_name=self.task_name,
            level="TASK_END",
            total_items=stats.get("total_items", 0),
            success_items=stats.get("success_items", 0),
            error_items=stats.get("error_items", 0),
            skipped_items=stats.get("skipped_items", 0),
        ).info(f"任务完成: {self.task_name}")

        if dry_run:
            logger.bind(
                task_id=str(self.task_id),
                task_name=self.task_name,
            ).info("预览模式执行完成")
            return

        self.task_repository.update_task(
            self.task_id,
            status=TaskStatus.COMPLETED,
            end_time=datetime.now(),
            statistics=stats,
        )

    def _process_file(self, path: Path, dry_run: bool) -> None:
        """处理单个文件

        执行：分析 → 执行 → 保存结果

        Args:
            path: 文件路径
            dry_run: 是否为预览模式
        """
        start_time = time.time()

        try:
            # 分析文件
            decision = analyze_file(path, self.analyze_config)

            # 执行决策
            result = execute_decision(
                decision,
                task_id=self.task_id,
                dry_run=dry_run,
                file_processor_repository=self.file_processor_repository,
            )

            # 计算耗时
            duration_ms = (time.time() - start_time) * 1000

            # 保存结果
            item_data = self._create_item_data(path, decision, result, duration_ms)
            self.file_item_repository.save_result(self.task_id, item_data)

            # 更新统计
            self._update_statistics(result, duration_ms)

            # 记录日志
            self._log_file_result(path, decision, result, duration_ms)

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.bind(
                task_id=str(self.task_id),
                task_name=self.task_name,
                error=str(e),
            ).error(f"处理文件失败: {path}")

            # 保存错误结果
            error_data = FileItemData(
                path=path,
                stem=path.stem,
                file_type=None,
                serial_id=None,
                decision_type="error",
                target_path=None,
                success=False,
                error_message=str(e),
                duration_ms=duration_ms,
            )
            self.file_item_repository.save_result(self.task_id, error_data)
            self.error_items += 1
            self.total_duration_ms += duration_ms

    def _create_item_data(
        self,
        path: Path,
        decision: FileDecision,
        result: ExecutionResult,
        duration_ms: float,
    ) -> FileItemData:
        """创建文件处理结果数据"""
        match decision:
            case MoveDecision():
                return FileItemData(
                    path=path,
                    stem=path.stem,
                    file_type=decision.file_type,
                    serial_id=decision.serial_id,
                    decision_type="move",
                    target_path=result.target_path,
                    success=result.status == ExecutionStatus.SUCCESS
                    or result.status == ExecutionStatus.PREVIEW,
                    error_message=result.message
                    if result.status == ExecutionStatus.ERROR
                    else None,
                    duration_ms=duration_ms,
                )
            case DeleteDecision():
                return FileItemData(
                    path=path,
                    stem=path.stem,
                    file_type=decision.file_type,
                    serial_id=None,
                    decision_type="delete",
                    target_path=None,
                    success=result.status == ExecutionStatus.SUCCESS
                    or result.status == ExecutionStatus.PREVIEW,
                    error_message=result.message
                    if result.status == ExecutionStatus.ERROR
                    else None,
                    duration_ms=duration_ms,
                )
            case SkipDecision():
                return FileItemData(
                    path=path,
                    stem=path.stem,
                    file_type=decision.file_type,
                    serial_id=None,
                    decision_type="skip",
                    target_path=None,
                    success=True,
                    error_message=None,
                    duration_ms=duration_ms,
                )

    def _update_statistics(self, result: ExecutionResult, duration_ms: float) -> None:
        """更新统计信息"""
        self.total_items += 1
        self.total_duration_ms += duration_ms

        match result.status:
            case ExecutionStatus.SUCCESS | ExecutionStatus.PREVIEW:
                self.success_items += 1
            case ExecutionStatus.ERROR:
                self.error_items += 1
            case ExecutionStatus.SKIPPED:
                self.skipped_items += 1

    def _log_file_result(
        self,
        path: Path,
        decision: FileDecision,
        result: ExecutionResult,
        duration_ms: float,
    ) -> None:
        """记录文件处理结果日志"""
        item_data: dict[str, str | float | None] = {
            "file_path": str(path),
            "decision_type": decision.decision_type,
            "status": result.status.value,
            "duration_ms": duration_ms,
        }

        if isinstance(decision, MoveDecision):
            item_data["file_type"] = (
                decision.file_type.value if decision.file_type else None
            )
            item_data["serial_id"] = (
                str(decision.serial_id) if decision.serial_id else None
            )
            item_data["target_path"] = (
                str(result.target_path) if result.target_path else None
            )

        logger.bind(
            task_id=str(self.task_id),
            task_name=self.task_name,
            level="ITEM_RESULT",
            **item_data,
        ).info(f"处理文件: {path.name}")

    def _cleanup_empty_directory(self, path: Path, dry_run: bool) -> None:
        """清理空目录

        Args:
            path: 目录路径
            dry_run: 是否为预览模式
        """
        if dry_run:
            return

        # 不删除扫描根目录
        if path.resolve() == self.scan_root.resolve():
            return

        if delete_directory_if_empty(path):
            logger.bind(
                task_id=str(self.task_id),
                task_name=self.task_name,
            ).info(f"清理空目录: {path}")
