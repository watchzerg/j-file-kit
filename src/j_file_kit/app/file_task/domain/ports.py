"""文件任务仓储接口

定义文件任务 domain 的全部仓储协议，遵循依赖倒置原则：
- FileTaskRunRepository：执行实例记录的持久化（状态、统计），由 FileTaskRunManager 使用
- FileResultRepository：文件处理结果的持久化，由 FilePipeline 使用
- TaskConfigRepository：任务配置的持久化（YAML），由 FileTaskConfigService 使用

Repository 方法接收 run_id 参数而非构造时绑定，支持单例复用，简化依赖注入。
"""

from datetime import datetime
from typing import Any, Protocol

from j_file_kit.app.file_task.domain.decisions import FileItemData
from j_file_kit.app.file_task.domain.models import (
    FileTaskRun,
    FileTaskRunStatus,
    FileTaskTriggerType,
    TaskConfig,
)


class FileTaskRunRepository(Protocol):
    """文件任务执行实例仓储协议

    定义执行实例数据持久化操作的接口，对应数据库 file_task_runs 表。
    提供执行实例的创建、更新、查询等功能，由 FileTaskRunManager 使用。
    """

    def create_run(
        self,
        run_name: str,
        task_type: str,
        trigger_type: FileTaskTriggerType,
        status: FileTaskRunStatus,
        start_time: datetime,
    ) -> int:
        """创建执行实例记录，返回生成的 run_id

        Args:
            run_name: 执行实例名称
            task_type: 任务类型
            trigger_type: 触发类型
            status: 执行状态
            start_time: 开始时间

        Returns:
            生成的执行实例 ID
        """
        ...

    def update_run(
        self,
        run_id: int,
        status: FileTaskRunStatus | None = None,
        end_time: datetime | None = None,
        error_message: str | None = None,
        statistics: dict[str, Any] | None = None,
    ) -> None:
        """更新执行实例记录（仅更新非 None 字段）

        Args:
            run_id: 执行实例 ID
            status: 执行状态（可选）
            end_time: 结束时间（可选）
            error_message: 错误消息（可选）
            statistics: 统计信息字典（可选）
        """
        ...

    def get_run(self, run_id: int) -> FileTaskRun | None:
        """获取执行实例记录，不存在时返回 None

        Args:
            run_id: 执行实例 ID

        Returns:
            执行实例对象，如果不存在则返回 None
        """
        ...

    def list_runs(self) -> list[FileTaskRun]:
        """列出所有执行实例记录（按开始时间降序）

        Returns:
            执行实例列表
        """
        ...

    def get_running_run(self) -> FileTaskRun | None:
        """获取当前运行中的执行实例，无则返回 None

        Returns:
            运行中的执行实例，如果没有则返回 None
        """
        ...

    def get_pending_or_running_runs(self) -> list[FileTaskRun]:
        """获取所有待处理或运行中的执行实例（用于启动时崩溃恢复）

        Returns:
            待处理或运行中的执行实例列表
        """
        ...


class FileResultRepository(Protocol):
    """文件处理结果仓储协议

    定义文件处理结果持久化操作的接口，对应数据库 file_results 表。
    专门用于文件处理结果，不处理目录操作。
    提供保存结果、获取统计信息等功能，由 FilePipeline 使用。

    设计说明：方法接收 run_id 参数，支持 Repository 作为单例复用。
    """

    def save_result(self, run_id: int, result: FileItemData) -> int:
        """保存单个文件处理结果，返回生成的结果 ID

        Args:
            run_id: 执行实例 ID
            result: 文件处理结果数据

        Returns:
            生成的结果 ID
        """
        ...

    def get_statistics(self, run_id: int) -> dict[str, Any]:
        """获取执行实例维度的文件处理统计信息

        Args:
            run_id: 执行实例 ID

        Returns:
            统计信息字典，包含 total_items, success_items, error_items,
            skipped_items, warning_items, total_duration_ms
        """
        ...


class TaskConfigRepository(Protocol):
    """任务配置仓储协议

    定义任务配置数据持久化操作的接口，遵循依赖倒置原则。
    Infrastructure 层负责实现此接口。
    """

    def get_by_type(self, task_type: str) -> TaskConfig | None:
        """根据任务类型获取任务配置，不存在则返回 None

        Args:
            task_type: 任务类型（如 "jav_video_organizer"）

        Returns:
            任务配置对象，如果不存在则返回 None
        """
        ...

    def update(self, config: TaskConfig) -> None:
        """更新任务配置

        Args:
            config: 任务配置对象

        Raises:
            ValueError: 如果任务不存在
        """
        ...
