"""处理器链

ProcessorChain 是处理器执行层，定义"怎么执行处理器"。

管理一组处理器的执行顺序和结果。
明确区分前置处理（initializers）和后置处理（finalizers）。
"""

from ...models import ItemContext, ProcessorResult, ProcessorStatus
from .item import Analyzer, Executor
from .task import Finalizer, Initializer


class ProcessorChain:
    """处理器链

    ProcessorChain 是处理器执行层，定义"怎么执行处理器"。

    职责：
    - 管理处理器的注册和执行顺序
    - 区分不同类型的处理器：initializers、analyzers、executors、finalizers
    - 处理单个 item 的执行逻辑

    与 Pipeline 的关系：
    - Pipeline 通过 ProcessorChain 执行处理器
    - Pipeline 负责流程协调，ProcessorChain 负责处理器执行逻辑
    """

    def __init__(self) -> None:
        """初始化处理器链"""
        self.analyzers: list[Analyzer] = []
        self.executors: list[Executor] = []
        self.initializers: list[Initializer] = []
        self.finalizers: list[Finalizer] = []

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

    def add_initializer(self, initializer: Initializer) -> ProcessorChain:
        """添加初始化器

        Args:
            initializer: 初始化器实例

        Returns:
            处理器链实例（支持链式调用）
        """
        self.initializers.append(initializer)
        return self

    def add_finalizer(self, finalizer: Finalizer) -> ProcessorChain:
        """添加终结器

        Args:
            finalizer: 终结器实例

        Returns:
            处理器链实例（支持链式调用）
        """
        self.finalizers.append(finalizer)
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

    def process_initializers(self) -> list[ProcessorResult]:
        """执行所有初始化器

        Returns:
            所有初始化器的结果列表
        """
        results = []

        for initializer in self.initializers:
            result = initializer.process_task()
            results.append(result)

        return results

    def process_finalizers(self) -> list[ProcessorResult]:
        """执行所有终结器

        Returns:
            所有终结器的结果列表
        """
        results = []

        for finalizer in self.finalizers:
            result = finalizer.process_task()
            results.append(result)

        return results

    def clear(self) -> None:
        """清空处理器链"""
        self.analyzers.clear()
        self.executors.clear()
        self.initializers.clear()
        self.finalizers.clear()
