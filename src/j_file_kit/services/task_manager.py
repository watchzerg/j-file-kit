"""任务管理器

管理任务的执行、状态跟踪和取消。
负责任务的生命周期管理，同一时间只允许一个任务运行。
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime
from typing import cast

from ..domain.models import (
    Task,
    TaskAlreadyRunningError,
    TaskCancelledError,
    TaskNotFoundError,
    TaskStatus,
    TaskType,
    TriggerType,
)
from ..domain.task import BaseTask
from ..infrastructure.persistence import (
    ItemResultRepository,
    OperationRepository,
    SQLiteConnectionManager,
    TaskRepository,
)

logger = logging.getLogger(__name__)


def generate_task_name(
    task_type: TaskType,
    trigger_type: TriggerType,
    start_time: datetime,
) -> str:
    """生成任务可读名称

    格式: {task_type}-{trigger_type}-{YYYYMMDDHHMMSSmmm}
    示例: video_organizer-manual-20241215143052123

    Args:
        task_type: 任务类型
        trigger_type: 触发类型
        start_time: 开始时间

    Returns:
        任务名称
    """
    date_time_str = start_time.strftime("%Y%m%d%H%M%S")
    millisecond = f"{start_time.microsecond // 1000:03d}"
    return f"{task_type.value}-{trigger_type.value}-{date_time_str}{millisecond}"


class TaskManager:
    """任务管理器

    负责管理任务的执行、状态跟踪和取消。
    同一时间只允许一个任务运行。
    """

    def __init__(
        self, task_repository: TaskRepository, sqlite_conn: SQLiteConnectionManager
    ) -> None:
        """初始化任务管理器

        Args:
            task_repository: 任务仓储实例
            sqlite_conn: SQLite 连接管理器实例
        """
        self.task_repository = task_repository
        self._sqlite_conn = sqlite_conn
        self._lock = threading.Lock()
        self._running_task_id: int | None = None
        self._cancellation_event: threading.Event | None = None

        # 启动时恢复：清理历史异常状态
        self._recover_from_crash()

    def start_task(
        self,
        task: BaseTask,
        trigger_type: TriggerType = TriggerType.MANUAL,
        dry_run: bool = False,
    ) -> int:
        """启动任务

        Args:
            task: 要执行的任务
            trigger_type: 触发类型，默认为手动
            dry_run: 是否为预览模式

        Returns:
            任务ID

        Raises:
            TaskAlreadyRunningError: 如果已有任务正在运行
        """
        with self._lock:
            # 检查是否有运行中的任务（从数据库查询，更可靠）
            running_task = self.task_repository.get_running_task()
            if running_task:
                raise TaskAlreadyRunningError(running_task.task_id)

            start_time = datetime.now()

            # 在插入前生成完整的 task_name
            task_name = generate_task_name(
                task_type=task.task_type,
                trigger_type=trigger_type,
                start_time=start_time,
            )

            # 创建新任务并获取生成的 task_id
            task_id = self.task_repository.create_task(
                task_name=task_name,
                task_type=task.task_type,
                trigger_type=trigger_type,
                status=TaskStatus.PENDING,
                start_time=start_time,
            )

            cancelled_event = threading.Event()
            self._cancellation_event = cancelled_event
            self._running_task_id = task_id

            # 在后台线程中执行任务
            thread = threading.Thread(
                target=self._execute_task,
                args=(task_id, task, dry_run, cancelled_event),
                daemon=True,
            )
            thread.start()

            return task_id

    def _execute_task(
        self,
        task_id: int,
        task: BaseTask,
        dry_run: bool,
        cancelled_event: threading.Event,
    ) -> None:
        """执行任务（内部方法）

        任务状态更新已移至 Pipeline 的 Initializer 中执行。

        Args:
            task_id: 任务ID
            task: 要执行的任务
            dry_run: 是否为预览模式
            cancelled_event: 取消事件
        """
        try:
            # 创建操作记录仓储
            operation_repository = OperationRepository(self._sqlite_conn, task_id)

            # 创建item结果仓储
            item_result_repository = ItemResultRepository(self._sqlite_conn, task_id)

            # 执行任务
            task.run(
                task_id=task_id,
                task_repository=self.task_repository,
                operation_repository=operation_repository,
                item_result_repository=item_result_repository,
                dry_run=dry_run,
                cancelled_event=cancelled_event,
            )

            # 检查是否被取消
            if cancelled_event.is_set():
                self.task_repository.update_task(
                    task_id,
                    status=TaskStatus.CANCELLED,
                    end_time=datetime.now(),
                )
                return

            # 任务完成
            self.task_repository.update_task(
                task_id,
                status=TaskStatus.COMPLETED,
                end_time=datetime.now(),
            )

        except Exception as e:
            # 任务失败
            self.task_repository.update_task(
                task_id,
                status=TaskStatus.FAILED,
                end_time=datetime.now(),
                error_message=str(e),
            )
        finally:
            # 清理运行中的任务ID
            with self._lock:
                if self._running_task_id == task_id:
                    self._running_task_id = None
                    self._cancellation_event = None

    def cancel_task(self, task_id: int) -> None:
        """取消任务

        Args:
            task_id: 任务ID

        Raises:
            TaskNotFoundError: 如果任务不存在
            TaskCancelledError: 如果任务已完成、失败或已取消
        """
        with self._lock:
            task_model = self.task_repository.get_task(task_id)
            if not task_model:
                raise TaskNotFoundError(task_id)

            # 检查任务状态
            if task_model.status in (
                TaskStatus.COMPLETED,
                TaskStatus.FAILED,
                TaskStatus.CANCELLED,
            ):
                raise TaskCancelledError(task_id)

            # 如果任务正在运行，设置取消事件
            if task_model.status == TaskStatus.RUNNING:
                if self._cancellation_event:
                    self._cancellation_event.set()
                self.task_repository.update_task(
                    task_id,
                    status=TaskStatus.CANCELLED,
                    end_time=datetime.now(),
                )
            elif task_model.status == TaskStatus.PENDING:
                # 如果任务还在等待，直接标记为取消
                self.task_repository.update_task(
                    task_id,
                    status=TaskStatus.CANCELLED,
                    end_time=datetime.now(),
                )

    def get_task(self, task_id: int) -> Task:
        """获取任务信息

        Args:
            task_id: 任务ID

        Returns:
            任务模型

        Raises:
            TaskNotFoundError: 如果任务不存在
        """
        task_model = self.task_repository.get_task(task_id)
        if task_model is None:
            raise TaskNotFoundError(task_id)
        return cast(Task, task_model)

    def list_tasks(self) -> list[Task]:
        """列出所有任务

        Returns:
            任务列表
        """
        return self.task_repository.list_tasks()

    def _recover_from_crash(self) -> None:
        """从崩溃中恢复：清理历史异常状态的任务

        在系统重启后，将数据库中所有 PENDING 或 RUNNING 状态的任务
        标记为 FAILED，因为系统已重启，这些任务无法继续执行。
        """
        with self._lock:
            incomplete_tasks = self.task_repository.get_pending_or_running_tasks()

            if not incomplete_tasks:
                return

            recovery_time = datetime.now()
            error_message = "Task interrupted due to system restart"

            for task in incomplete_tasks:
                self.task_repository.update_task(
                    task_id=task.task_id,
                    status=TaskStatus.FAILED,
                    end_time=recovery_time,
                    error_message=error_message,
                )

            # 确保内存状态为 None
            self._running_task_id = None
            self._cancellation_event = None

            # 记录恢复日志
            logger.info(
                "Recovered %d incomplete task(s) from previous session",
                len(incomplete_tasks),
                extra={
                    "recovered_task_ids": [task.task_id for task in incomplete_tasks]
                },
            )
