"""任务基类

定义任务的抽象接口。
"""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod

from .db import DatabaseManager
from .models import TaskReport


class BaseTask(ABC):
    """任务基类

    所有任务必须继承此类并实现 run 方法。
    """

    @property
    @abstractmethod
    def task_name(self) -> str:
        """任务名称"""
        pass

    @abstractmethod
    def run(
        self,
        task_id: str,
        db_manager: DatabaseManager,
        dry_run: bool = False,
        cancelled_event: threading.Event | None = None,
    ) -> TaskReport:
        """运行任务

        Args:
            task_id: 任务ID
            db_manager: 数据库管理器实例
            dry_run: 是否为预览模式（不执行实际文件操作，只进行分析）
            cancelled_event: 取消事件，用于检查任务是否被取消

        Returns:
            任务报告

        Raises:
            Exception: 任务执行过程中的任何异常
        """
        pass
