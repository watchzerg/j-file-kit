"""文件处理管道核心实现

文件处理管道（流程协调层），协调文件处理流程：扫描 → 分析 → 执行 → 终结。
主要处理文件，目录清理是辅助功能。
"""

import threading
import time
from datetime import datetime
from pathlib import Path

from loguru import logger

from j_file_kit.infrastructure.filesystem.scanner import scan_directory_items
from j_file_kit.infrastructure.logging.logging_setup import (
    configure_task_logger,
    remove_task_logger,
)
from j_file_kit.interfaces.file.repositories import (
    FileItemRepository,
    FileProcessorRepository,
)
from j_file_kit.interfaces.processors.chain import ProcessorChain
from j_file_kit.interfaces.processors.item import Analyzer, Executor
from j_file_kit.interfaces.processors.task import Finalizer, Initializer
from j_file_kit.interfaces.repositories import TaskRepository
from j_file_kit.models.config import AppConfig
from j_file_kit.models.contexts import PathEntryContext
from j_file_kit.models.path_entry import PathEntryInfo, PathEntryType
from j_file_kit.models.results import FileItemResult, ProcessorResult, ProcessorStatus
from j_file_kit.models.task import TaskReport
from j_file_kit.services.processors.file.executors import UnifiedFileExecutor

from .statistics import StatisticsTracker
from .utils import create_error_result, create_initial_context, extract_error_message


class FilePipeline:
    """文件处理管道协调器（流程协调层）

    文件处理管道是流程协调层，定义"怎么做流程"。

    职责：
    - 协调处理流程（扫描 → 处理 → 汇总）
    - 管理任务生命周期（初始化 → 处理 → 终结）
    - 封装统计信息管理和结果持久化
    - 主要处理文件，目录清理是辅助功能

    与 ProcessorChain 的关系：
    - Pipeline 通过 ProcessorChain 执行处理器
    - Pipeline 负责流程协调，ProcessorChain 负责处理器执行逻辑

    设计意图：
    - 统一文件处理流程，支持预览模式和实际执行模式
    - 协调处理器链的执行，管理任务生命周期
    - 封装统计信息管理，使职责更清晰
    """

    def __init__(
        self,
        config: AppConfig,
        task_name: str,
        log_dir: Path,
        file_processor_repository: FileProcessorRepository,
        file_item_repository: FileItemRepository,
        task_id: int,
        task_repository: TaskRepository,
    ) -> None:
        """初始化文件处理管道

        Args:
            config: 任务配置
            task_name: 任务名称
            log_dir: 日志目录
            file_processor_repository: 文件处理操作仓储实例
            file_item_repository: 文件处理结果仓储实例
            task_id: 任务ID
            task_repository: 任务仓储实例，finalizer 需要更新任务统计信息
        """
        self.config = config
        self.task_name = task_name
        self.task_id = task_id

        # 初始化组件
        self.scan_root = config.global_.inbox_dir
        self.processor_chain = ProcessorChain()
        self._log_handler_id = configure_task_logger(
            log_dir,
            self.task_name,
            self.task_id,
        )
        self.file_processor_repository = file_processor_repository
        self.file_item_repository = file_item_repository
        self.task_repository = task_repository

        # 保存EmptyDirectoryExecutor引用（如果存在），用于目录处理
        self.empty_directory_executor: Executor | None = None

        # 任务报告
        self.report = TaskReport(
            task_name=self.task_name,
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_items=0,
            success_items=0,
            error_items=0,
            skipped_items=0,
            warning_items=0,
            total_duration_ms=0.0,
        )

        # 统计信息跟踪器
        self.statistics_tracker = StatisticsTracker(self.report)

    def add_analyzer(self, analyzer: Analyzer) -> FilePipeline:
        """添加分析器

        Args:
            analyzer: 分析器实例

        Returns:
            管道实例（支持链式调用）
        """
        self.processor_chain.add_analyzer(analyzer)
        return self

    def add_executor(self, executor: Executor) -> FilePipeline:
        """添加执行器

        Args:
            executor: 执行器实例

        Returns:
            管道实例（支持链式调用）
        """
        self.processor_chain.add_executor(executor)
        # 如果是EmptyDirectoryExecutor，保存引用以便直接调用
        if executor.name == "EmptyDirectoryExecutor":
            self.empty_directory_executor = executor
        return self

    def add_initializer(self, initializer: Initializer) -> FilePipeline:
        """添加初始化器

        Args:
            initializer: 初始化器实例

        Returns:
            管道实例（支持链式调用）
        """
        self.processor_chain.add_initializer(initializer)
        return self

    def add_finalizer(self, finalizer: Finalizer) -> FilePipeline:
        """添加终结器

        Args:
            finalizer: 终结器实例

        Returns:
            管道实例（支持链式调用）
        """
        self.processor_chain.add_finalizer(finalizer)
        return self

    def create_unified_executor(self) -> Executor:
        """创建统一文件执行器（自动注入 file_processor_repository）

        Returns:
            配置好的统一文件执行器
        """
        return UnifiedFileExecutor(self.file_processor_repository)

    def _process_single_directory(
        self,
        item_info: PathEntryInfo,
        dry_run: bool,
    ) -> None:
        """处理单个目录

        在遍历过程中同步处理目录，利用自底向上遍历顺序确保空文件夹及时清理。
        目录清理是辅助操作，不需要复杂的统计和持久化，只需简单日志记录。

        设计意图：
        - 利用扫描顺序，在文件处理完成后及时清理空目录
        - 简化目录处理逻辑，不进行复杂的统计和持久化

        Args:
            item_info: 路径项信息（目录类型）
            dry_run: 是否为预览模式
        """
        # 仅在非dry_run模式下执行
        if dry_run:
            return

        # 创建PathEntryContext（使用工具函数保持一致性）
        ctx = create_initial_context(item_info)

        # 调用EmptyDirectoryExecutor处理（如果存在）
        if self.empty_directory_executor:
            result = self.empty_directory_executor.process(ctx)
            # 记录日志
            if result.status == ProcessorStatus.SUCCESS:
                logger.bind(
                    task_id=str(self.task_id),
                    task_name=self.task_name,
                ).info(f"目录清理成功: {item_info.path}")
            elif result.status == ProcessorStatus.SKIP:
                # 跳过的情况不需要记录日志
                pass
            elif result.status == ProcessorStatus.ERROR:
                logger.bind(
                    task_id=str(self.task_id),
                    task_name=self.task_name,
                    error=result.message,
                ).error(f"目录清理失败: {item_info.path}")

    def _process_single_file(
        self,
        item_info: PathEntryInfo,
        dry_run: bool,
    ) -> FileItemResult:
        """处理单个文件

        执行文件处理流程：创建上下文 → 执行处理器链 → 构建结果。

        设计意图：
        - 统一文件处理流程，支持预览模式和实际执行模式
        - 记录处理耗时，用于统计和日志

        Args:
            item_info: 路径项信息（文件类型）
            dry_run: 是否为预览模式

        Returns:
            文件结果
        """
        # 类型检查：只处理文件类型的项
        item_type_enum = PathEntryType(item_info.item_type)
        if item_type_enum != PathEntryType.FILE:
            raise ValueError(f"期望文件类型，但收到: {item_info.item_type}")

        file_start_time = time.time()

        # 创建处理上下文
        ctx = create_initial_context(item_info)

        # 根据模式执行不同的处理器
        if dry_run:
            processor_results = self._run_analyzers_only(ctx)
        else:
            processor_results = self.processor_chain.process_item(ctx)

        # 计算文件处理总耗时
        file_duration_ms = (time.time() - file_start_time) * 1000

        # 创建文件结果
        return FileItemResult(
            item_info=item_info,
            context=ctx,
            processor_results=processor_results,
            total_duration_ms=file_duration_ms,
            success=not any(
                r.status == ProcessorStatus.ERROR for r in processor_results
            ),
            error_message=extract_error_message(processor_results),
        )

    def _start_task(self, dry_run: bool) -> None:
        """任务开始处理

        执行初始化器，确保任务环境准备就绪。

        设计意图：
        - 统一任务开始逻辑，确保初始化器正确执行
        - 初始化失败时阻止任务继续执行

        Args:
            dry_run: 是否为预览模式

        Raises:
            RuntimeError: 如果任何 initializer 失败
        """
        scan_root_str = (
            str(self.config.global_.inbox_dir)
            if self.config.global_.inbox_dir
            else "未设置"
        )
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
            ).info("运行在干模式（预览模式）")

        # 执行初始化器（仅在非预览模式）
        if not dry_run:
            initializer_results = self.processor_chain.process_initializers()
            logger.bind(
                task_id=str(self.task_id),
                task_name=self.task_name,
            ).info(f"执行了 {len(initializer_results)} 个初始化器")

            # 检查是否有初始化器失败
            failed_initializers = [
                r for r in initializer_results if r.status == ProcessorStatus.ERROR
            ]
            if failed_initializers:
                error_messages = [r.message for r in failed_initializers]
                error_msg = "初始化失败:\n" + "\n".join(
                    f"  - {msg}" for msg in error_messages
                )
                logger.bind(
                    task_id=str(self.task_id),
                    task_name=self.task_name,
                ).error(error_msg)
                raise RuntimeError(error_msg)

    def _finish_task(self, dry_run: bool) -> None:
        """任务结束处理

        执行终结器，最终化统计信息，记录任务结束日志。

        设计意图：
        - 统一任务结束逻辑，确保终结器正确执行
        - 从数据库重新计算统计信息，确保准确性

        Args:
            dry_run: 是否为预览模式
        """
        # 执行终结器（仅在非预览模式）
        if not dry_run:
            finalizer_results = self.processor_chain.process_finalizers()
            logger.bind(
                task_id=str(self.task_id),
                task_name=self.task_name,
            ).info(f"执行了 {len(finalizer_results)} 个终结器")

        # 完成报告
        self.report.end_time = datetime.now()

        # 从数据库重新计算统计信息，确保准确性
        self.statistics_tracker.finalize(self.file_item_repository)

        # 记录任务结束
        report_data = self.report.model_dump(exclude_none=True)
        logger.bind(
            task_id=str(self.task_id),
            task_name=self.task_name,
            level="TASK_END",
            **report_data,
        ).info(f"任务完成: {self.task_name}")
        if dry_run:
            logger.bind(
                task_id=str(self.task_id),
                task_name=self.task_name,
            ).info("干模式执行完成")

    def run(
        self,
        dry_run: bool = False,
        cancelled_event: threading.Event | None = None,
    ) -> None:
        """运行管道

        协调文件处理流程：扫描 → 处理 → 汇总。
        主要处理文件，目录清理是辅助功能。

        设计意图：
        - 统一文件处理流程，支持预览模式和实际执行模式
        - 支持任务取消机制

        Args:
            dry_run: 是否为预览模式（不执行实际文件操作，只进行分析）
            cancelled_event: 取消事件，用于检查任务是否被取消
        """
        try:
            # 先检查扫描根目录是否设置（先验证，后执行）
            if self.scan_root is None:
                raise ValueError("扫描根目录未设置")

            self._start_task(dry_run)

            # 处理每个文件和目录（使用生成器模式，边扫描边处理）
            for path, item_type in scan_directory_items(self.scan_root):
                # 检查是否被取消
                if cancelled_event and cancelled_event.is_set():
                    logger.bind(
                        task_id=str(self.task_id),
                        task_name=self.task_name,
                    ).info("任务已被取消")
                    break

                try:
                    # 统一处理：使用 PathEntryInfo.from_path 创建信息对象
                    item_info = PathEntryInfo.from_path(path, item_type)

                    # 根据类型判断：文件或目录
                    if item_type == PathEntryType.FILE:
                        file_result = self._process_single_file(item_info, dry_run)
                        # 保存到数据库
                        item_result_id = self.file_item_repository.save_result(
                            file_result,
                        )
                        # 设置 item_result_id 到 context（虽然 executor 已执行，但可用于后续查询）
                        file_result.context.item_result_id = item_result_id
                        # 更新内存中的统计信息
                        self.statistics_tracker.update(file_result)
                        # 记录文件处理结果
                        item_data = {
                            "file_path": str(file_result.item_info.path),
                            "file_type": file_result.context.file_type,
                            "serial_id": (
                                str(file_result.context.serial_id)
                                if file_result.context.serial_id
                                else None
                            ),
                            "success": file_result.success,
                            "has_errors": file_result.has_errors,
                            "has_warnings": file_result.has_warnings,
                            "was_skipped": file_result.was_skipped,
                            "duration_ms": file_result.total_duration_ms,
                            "processor_count": len(file_result.processor_results),
                        }
                        if file_result.error_message:
                            item_data["error_message"] = file_result.error_message
                        logger.bind(
                            task_id=str(self.task_id),
                            task_name=self.task_name,
                            level="ITEM_RESULT",
                            **item_data,
                        ).info(f"处理文件: {file_result.item_info.path.name}")
                    else:
                        # 处理目录（清理空文件夹）
                        self._process_single_directory(item_info, dry_run)
                except Exception as e:
                    # 处理单个文件或目录时的异常
                    error_msg = "分析失败" if dry_run else "处理失败"
                    item_path = path
                    logger.bind(
                        task_id=str(self.task_id),
                        task_name=self.task_name,
                        error=str(e),
                    ).error(f"{error_msg}: {item_path}")
                    # 如果是文件，创建错误结果并保存
                    if item_type == PathEntryType.FILE:
                        item_info = PathEntryInfo.from_path(path, item_type)
                        error_result = create_error_result(item_info, e)
                        # 立即保存到数据库
                        item_result_id = self.file_item_repository.save_result(
                            error_result,
                        )
                        # 设置 item_result_id 到 context 中
                        error_result.context.item_result_id = item_result_id
                        # 更新内存中的统计信息
                        self.statistics_tracker.update(error_result)

                # 检查是否被取消
                if cancelled_event and cancelled_event.is_set():
                    logger.bind(
                        task_id=str(self.task_id),
                        task_name=self.task_name,
                    ).info("任务已被取消")
                    break

            self._finish_task(dry_run)

        except Exception as e:
            # 管道级别的异常
            logger.bind(
                task_id=str(self.task_id),
                task_name=self.task_name,
            ).error(f"管道执行失败: {str(e)}")
            raise
        finally:
            # 清理任务级别的日志 handler
            remove_task_logger(self._log_handler_id)

    def _run_analyzers_only(self, ctx: PathEntryContext) -> list[ProcessorResult]:
        """仅执行分析器（用于预览模式）

        在预览模式下，只执行分析器，不执行执行器。

        设计意图：
        - 支持预览模式，允许用户查看分析结果而不执行实际操作
        - 遇到错误或跳过标记时提前终止

        Args:
            ctx: 处理上下文

        Returns:
            分析器结果列表
        """
        results = []
        for analyzer in self.processor_chain.analyzers:
            result = analyzer.process(ctx)
            results.append(result)

            if result.status == ProcessorStatus.ERROR:
                break
            if ctx.skip_remaining:
                break

        return results
