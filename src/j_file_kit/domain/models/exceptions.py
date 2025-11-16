"""领域异常

定义领域相关的异常类型。
"""

from __future__ import annotations


class TaskError(Exception):
    """任务相关异常基类"""

    pass


class TaskNotFoundError(TaskError):
    """任务不存在异常"""

    def __init__(self, task_id: int):
        self.task_id = task_id
        super().__init__(f"任务不存在: {task_id}")


class TaskAlreadyRunningError(TaskError):
    """任务已在运行异常"""

    def __init__(self, running_task_id: int):
        self.running_task_id = running_task_id
        super().__init__(f"已有任务正在运行: {running_task_id}")


class TaskCancelledError(TaskError):
    """任务已取消异常"""

    def __init__(self, task_id: int):
        self.task_id = task_id
        super().__init__(f"任务已取消: {task_id}")
