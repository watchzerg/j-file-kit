"""文件任务领域异常

供 `FileTaskRunManager`、`api.app` 异常映射及测试使用；表示执行实例并发与生命周期冲突。
"""


class FileTaskError(Exception):
    """文件任务相关异常基类"""

    pass


class FileTaskNotFoundError(FileTaskError):
    """任务执行实例不存在异常"""

    def __init__(self, run_id: int) -> None:
        self.run_id = run_id
        super().__init__(f"任务执行实例不存在: {run_id}")


class FileTaskAlreadyRunningError(FileTaskError):
    """任务已在运行异常"""

    def __init__(self, running_run_id: int) -> None:
        self.running_run_id = running_run_id
        super().__init__(f"已有任务正在运行: {running_run_id}")


class FileTaskCancelledError(FileTaskError):
    """任务已取消异常"""

    def __init__(self, run_id: int) -> None:
        self.run_id = run_id
        super().__init__(f"任务已取消: {run_id}")
