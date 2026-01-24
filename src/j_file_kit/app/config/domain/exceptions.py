"""配置领域异常

定义配置相关的领域异常，用于在 application 层抛出。
API 层负责将这些异常转换为 HTTP 响应。
"""


class ConfigError(Exception):
    """配置相关异常基类"""

    pass


class MissingTaskNameError(ConfigError):
    """缺少任务名称异常

    更新任务配置时必须提供任务名称。
    """

    def __init__(self) -> None:
        super().__init__("更新任务配置时必须提供任务名称")


class TaskConfigNotFoundError(ConfigError):
    """任务配置不存在异常"""

    def __init__(self, task_name: str) -> None:
        self.task_name = task_name
        super().__init__(f"任务不存在: {task_name}")


class InvalidTaskConfigError(ConfigError):
    """无效任务配置异常"""

    def __init__(self, task_name: str, reason: str) -> None:
        self.task_name = task_name
        self.reason = reason
        super().__init__(f"更新任务 '{task_name}' 配置失败: {reason}")


class InvalidConfigError(ConfigError):
    """无效配置异常（模型验证失败）"""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"配置验证失败: {reason}")


class InvalidPathError(ConfigError):
    """无效路径异常"""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        error_msg = "目录配置验证失败:\n" + "\n".join(f"  - {e}" for e in errors)
        super().__init__(error_msg)


class ConfigUpdateError(ConfigError):
    """配置更新失败异常"""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"更新配置失败: {reason}")


class ConfigReloadError(ConfigError):
    """配置重载失败异常"""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"重新加载配置失败: {reason}")
