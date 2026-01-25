"""任务配置领域异常

定义任务配置相关的领域异常，用于任务配置管理流程。
API 层负责将这些异常转换为 HTTP 响应。
"""


class TaskConfigError(Exception):
    """任务配置相关异常基类"""

    pass


class MissingTaskNameError(TaskConfigError):
    """缺少任务名称异常

    更新任务配置时必须提供任务名称。
    """

    def __init__(self) -> None:
        super().__init__("更新任务配置时必须提供任务名称")


class TaskConfigNotFoundError(TaskConfigError):
    """任务配置不存在异常"""

    def __init__(self, task_name: str) -> None:
        self.task_name = task_name
        super().__init__(f"任务不存在: {task_name}")


class InvalidTaskConfigError(TaskConfigError):
    """无效任务配置异常"""

    def __init__(self, task_name: str, reason: str) -> None:
        self.task_name = task_name
        self.reason = reason
        super().__init__(f"更新任务 '{task_name}' 配置失败: {reason}")
