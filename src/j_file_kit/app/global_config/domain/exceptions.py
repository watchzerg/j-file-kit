"""全局配置领域异常

定义全局配置相关的领域异常，用于在 application 层抛出。
API 层负责将这些异常转换为 HTTP 响应。
"""


class GlobalConfigError(Exception):
    """全局配置相关异常基类"""

    pass


class InvalidConfigError(GlobalConfigError):
    """无效配置异常（模型验证失败）

    当 GlobalConfig 模型验证失败时抛出。
    """

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"配置验证失败: {reason}")


class InvalidPathError(GlobalConfigError):
    """无效路径异常

    当目录路径配置验证失败时抛出（如路径冲突、必需字段缺失等）。
    """

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        error_msg = "目录配置验证失败:\n" + "\n".join(f"  - {e}" for e in errors)
        super().__init__(error_msg)


class ConfigUpdateError(GlobalConfigError):
    """配置更新失败异常

    当更新全局配置到数据库失败时抛出。
    """

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"更新配置失败: {reason}")
