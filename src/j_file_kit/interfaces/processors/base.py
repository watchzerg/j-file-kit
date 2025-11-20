"""处理器基础协议

定义处理器的核心抽象接口。

这是处理器的基础抽象协议，不依赖特定领域。
定义了 ItemProcessor（处理单个 item）和 TaskProcessor（处理任务级别）两个核心抽象。
"""

from abc import ABC, abstractmethod

from ...models.contexts import ItemContext
from ...models.results import ProcessorResult


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
