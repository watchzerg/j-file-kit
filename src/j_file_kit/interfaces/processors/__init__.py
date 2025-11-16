"""处理器协议定义包

定义分析器、执行器和终结器的基类协议。
定义了 ItemProcessor（处理单个 item）和 TaskProcessor（处理任务级别）两个核心抽象。
"""

from .base import ItemProcessor, TaskProcessor
from .chain import ProcessorChain
from .item import Analyzer, Executor
from .task import Finalizer, Initializer

__all__ = [
    "ItemProcessor",
    "TaskProcessor",
    "Analyzer",
    "Executor",
    "Initializer",
    "Finalizer",
    "ProcessorChain",
]
