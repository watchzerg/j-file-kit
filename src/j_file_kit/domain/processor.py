"""Processor 协议定义

定义分析器、执行器和终结器的基类协议。
定义了 ItemProcessor（处理单个 item）和 TaskProcessor（处理任务级别）两个核心抽象。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .models import ItemContext, ProcessorResult, ProcessorStatus


class ItemProcessor(ABC):
    """Item 级别处理器基类

    处理单个 item（文件、网页等），接收 ItemContext。
    """

    def __init__(self, name: str | None = None):
        """初始化处理器

        Args:
            name: 处理器名称，用于日志和调试
        """
        self.name = name or self.__class__.__name__

    @abstractmethod
    def process(self, ctx: ItemContext) -> ProcessorResult:
        """处理单个 item

        Args:
            ctx: Item 处理上下文

        Returns:
            处理结果
        """
        pass


class TaskProcessor(ABC):
    """任务级别处理器基类

    处理任务级别的操作，不接收 item 上下文。
    """

    def __init__(self, name: str | None = None):
        """初始化处理器

        Args:
            name: 处理器名称，用于日志和调试
        """
        self.name = name or self.__class__.__name__

    @abstractmethod
    def process_task(self) -> ProcessorResult:
        """处理任务级别操作

        Returns:
            处理结果
        """
        pass


class Analyzer(ItemProcessor):
    """分析器基类

    用于分析文件，填充 ItemContext 中的分析结果。
    分析器不应该执行文件操作，只负责分析。
    """

    def process(self, ctx: ItemContext) -> ProcessorResult:
        """分析文件

        子类应该重写此方法实现具体的分析逻辑。
        """
        return ProcessorResult.success(f"{self.name} 分析完成")


class Executor(ItemProcessor):
    """执行器基类

    用于执行文件操作，如重命名、移动等。
    执行器根据 ItemContext 中的分析结果执行操作。
    """

    def process(self, ctx: ItemContext) -> ProcessorResult:
        """执行操作

        子类应该重写此方法实现具体的执行逻辑。
        """
        return ProcessorResult.success(f"{self.name} 执行完成")


class Finalizer(TaskProcessor):
    """终结器基类

    用于全局后处理，如清理空目录、生成报告等。
    终结器在所有文件处理完成后执行。
    """

    def process_task(self) -> ProcessorResult:
        """处理任务级别操作（调用 finalize）"""
        return self.finalize()

    def finalize(self) -> ProcessorResult:
        """全局终结处理

        在所有文件处理完成后调用，用于执行全局清理等操作。
        """
        return ProcessorResult.success(f"{self.name} 全局终结完成")


class ProcessorChain:
    """处理器链

    管理一组处理器的执行顺序和结果。
    """

    def __init__(self) -> None:
        """初始化处理器链"""
        self.analyzers: list[Analyzer] = []
        self.executors: list[Executor] = []
        self.task_processors: list[TaskProcessor] = []

    def add_analyzer(self, analyzer: Analyzer) -> ProcessorChain:
        """添加分析器

        Args:
            analyzer: 分析器实例

        Returns:
            处理器链实例（支持链式调用）
        """
        self.analyzers.append(analyzer)
        return self

    def add_executor(self, executor: Executor) -> ProcessorChain:
        """添加执行器

        Args:
            executor: 执行器实例

        Returns:
            处理器链实例（支持链式调用）
        """
        self.executors.append(executor)
        return self

    def add_item_processor(self, processor: ItemProcessor) -> ProcessorChain:
        """添加 item 处理器（统一入口，内部自动分类）

        Args:
            processor: Item 处理器实例（Analyzer 或 Executor）

        Returns:
            处理器链实例（支持链式调用）
        """
        if isinstance(processor, Analyzer):
            self.analyzers.append(processor)
        elif isinstance(processor, Executor):
            self.executors.append(processor)
        return self

    def add_task_processor(self, processor: TaskProcessor) -> ProcessorChain:
        """添加任务处理器

        Args:
            processor: 任务处理器实例

        Returns:
            处理器链实例（支持链式调用）
        """
        self.task_processors.append(processor)
        return self

    def process_item(self, ctx: ItemContext) -> list[ProcessorResult]:
        """处理单个 item

        Args:
            ctx: Item 处理上下文

        Returns:
            所有处理器的结果列表
        """
        results = []

        # 执行分析器
        for analyzer in self.analyzers:
            result = analyzer.process(ctx)
            results.append(result)

            # 如果分析器返回错误，跳过后续处理器
            if result.status == ProcessorStatus.ERROR:
                break

            # 如果设置了短路标记，跳过后续处理器
            if ctx.skip_remaining:
                break

        # 如果前面没有错误且未短路，执行执行器
        if not ctx.skip_remaining and not any(
            r.status == ProcessorStatus.ERROR for r in results
        ):
            for executor in self.executors:
                result = executor.process(ctx)
                results.append(result)

                # 如果执行器返回错误，跳过后续处理器
                if result.status == ProcessorStatus.ERROR:
                    break

                # 如果设置了短路标记，跳过后续处理器
                if ctx.skip_remaining:
                    break

        return results

    def process_task(self) -> list[ProcessorResult]:
        """执行所有任务处理器

        Returns:
            所有任务处理器的结果列表
        """
        results = []

        for processor in self.task_processors:
            result = processor.process_task()
            results.append(result)

        return results

    def clear(self) -> None:
        """清空处理器链"""
        self.analyzers.clear()
        self.executors.clear()
        self.task_processors.clear()
