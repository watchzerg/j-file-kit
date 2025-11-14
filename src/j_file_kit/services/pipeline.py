"""管道协调器

协调整个文件处理流程：扫描 → 分析 → 执行 → 终结。
负责文件扫描、处理器链执行和结果汇总。
"""

from __future__ import annotations

import threading
import time
from datetime import datetime
from typing import Any

from ..domain.models import (
    ProcessingContext,
    ProcessorResult,
    ProcessorStatus,
    TaskReport,
    TaskResult,
)
from ..domain.processor import Analyzer, Executor, Finalizer, ProcessorChain
from ..infrastructure.config.config import TaskConfig
from ..infrastructure.logging.logger import StructuredLogger
from ..infrastructure.persistence import OperationRepository
from .scanner import FileScanner


class Pipeline:
    """管道协调器

    协调整个文件处理流程：扫描 → 分析 → 执行 → 终结。
    """

    def __init__(
        self,
        config: TaskConfig,
        task_name: str,
        task_id: int,
        operation_repository: OperationRepository,
    ):
        """初始化管道

        Args:
            config: 任务配置
            task_name: 任务名称
            task_id: 任务ID
            operation_repository: 操作记录仓储实例
        """
        self.config = config
        self.task_name = task_name
        self.task_id = task_id
        self.task_config = self._get_task_config()

        # 初始化组件
        self.scanner = FileScanner(config.global_.scan_roots)
        self.processor_chain = ProcessorChain()
        self.logger = StructuredLogger(config.global_.log_dir, self.task_name)
        self.operation_repository = operation_repository

        # 任务报告
        self.report = TaskReport(
            task_name=self.task_name,
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_files=0,
            success_files=0,
            error_files=0,
            skipped_files=0,
            warning_files=0,
            total_duration_ms=0.0,
        )

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

    def create_unified_executor(self) -> Executor:
        """创建统一文件执行器（自动注入 operation_repository）

        Returns:
            配置好的统一文件执行器
        """
        from ..domain.processors.executors import UnifiedFileExecutor

        return UnifiedFileExecutor(self.operation_repository)

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
            # 记录任务开始
            scan_roots_str = ", ".join(str(p) for p in self.config.global_.scan_roots)
            self.logger.log_task_start(scan_roots_str)
            if dry_run:
                self.logger.info("运行在干模式（预览模式）")

            # 处理每个文件（使用生成器模式，边扫描边处理）
            for file_info in self.scanner.scan_files():
                # 检查是否被取消
                if cancelled_event and cancelled_event.is_set():
                    self.logger.info("任务已被取消")
                    break
                try:
                    # 记录文件处理开始时间
                    file_start_time = time.time()

                    # 创建处理上下文
                    ctx = ProcessingContext(
                        file_info=file_info,
                        file_type=None,
                        serial_id=None,
                        target_path=None,
                        skip_remaining=False,
                        action=None,
                        target_dir=None,
                        should_delete=False,
                    )

                    # 根据模式执行不同的处理器
                    if dry_run:
                        processor_results = self._run_analyzers_only(ctx)
                    else:
                        processor_results = self.processor_chain.process_file(ctx)

                    # 计算文件处理总耗时
                    file_duration_ms = (time.time() - file_start_time) * 1000

                    # 创建任务结果
                    task_result = TaskResult(
                        file_info=file_info,
                        context=ctx,
                        processor_results=processor_results,
                        total_duration_ms=file_duration_ms,
                        success=not any(
                            r.status == ProcessorStatus.ERROR for r in processor_results
                        ),
                        error_message=next(
                            (
                                r.message
                                for r in processor_results
                                if r.status == ProcessorStatus.ERROR
                            ),
                            None,
                        ),
                    )

                    # 记录结果
                    self.report.add_result(task_result)
                    self.logger.log_file_result(task_result)

                except Exception as e:
                    # 处理单个文件时的异常
                    error_msg = "分析文件失败" if dry_run else "处理文件失败"
                    self.logger.error(
                        f"{error_msg}: {file_info.path}", {"error": str(e)}
                    )

                    # 创建错误结果
                    error_result = TaskResult(
                        file_info=file_info,
                        context=ProcessingContext(
                            file_info=file_info,
                            file_type=None,
                            serial_id=None,
                            target_path=None,
                            skip_remaining=False,
                            action=None,
                            target_dir=None,
                            should_delete=False,
                        ),
                        success=False,
                        error_message=str(e),
                        total_duration_ms=0.0,
                    )
                    self.report.add_result(error_result)

            # 执行终结器（仅在非预览模式）
            if not dry_run:
                finalizer_results = self.processor_chain.finalize_all()
                self.logger.info(f"执行了 {len(finalizer_results)} 个终结器")

            # 完成报告
            self.report.end_time = datetime.now()
            self.report.total_duration_ms = (
                self.report.end_time - self.report.start_time
            ).total_seconds() * 1000

            # 记录任务结束
            self.logger.log_task_end(self.report)
            if dry_run:
                self.logger.info("干模式执行完成")

            return self.report

        except Exception as e:
            # 管道级别的异常
            self.logger.error(f"管道执行失败: {str(e)}")
            raise

    def _run_analyzers_only(self, ctx: ProcessingContext) -> list[ProcessorResult]:
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
