"""终结器实现

实现全局后处理功能，如清理空目录等。
终结器在所有文件处理完成后执行。

这些处理器位于服务层，可以依赖infrastructure层。
"""

import logging
from typing import Any

from ....interfaces.file.repositories import (
    FileItemRepository,
    FileProcessorRepository,
)
from ....interfaces.processors import Finalizer
from ....interfaces.repositories import TaskRepository
from ....models import ProcessorResult


class TaskStatisticsFinalizer(Finalizer):
    """任务统计信息终结器

    在任务完成后统计所有操作和性能指标，更新到 tasks 表。
    finalizer 是全局的，在所有文件处理完成后执行。

    设计意图：
    - 在 finalize 阶段统计：此时所有操作已完成，数据完整
    - 错误处理策略：finalizer 失败不应影响任务完成状态，记录错误但不抛出异常

    注意：这是任务级别的统计终结器，不特定于文件处理任务。
    """

    def __init__(
        self,
        task_id: int,
        task_repository: TaskRepository,
        file_processor_repository: FileProcessorRepository,
        file_item_repository: FileItemRepository,
    ) -> None:
        """初始化任务统计信息终结器

        Args:
            task_id: 任务ID
            task_repository: 任务仓储实例
            file_processor_repository: 文件处理操作仓储实例
            file_item_repository: 文件处理结果仓储实例
        """
        super().__init__("TaskStatisticsFinalizer")
        self.task_id = task_id
        self.task_repository = task_repository
        self.file_processor_repository = file_processor_repository
        self.file_item_repository = file_item_repository
        self._logger = logging.getLogger(__name__)

    def finalize(self) -> ProcessorResult:
        """全局终结处理

        统计任务的操作数量、文件类型分布和性能指标，并更新到 tasks 表。

        统计信息结构：
        {
            "operations": {
                "by_operation_type": {...},
                "by_item_type": {...}
            },
            "items": {
                "by_item_type": {...}
            },
            "performance": {
                "total_duration_ms": ...,
                "avg_duration_ms": ...,
                "min_duration_ms": ...,
                "max_duration_ms": ...,
                "items_per_second": ...
            }
        }

        Returns:
            处理结果，成功或错误
        """
        try:
            # 获取操作统计
            operation_stats = self.file_processor_repository.get_operation_statistics()

            # 获取item统计和性能指标
            detailed_stats = self.file_item_repository.get_detailed_statistics()

            # 合并统计信息为统一结构
            statistics: dict[str, Any] = {
                "operations": {
                    "by_operation_type": operation_stats.get("by_operation_type", {}),
                    "by_item_type": operation_stats.get("by_item_type", {}),
                },
                "items": {
                    "by_item_type": detailed_stats.get("by_item_type", {}),
                },
                "performance": detailed_stats.get("performance_metrics", {}),
            }

            # 更新数据库
            self.task_repository.update_task(self.task_id, statistics=statistics)

            return ProcessorResult.success(
                f"任务统计信息已更新：操作数={sum(operation_stats.get('by_operation_type', {}).values())}, "
                f"item数={sum(f.get('total', 0) for f in detailed_stats.get('by_item_type', {}).values())}"
            )

        except Exception as e:
            # finalizer 失败不应影响任务完成状态
            # 记录错误日志但不抛出异常
            error_msg = f"统计任务信息失败: {str(e)}"
            self._logger.error(error_msg, exc_info=True)
            return ProcessorResult.error(error_msg)
