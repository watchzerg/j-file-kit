"""管道协调器

协调文件扫描、处理器链执行和结果汇总。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ..utils.logger import StructuredLogger
from ..utils.progress import ProgressTracker
from ..utils.transaction_log import TransactionLog
from .config import TaskConfig
from .models import ProcessingContext, TaskReport, TaskResult, TaskStats
from .processor import Analyzer, Executor, Finalizer, ProcessorChain
from .scanner import FileScanner


class Pipeline:
    """管道协调器

    协调整个文件处理流程：扫描 → 分析 → 执行 → 终结。
    """

    def __init__(self, config: TaskConfig, task_name: str | None = None):
        """初始化管道

        Args:
            config: 任务配置
            task_name: 任务名称，如果为 None 则使用第一个启用的任务
        """
        self.config = config
        self.task_name = task_name or self._get_default_task_name()
        self.task_config = self._get_task_config()

        # 初始化组件
        self.scanner = FileScanner(config.global_.scan_roots)
        self.processor_chain = ProcessorChain()
        self.logger = StructuredLogger(config.global_.log_dir, self.task_name)
        self.transaction_log = TransactionLog(config.global_.log_dir, self.task_name)
        self.progress_logger = ProgressTracker(self.logger.console)

        # 任务报告
        self.report = TaskReport(
            task_name=self.task_name, start_time=datetime.now(), end_time=datetime.now()
        )

    def _get_default_task_name(self) -> str:
        """获取默认任务名称"""
        enabled_tasks = self.config.enabled_tasks
        if not enabled_tasks:
            raise ValueError("没有启用的任务")
        return enabled_tasks[0].name

    def _get_task_config(self) -> Any:
        """获取任务配置"""
        task = self.config.get_task(self.task_name)
        if not task:
            raise ValueError(f"任务不存在: {self.task_name}")
        return task

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

    def setup_scanner_filters(self) -> Pipeline:
        """设置扫描器过滤器

        根据任务配置设置相应的过滤器。

        Returns:
            管道实例
        """
        if self.task_config.type == "file_organize":
            # 文件整理任务：扫描所有文件
            pass  # 不添加过滤器，扫描所有文件
        elif self.task_config.type == "db_update":
            # 数据库更新任务：可能需要特定过滤器
            pass  # 根据具体需求添加过滤器

        return self

    def run(self) -> TaskReport:
        """运行管道

        Returns:
            任务报告
        """
        try:
            # 设置扫描器过滤器
            self.setup_scanner_filters()

            # 记录任务开始
            scan_roots_str = ", ".join(str(p) for p in self.config.global_.scan_roots)
            self.logger.log_task_start(scan_roots_str)
            self.progress_logger.start_progress()

            # 处理每个文件（使用生成器模式，边扫描边处理）
            for file_info in self.scanner.scan_files():
                try:
                    # 创建处理上下文
                    ctx = ProcessingContext(file_info=file_info)

                    # 执行处理器链
                    processor_results = self.processor_chain.process_file(ctx)

                    # 创建任务结果
                    task_result = TaskResult(
                        file_info=file_info,
                        context=ctx,
                        processor_results=processor_results,
                        total_duration_ms=sum(r.duration_ms for r in processor_results),
                        success=not any(r.status == "error" for r in processor_results),
                        error_message=next(
                            (
                                r.message
                                for r in processor_results
                                if r.status == "error"
                            ),
                            None,
                        ),
                    )

                    # 记录结果
                    self.report.add_result(task_result)
                    self.logger.log_file_result(task_result)
                    self.progress_logger.update_progress(file_info.name)

                except Exception as e:
                    # 处理单个文件时的异常
                    self.logger.error(
                        f"处理文件失败: {file_info.path}", {"error": str(e)}
                    )

                    # 创建错误结果
                    error_result = TaskResult(
                        file_info=file_info,
                        context=ProcessingContext(file_info=file_info),
                        success=False,
                        error_message=str(e),
                    )
                    self.report.add_result(error_result)
                    self.progress_logger.update_progress(file_info.name)

            # 执行终结器
            finalizer_results = self.processor_chain.finalize_all()
            self.logger.info(f"执行了 {len(finalizer_results)} 个终结器")

            # 完成报告
            self.report.end_time = datetime.now()
            self.report.total_duration_ms = (
                self.report.end_time - self.report.start_time
            ).total_seconds() * 1000

            # 记录任务结束
            self.logger.log_task_end(self.report)
            self.progress_logger.stop_progress()

            return self.report

        except Exception as e:
            # 管道级别的异常
            self.logger.error(f"管道执行失败: {str(e)}")
            self.progress_logger.stop_progress()
            raise

    def run_dry(self) -> TaskReport:
        """运行干模式（预览模式）

        不执行实际的文件操作，只进行分析和报告生成。

        Returns:
            任务报告
        """
        # 设置扫描器过滤器
        self.setup_scanner_filters()

        # 记录任务开始
        scan_roots_str = ", ".join(str(p) for p in self.config.global_.scan_roots)
        self.logger.log_task_start(scan_roots_str)
        self.logger.info("运行在干模式（预览模式）")

        # 处理每个文件（仅分析，不执行，使用生成器模式）
        for file_info in self.scanner.scan_files():
            try:
                # 创建处理上下文
                ctx = ProcessingContext(file_info=file_info)

                # 只执行分析器
                analyzer_results = []
                for analyzer in self.processor_chain.analyzers:
                    result = analyzer._timed_process(ctx)
                    analyzer_results.append(result)

                    if result.status == "error":
                        break
                    if ctx.skip_remaining:
                        break

                # 创建任务结果（标记为预览模式）
                task_result = TaskResult(
                    file_info=file_info,
                    context=ctx,
                    processor_results=analyzer_results,
                    total_duration_ms=sum(r.duration_ms for r in analyzer_results),
                    success=not any(r.status == "error" for r in analyzer_results),
                    error_message=next(
                        (r.message for r in analyzer_results if r.status == "error"),
                        None,
                    ),
                )

                # 记录结果
                self.report.add_result(task_result)
                self.logger.log_file_result(task_result)

            except Exception as e:
                # 处理单个文件时的异常
                self.logger.error(f"分析文件失败: {file_info.path}", {"error": str(e)})

        # 完成报告
        self.report.end_time = datetime.now()
        self.report.total_duration_ms = (
            self.report.end_time - self.report.start_time
        ).total_seconds() * 1000

        # 记录任务结束
        self.logger.log_task_end(self.report)
        self.logger.info("干模式执行完成")

        return self.report

    def get_stats(self) -> TaskStats:
        """获取当前统计信息

        Returns:
            任务统计信息
        """
        return self.progress_logger.stats
