"""任务基类协议

Task 是业务用例层，定义"做什么"。

这是抽象的任务协议，不依赖特定领域。
使用通用的任务概念，支持不同类型的任务实现。
所有具体任务实现必须继承此类并实现run方法。
"""

import threading
from abc import ABC, abstractmethod

from ..models.task import TaskType
from .repositories import TaskRepositoryRegistry


class BaseTask(ABC):
    """任务基类协议

    Task 是业务用例层，定义"做什么"。

    职责：
    - 定义业务用例，组合处理器，创建并配置 Pipeline
    - 通过 `create_pipeline()` 方法组装 Pipeline
    - 通过 `run()` 方法执行任务

    与 Pipeline 的关系：
    - Task 通过 `create_pipeline()` 创建 Pipeline
    - Task 通过 `run()` 方法执行任务，内部调用 Pipeline

    所有任务实现必须继承此类并实现run方法。
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

        Task 通过 `run()` 方法执行任务，内部调用 Pipeline。

        Args:
            task_id: 任务ID
            repository_registry: 任务仓储注册表，提供统一的 Repository 获取接口
            dry_run: 是否为预览模式（不执行实际文件操作，只进行分析）
            cancelled_event: 取消事件，用于检查任务是否被取消

        Raises:
            Exception: 任务执行过程中的任何异常
        """
        pass
