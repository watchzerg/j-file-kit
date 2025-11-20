"""任务基类协议

定义任务的抽象接口。
所有具体任务实现必须继承此类并实现run方法。
"""

import threading
from abc import ABC, abstractmethod

from ..models import TaskType
from .repositories import TaskRepositoryRegistry


class BaseTask(ABC):
    """任务基类协议

    定义任务的抽象接口，所有任务实现必须继承此类并实现run方法。
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
        repository_registry: TaskRepositoryRegistry,
        dry_run: bool = False,
        cancelled_event: threading.Event | None = None,
    ) -> None:
        """运行任务

        Args:
            task_id: 任务ID
            repository_registry: 任务仓储注册表，提供统一的 Repository 获取接口
            dry_run: 是否为预览模式（不执行实际文件操作，只进行分析）
            cancelled_event: 取消事件，用于检查任务是否被取消

        Raises:
            Exception: 任务执行过程中的任何异常
        """
        pass
