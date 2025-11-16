"""接口层

定义所有协议和抽象接口，包括处理器协议和任务协议。
"""

from .processors import (
    Analyzer,
    Executor,
    Finalizer,
    Initializer,
    ItemProcessor,
    ProcessorChain,
    TaskProcessor,
)
from .task import BaseTask

__all__ = [
    # 处理器协议
    "ItemProcessor",
    "TaskProcessor",
    "Analyzer",
    "Executor",
    "Initializer",
    "Finalizer",
    "ProcessorChain",
    # 任务协议
    "BaseTask",
]
