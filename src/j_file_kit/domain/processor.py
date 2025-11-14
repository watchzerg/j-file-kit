"""Processor 协议定义

定义分析器、执行器和终结器的基类协议。
Processor是领域层的核心抽象，定义了文件处理的标准接口。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .models import ProcessingContext, ProcessorResult, ProcessorStatus


class Processor(ABC):
    """处理器基类

    所有处理器的抽象基类，定义统一的处理接口。
    """

    def __init__(self, name: str | None = None):
        """初始化处理器

        Args:
            name: 处理器名称，用于日志和调试
        """
        self.name = name or self.__class__.__name__

    @abstractmethod
    def process(self, ctx: ProcessingContext) -> ProcessorResult:
        """处理文件

        Args:
            ctx: 处理上下文

        Returns:
            处理结果
        """
        pass


class Analyzer(Processor):
    """分析器基类

    用于分析文件，填充 ProcessingContext 中的分析结果。
    分析器不应该执行文件操作，只负责分析。
    """

    def process(self, ctx: ProcessingContext) -> ProcessorResult:
        """分析文件

        子类应该重写此方法实现具体的分析逻辑。
        """
        return ProcessorResult.success(f"{self.name} 分析完成")


class Executor(Processor):
    """执行器基类

    用于执行文件操作，如重命名、移动等。
    执行器根据 ProcessingContext 中的分析结果执行操作。
    """

    def process(self, ctx: ProcessingContext) -> ProcessorResult:
        """执行操作

        子类应该重写此方法实现具体的执行逻辑。
        """
        return ProcessorResult.success(f"{self.name} 执行完成")


class Finalizer(Processor):
    """终结器基类

    用于全局后处理，如清理空目录、生成报告等。
    终结器在所有文件处理完成后执行。
    """

    def process(self, ctx: ProcessingContext) -> ProcessorResult:
        """后处理

        子类应该重写此方法实现具体的后处理逻辑。
        """
        return ProcessorResult.success(f"{self.name} 后处理完成")

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
        self.finalizers: list[Finalizer] = []

    def add_analyzer(self, analyzer: Analyzer) -> ProcessorChain:
        """添加分析器"""
        self.analyzers.append(analyzer)
        return self

    def add_executor(self, executor: Executor) -> ProcessorChain:
        """添加执行器"""
        self.executors.append(executor)
        return self

    def add_finalizer(self, finalizer: Finalizer) -> ProcessorChain:
        """添加终结器"""
        self.finalizers.append(finalizer)
        return self

    def process_file(self, ctx: ProcessingContext) -> list[ProcessorResult]:
        """处理单个文件

        Args:
            ctx: 处理上下文

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

    def finalize_all(self) -> list[ProcessorResult]:
        """执行所有终结器

        Returns:
            所有终结器的结果列表
        """
        results = []

        for finalizer in self.finalizers:
            result = finalizer.finalize()
            results.append(result)

        return results

    def clear(self) -> None:
        """清空处理器链"""
        self.analyzers.clear()
        self.executors.clear()
        self.finalizers.clear()
