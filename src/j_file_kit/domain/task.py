"""任务基类

定义任务的抽象接口。
所有具体任务实现必须继承此类并实现run方法。
"""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod

from ..infrastructure.persistence import (
    FileResultRepository,
    OperationRepository,
    TaskRepository,
)
from .models import TaskReport, TaskType


class BaseTask(ABC):
    """任务基类

    所有任务必须继承此类并实现 run 方法。
    """

    @property
    @abstractmethod
    def task_type(self) -> TaskType:
        """任务类型"""
        pass

    @abstractmethod
    def run(
        self,
        task_id: int,
        task_repository: TaskRepository,
        operation_repository: OperationRepository,
        file_result_repository: FileResultRepository,
        dry_run: bool = False,
        cancelled_event: threading.Event | None = None,
    ) -> TaskReport:
        """运行任务

        Args:
            task_id: 任务ID
            task_repository: 任务仓储实例
            operation_repository: 操作记录仓储实例
            file_result_repository: 文件结果仓储实例
            dry_run: 是否为预览模式（不执行实际文件操作，只进行分析）
            cancelled_event: 取消事件，用于检查任务是否被取消

        Returns:
            任务报告

        Raises:
            Exception: 任务执行过程中的任何异常
        """
        pass
