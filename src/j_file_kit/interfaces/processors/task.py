"""Task 级别处理器

定义处理任务级别的处理器基类，包括初始化器和终结器。
"""

from __future__ import annotations

from abc import abstractmethod

from ...models import ProcessorResult
from .base import TaskProcessor


class Initializer(TaskProcessor):
    """初始化器基类

    用于任务前置处理，如状态更新、配置验证、资源初始化等。
    初始化器在任务开始执行前调用，如果初始化失败，将阻止任务继续执行。
    """

    def process_task(self) -> ProcessorResult:
        """处理任务级别操作（调用 initialize）"""
        return self.initialize()

    @abstractmethod
    def initialize(self) -> ProcessorResult:
        """初始化处理

        在任务开始执行前调用，用于执行前置操作。
        如果初始化失败，应返回 ERROR 状态的结果，任务将不会继续执行。

        Returns:
            处理结果，成功或错误
        """
        pass


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
