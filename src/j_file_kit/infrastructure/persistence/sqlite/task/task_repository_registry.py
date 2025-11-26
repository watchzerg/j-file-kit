"""任务仓储注册表实现

管理所有类型的 Repository，提供统一的获取接口。
实现 TaskRepositoryRegistry Protocol。
"""

from j_file_kit.app.file_task.ports import (
    FileItemRepository,
    FileProcessorRepository,
    TaskRepository,
)
from j_file_kit.infrastructure.persistence.sqlite.connection import (
    SQLiteConnectionManager,
)
from j_file_kit.infrastructure.persistence.sqlite.task.file_item_repository import (
    FileItemRepositoryImpl,
)
from j_file_kit.infrastructure.persistence.sqlite.task.file_processor_repository import (
    FileProcessorRepositoryImpl,
)


class TaskRepositoryRegistryImpl:
    """任务仓储注册表实现

    管理所有类型的 Repository，提供统一的获取接口。
    作为依赖注入容器，统一管理 Repository 的生命周期。

    实现 TaskRepositoryRegistry Protocol。
    """

    def __init__(
        self,
        connection_manager: SQLiteConnectionManager,
        task_id: int,
        task_repository: TaskRepository,
    ) -> None:
        """初始化任务仓储注册表

        Args:
            connection_manager: SQLite 连接管理器
            task_id: 任务 ID
            task_repository: 任务仓储实例（全局，不依赖 task_id）
        """
        self._connection_manager = connection_manager
        self._task_id = task_id
        self._task_repository = task_repository
        self._file_item_repository: FileItemRepository | None = None
        self._file_processor_repository: FileProcessorRepository | None = None

    def get_task_repository(self) -> TaskRepository:
        """获取任务仓储

        Returns:
            任务仓储实例
        """
        return self._task_repository

    def get_file_item_repository(self) -> FileItemRepository:
        """获取文件处理结果仓储

        使用懒加载模式，首次调用时创建。

        Returns:
            文件处理结果仓储实例
        """
        if self._file_item_repository is None:
            self._file_item_repository = FileItemRepositoryImpl(
                self._connection_manager,
                self._task_id,
            )
        return self._file_item_repository

    def get_file_processor_repository(self) -> FileProcessorRepository:
        """获取文件处理操作仓储

        使用懒加载模式，首次调用时创建。

        Returns:
            文件处理操作仓储实例
        """
        if self._file_processor_repository is None:
            self._file_processor_repository = FileProcessorRepositoryImpl(
                self._connection_manager,
                self._task_id,
            )
        return self._file_processor_repository
