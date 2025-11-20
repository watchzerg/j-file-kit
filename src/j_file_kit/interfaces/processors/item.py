"""Item 级别处理器协议

定义处理单个 item 的处理器基类，包括分析器和执行器。

这是抽象的 item 级别处理器协议，不依赖特定领域。
使用通用的 item 概念，支持文件、网页、爬虫数据等不同类型的 item。
"""

from ...models import ItemContext, ProcessorResult
from .base import ItemProcessor


class Analyzer(ItemProcessor):
    """分析器基类

    用于分析 item，填充 ItemContext 中的分析结果。
    分析器不应该执行操作，只负责分析。
    """

    def process(self, ctx: ItemContext) -> ProcessorResult:
        """分析 item

        子类应该重写此方法实现具体的分析逻辑。
        """
        return ProcessorResult.success(f"{self.name} 分析完成")


class Executor(ItemProcessor):
    """执行器基类

    用于执行操作，如重命名、移动等。
    执行器根据 ItemContext 中的分析结果执行操作。
    """

    def process(self, ctx: ItemContext) -> ProcessorResult:
        """执行操作

        子类应该重写此方法实现具体的执行逻辑。
        """
        return ProcessorResult.success(f"{self.name} 执行完成")
