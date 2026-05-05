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
from j_file_kit.app.file_task.domain.task_config import TaskConfig
from j_file_kit.app.file_task.domain.task_run import (
    FileTaskRun,
    FileTaskRunStatus,
    FileTaskTriggerType,
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
    """单次文件处理结果的持久化端口（`file_results` 表），由 `FilePipeline` 在每文件末尾调用。

    数据流：`process_single_file_for_run`（见 `jav_pipeline.item_processor`）将 Decision 与执行结果经
    `build_file_item_data`（`jav_pipeline.result_mapper`）折叠为 `FileItemData` →
    `save_result(run_id, …)` 追加一行；任务收尾时 `get_statistics(run_id)` 聚合为
    `FileTaskRunStatistics`（与管道内内存计数器解耦，以仓储聚合为准）。

    方法均接收 `run_id`，便于仓储实现类作为单例注入多轮 run。
    """

    def save_result(self, run_id: int, result: FileItemData) -> int:
        """持久化单文件处理结果（成功、跳过、删除、或异常兜底的一条记录）。

        `run_id` 将本条结果与 `file_task_runs` 中的执行实例关联。返回值为新插入记录的数据库 ID（由实现定义）。
        """
        ...

    def get_statistics(self, run_id: int) -> dict[str, Any]:
        """按 `run_id` 从已落库结果聚合计数与总耗时，供任务收尾构建 `FileTaskRunStatistics`。

        键名约定：`total_items`、`success_items`、`error_items`、`skipped_items`、
        `warning_items`、`total_duration_ms`（与 `FileTaskRunStatistics` 字段对齐）。
        Raw 管道还会在内存侧合并 `phase*` 阶段计数后再校验模型。
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
