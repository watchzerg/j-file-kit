"""任务基类协议

Task 是业务用例层，定义"做什么"。

这是抽象的任务协议，不依赖特定领域。
使用通用的任务概念，支持不同类型的任务实现。
所有具体任务实现必须符合此协议。
"""

import threading
from typing import TYPE_CHECKING, Protocol

from j_file_kit.shared.models.enums import TaskType

if TYPE_CHECKING:
    from j_file_kit.app.file_task.ports import TaskRepositoryRegistry


class BaseTask(Protocol):
    """任务基类协议

    Task 是业务用例层，定义"做什么"。

    职责：
    - 定义业务用例
    - 通过 `run()` 方法执行任务

    所有具体任务实现必须符合此协议（通过继承或实现相同接口）。
    """

    @property
    def task_type(self) -> TaskType:
        """任务类型"""
        ...

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
        ...
