"""管道协调器

协调整个文件处理流程：扫描 → 分析 → 执行 → 终结。
负责文件扫描、处理器链执行和结果汇总。
"""

from __future__ import annotations

import threading
import time
from datetime import datetime

from ..domain.models import (
    DirectoryInfo,
    FileContext,
    FileInfo,
    FileItemResult,
    ProcessorResult,
    ProcessorStatus,
    TaskReport,
)
from ..domain.processors import (
    Analyzer,
    Executor,
    Finalizer,
    Initializer,
    ProcessorChain,
)
from ..infrastructure.config.config import TaskConfig
from ..infrastructure.logging.logger import StructuredLogger
from ..infrastructure.persistence import (
    ItemResultRepository,
    OperationRepository,
    TaskRepository,
)
from .scanner import FileScanner


class Pipeline:
    """管道协调器

    协调整个文件处理流程：扫描 → 分析 → 执行 → 终结。
    """

    def __init__(
        self,
        config: TaskConfig,
        task_name: str,
        operation_repository: OperationRepository,
        item_result_repository: ItemResultRepository,
        task_id: int,
        task_repository: TaskRepository,
    ):
        """初始化管道

        Args:
            config: 任务配置
            task_name: 任务名称
            operation_repository: 操作记录仓储实例
            item_result_repository: Item结果仓储实例
            task_id: 任务ID
            task_repository: 任务仓储实例，finalizer 需要更新任务统计信息
        """
        self.config = config
        self.task_name = task_name

        # 初始化组件
        self.scanner = FileScanner(config.global_.scan_roots)
        self.processor_chain = ProcessorChain()
        self.logger = StructuredLogger(config.global_.log_dir, self.task_name)
        self.operation_repository = operation_repository
        self.item_result_repository = item_result_repository
        self.task_id = task_id
        self.task_repository = task_repository

        # 保存FileEmptyDirectoryExecutor引用（如果存在），用于目录处理
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

    def add_analyzer(self, analyzer: Analyzer) -> Pipeline:
        """添加分析器

        Args:
            analyzer: 分析器实例

        Returns:
            管道实例（支持链式调用）
        """
        self.processor_chain.add_analyzer(analyzer)
        return self

    def add_executor(self, executor: Executor) -> Pipeline:
        """添加执行器

        Args:
            executor: 执行器实例

        Returns:
            管道实例（支持链式调用）
        """
        self.processor_chain.add_executor(executor)
        # 如果是FileEmptyDirectoryExecutor，保存引用以便直接调用
        if executor.name == "FileEmptyDirectoryExecutor":
            self.empty_directory_executor = executor
        return self

    def add_initializer(self, initializer: Initializer) -> Pipeline:
        """添加初始化器

        Args:
            initializer: 初始化器实例

        Returns:
            管道实例（支持链式调用）
        """
        self.processor_chain.add_initializer(initializer)
        return self

    def add_finalizer(self, finalizer: Finalizer) -> Pipeline:
        """添加终结器

        Args:
            finalizer: 终结器实例

        Returns:
            管道实例（支持链式调用）
        """
        self.processor_chain.add_finalizer(finalizer)
        return self

    def create_unified_executor(self) -> Executor:
        """创建统一文件执行器（自动注入 operation_repository）

        Returns:
            配置好的统一文件执行器
        """
        from ..domain.file.processors.executors import UnifiedFileExecutor

        return UnifiedFileExecutor(self.operation_repository)

    def _create_initial_context(self, file_info: FileInfo) -> FileContext:
        """创建初始处理上下文

        Args:
            file_info: 文件信息

        Returns:
            初始化的处理上下文
        """
        return FileContext.model_construct(file_info=file_info)

    def _extract_error_message(
        self, processor_results: list[ProcessorResult]
    ) -> str | None:
        """从处理器结果中提取错误消息

        Args:
            processor_results: 处理器结果列表

        Returns:
            错误消息，如果没有错误则返回 None
        """
        return next(
            (r.message for r in processor_results if r.status == ProcessorStatus.ERROR),
            None,
        )

    def _create_error_result(
        self, file_info: FileInfo, error: Exception
    ) -> FileItemResult:
        """创建错误结果

        Args:
            file_info: 文件信息
            error: 异常对象

        Returns:
            错误文件结果
        """
        return FileItemResult(
            file_info=file_info,
            context=self._create_initial_context(file_info),
            success=False,
            error_message=str(error),
            total_duration_ms=0.0,
        )

    def _process_single_directory(
        self, directory_info: DirectoryInfo, dry_run: bool
    ) -> None:
        """处理单个目录

        在遍历过程中同步处理目录，利用自底向上遍历顺序确保空文件夹及时清理。
        直接传递DirectoryInfo给Executor，虽然类型不匹配但运行时安全。
        目录清理是辅助操作，不需要复杂的统计和持久化，只需简单日志记录。

        Args:
            directory_info: 目录信息
            dry_run: 是否为预览模式
        """
        # 仅在非dry_run模式下执行
        if dry_run:
            return

        # 创建FileContext，将directory_info赋值给ctx.file_info
        # 虽然类型声明是FileInfo，但FileEmptyDirectoryExecutor会通过路径判断，运行时安全
        ctx = FileContext.model_construct(file_info=directory_info)

        # 调用FileEmptyDirectoryExecutor处理（如果存在）
        if self.empty_directory_executor:
            result = self.empty_directory_executor.process(ctx)
            # 记录日志
            if result.status == ProcessorStatus.SUCCESS:
                self.logger.info(f"目录清理成功: {directory_info.path}")
            elif result.status == ProcessorStatus.SKIP:
                # 跳过的情况不需要记录日志
                pass
            elif result.status == ProcessorStatus.ERROR:
                self.logger.error(
                    f"目录清理失败: {directory_info.path}",
                    {"error": result.message},
                )

    def _process_single_file(
        self, file_info: FileInfo, dry_run: bool
    ) -> FileItemResult:
        """处理单个文件

        Args:
            file_info: 文件信息
            dry_run: 是否为预览模式

        Returns:
            文件结果
        """
        file_start_time = time.time()

        # 创建处理上下文
        ctx = self._create_initial_context(file_info)

        # 根据模式执行不同的处理器
        if dry_run:
            processor_results = self._run_analyzers_only(ctx)
        else:
            processor_results = self.processor_chain.process_item(ctx)

        # 计算文件处理总耗时
        file_duration_ms = (time.time() - file_start_time) * 1000

        # 创建文件结果
        return FileItemResult(
            file_info=file_info,
            context=ctx,
            processor_results=processor_results,
            total_duration_ms=file_duration_ms,
            success=not any(
                r.status == ProcessorStatus.ERROR for r in processor_results
            ),
            error_message=self._extract_error_message(processor_results),
        )

    def _start_task(self, dry_run: bool) -> None:
        """任务开始处理

        Args:
            dry_run: 是否为预览模式

        Raises:
            RuntimeError: 如果任何 initializer 失败
        """
        scan_roots_str = ", ".join(str(p) for p in self.config.global_.scan_roots)
        self.logger.log_task_start(scan_roots_str)
        if dry_run:
            self.logger.info("运行在干模式（预览模式）")

        # 执行初始化器（仅在非预览模式）
        if not dry_run:
            initializer_results = self.processor_chain.process_initializers()
            self.logger.info(f"执行了 {len(initializer_results)} 个初始化器")

            # 检查是否有初始化器失败
            failed_initializers = [
                r for r in initializer_results if r.status == ProcessorStatus.ERROR
            ]
            if failed_initializers:
                error_messages = [r.message for r in failed_initializers]
                error_msg = "初始化失败:\n" + "\n".join(
                    f"  - {msg}" for msg in error_messages
                )
                self.logger.error(error_msg)
                raise RuntimeError(error_msg)

    def _finish_task(self, dry_run: bool) -> None:
        """任务结束处理

        Args:
            dry_run: 是否为预览模式
        """
        # 执行终结器（仅在非预览模式）
        if not dry_run:
            finalizer_results = self.processor_chain.process_finalizers()
            self.logger.info(f"执行了 {len(finalizer_results)} 个终结器")

        # 完成报告
        self.report.end_time = datetime.now()

        # 从数据库重新计算统计信息，确保准确性
        # total_duration_ms 是所有item处理的总耗时，不是任务总耗时
        stats = self.item_result_repository.get_statistics()
        self.report.update_from_stats(stats)

        # 记录任务结束
        self.logger.log_task_end(self.report)
        if dry_run:
            self.logger.info("干模式执行完成")

    def run(
        self, dry_run: bool = False, cancelled_event: threading.Event | None = None
    ) -> TaskReport:
        """运行管道

        Args:
            dry_run: 是否为预览模式（不执行实际文件操作，只进行分析）
            cancelled_event: 取消事件，用于检查任务是否被取消

        Returns:
            任务报告
        """
        try:
            self._start_task(dry_run)

            # 处理每个文件和目录（使用生成器模式，边扫描边处理）
            for item in self.scanner.scan_items():
                # 检查是否被取消
                if cancelled_event and cancelled_event.is_set():
                    self.logger.info("任务已被取消")
                    break

                try:
                    # 根据类型判断：文件或目录
                    if isinstance(item, FileInfo):
                        file_result = self._process_single_file(item, dry_run)
                        # 保存到数据库
                        item_result_id = self.item_result_repository.save_result(
                            file_result
                        )
                        # 设置 item_result_id 到 context（虽然 executor 已执行，但可用于后续查询）
                        file_result.context.item_result_id = item_result_id
                        # 更新内存中的统计信息
                        self._update_statistics(file_result)
                        self.logger.log_item_result(file_result)
                    elif isinstance(item, DirectoryInfo):
                        # 处理目录（清理空文件夹）
                        self._process_single_directory(item, dry_run)
                except Exception as e:
                    # 处理单个文件或目录时的异常
                    error_msg = "分析失败" if dry_run else "处理失败"
                    item_path = item.path if hasattr(item, "path") else str(item)
                    self.logger.error(f"{error_msg}: {item_path}", {"error": str(e)})
                    # 如果是文件，创建错误结果并保存
                    if isinstance(item, FileInfo):
                        error_result = self._create_error_result(item, e)
                        # 立即保存到数据库
                        item_result_id = self.item_result_repository.save_result(
                            error_result
                        )
                        # 设置 item_result_id 到 context 中
                        error_result.context.item_result_id = item_result_id
                        # 更新内存中的统计信息
                        self._update_statistics(error_result)

            self._finish_task(dry_run)
            return self.report

        except Exception as e:
            # 管道级别的异常
            self.logger.error(f"管道执行失败: {str(e)}")
            raise

    def _update_statistics(self, result: FileItemResult) -> None:
        """更新统计信息

        Args:
            result: 文件结果
        """
        self.report.total_items += 1

        if result.success:
            if result.was_skipped:
                self.report.skipped_items += 1
            elif result.has_warnings:
                self.report.warning_items += 1
            else:
                self.report.success_items += 1
        else:
            self.report.error_items += 1

        self.report.total_duration_ms += result.total_duration_ms

    def _run_analyzers_only(self, ctx: FileContext) -> list[ProcessorResult]:
        """仅执行分析器（用于预览模式）

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
