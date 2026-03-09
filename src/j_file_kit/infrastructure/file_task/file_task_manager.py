"""文件任务管理器

管理文件任务的执行、状态跟踪和取消。
负责任务的生命周期管理，同一时间只允许一个任务运行。
"""

import threading
from datetime import datetime

from loguru import logger

from j_file_kit.app.file_task.domain.models import (
    FileTaskAlreadyRunningError,
    FileTaskCancelledError,
    FileTaskNotFoundError,
    FileTaskRecord,
    FileTaskRunner,
    FileTaskStatus,
    FileTaskTriggerType,
)
from j_file_kit.app.file_task.domain.ports import FileTaskRepository


def generate_task_name(
    task_type: str,
    trigger_type: FileTaskTriggerType,
    start_time: datetime,
) -> str:
    """生成任务可读名称

    格式: {task_type}-{trigger_type}-{YYYYMMDDHHMMSSmmm}
    示例: jav_video_organizer-manual-20241215143052123

    Args:
        task_type: 任务类型
        trigger_type: 触发类型
        start_time: 开始时间

    Returns:
        任务名称
    """
    date_time_str = start_time.strftime("%Y%m%d%H%M%S")
    millisecond = f"{start_time.microsecond // 1000:03d}"
    return f"{task_type}-{trigger_type.value}-{date_time_str}{millisecond}"


class FileTaskManager:
    """文件任务管理器

    负责管理文件任务的执行、状态跟踪和取消。
    同一时间只允许一个任务运行。

    设计说明：
    - 任务状态以数据库为权威来源，内存中只保存运行中的 task_id 和取消事件
    - 启动时执行崩溃恢复：将历史遗留的 PENDING/RUNNING 任务标记为 FAILED
    """

    def __init__(
        self,
        file_task_repository: FileTaskRepository,
    ) -> None:
        """初始化文件任务管理器

        Args:
            file_task_repository: 任务仓储实例
        """
        self.file_task_repository = file_task_repository
        self._lock = threading.Lock()
        self._running_task_id: int | None = None
        self._cancellation_event: threading.Event | None = None

        self._recover_from_crash()

    def start_task(
        self,
        task: FileTaskRunner,
        trigger_type: FileTaskTriggerType = FileTaskTriggerType.MANUAL,
        dry_run: bool = False,
    ) -> int:
        """启动任务，返回 task_id

        Args:
            task: 要执行的任务
            trigger_type: 触发类型，默认为手动
            dry_run: 是否为预览模式

        Returns:
            任务ID

        Raises:
            FileTaskAlreadyRunningError: 如果已有任务正在运行
        """
        with self._lock:
            running_task = self.file_task_repository.get_running_task()
            if running_task:
                raise FileTaskAlreadyRunningError(running_task.task_id)

            start_time = datetime.now()

            task_name = generate_task_name(
                task_type=task.task_type,
                trigger_type=trigger_type,
                start_time=start_time,
            )

            task_id = self.file_task_repository.create_task(
                task_name=task_name,
                task_type=task.task_type,
                trigger_type=trigger_type,
                status=FileTaskStatus.PENDING,
                start_time=start_time,
            )

            cancellation_event = threading.Event()
            self._cancellation_event = cancellation_event
            self._running_task_id = task_id

            thread = threading.Thread(
                target=self._execute_task,
                args=(task_id, task, dry_run, cancellation_event),
                daemon=True,
            )
            thread.start()

            return task_id

    def _execute_task(
        self,
        task_id: int,
        task: FileTaskRunner,
        dry_run: bool,
        cancellation_event: threading.Event,
    ) -> None:
        """执行任务（后台线程入口）

        Args:
            task_id: 任务ID
            task: 要执行的任务
            dry_run: 是否为预览模式
            cancellation_event: 取消事件
        """
        try:
            self.file_task_repository.update_task(
                task_id,
                status=FileTaskStatus.RUNNING,
            )

            statistics = task.run(
                task_id=task_id,
                dry_run=dry_run,
                cancellation_event=cancellation_event,
            )

            if cancellation_event.is_set():
                self.file_task_repository.update_task(
                    task_id,
                    status=FileTaskStatus.CANCELLED,
                    end_time=datetime.now(),
                )
                return

            self.file_task_repository.update_task(
                task_id,
                status=FileTaskStatus.COMPLETED,
                end_time=datetime.now(),
                statistics=statistics.model_dump(exclude_none=True),
            )

        except Exception as e:
            self.file_task_repository.update_task(
                task_id,
                status=FileTaskStatus.FAILED,
                end_time=datetime.now(),
                error_message=str(e),
            )
        finally:
            with self._lock:
                if self._running_task_id == task_id:
                    self._running_task_id = None
                    self._cancellation_event = None

    def cancel_task(self, task_id: int) -> None:
        """取消任务

        Args:
            task_id: 任务ID

        Raises:
            FileTaskNotFoundError: 如果任务不存在
            FileTaskCancelledError: 如果任务已完成、失败或已取消
        """
        with self._lock:
            task_model = self.file_task_repository.get_task(task_id)
            if not task_model:
                raise FileTaskNotFoundError(task_id)

            if task_model.status in (
                FileTaskStatus.COMPLETED,
                FileTaskStatus.FAILED,
                FileTaskStatus.CANCELLED,
            ):
                raise FileTaskCancelledError(task_id)

            if task_model.status == FileTaskStatus.RUNNING:
                if self._cancellation_event:
                    self._cancellation_event.set()
                self.file_task_repository.update_task(
                    task_id,
                    status=FileTaskStatus.CANCELLED,
                    end_time=datetime.now(),
                )
            elif task_model.status == FileTaskStatus.PENDING:
                self.file_task_repository.update_task(
                    task_id,
                    status=FileTaskStatus.CANCELLED,
                    end_time=datetime.now(),
                )

    def get_task(self, task_id: int) -> FileTaskRecord:
        """获取任务信息

        Args:
            task_id: 任务ID

        Returns:
            任务记录

        Raises:
            FileTaskNotFoundError: 如果任务不存在
        """
        task_model = self.file_task_repository.get_task(task_id)
        if task_model is None:
            raise FileTaskNotFoundError(task_id)
        return task_model

    def list_tasks(self) -> list[FileTaskRecord]:
        """列出所有任务（按开始时间降序）

        Returns:
            任务列表
        """
        return self.file_task_repository.list_tasks()

    def _recover_from_crash(self) -> None:
        """从崩溃中恢复：将历史遗留的 PENDING/RUNNING 任务标记为 FAILED

        在系统重启后，数据库中残留的 PENDING 或 RUNNING 任务无法继续执行，
        统一标记为 FAILED 并记录恢复日志。
        """
        with self._lock:
            incomplete_tasks = self.file_task_repository.get_pending_or_running_tasks()

            if not incomplete_tasks:
                return

            recovery_time = datetime.now()
            error_message = "Task interrupted due to system restart"

            for task in incomplete_tasks:
                self.file_task_repository.update_task(
                    task_id=task.task_id,
                    status=FileTaskStatus.FAILED,
                    end_time=recovery_time,
                    error_message=error_message,
                )

            self._running_task_id = None
            self._cancellation_event = None

            logger.bind(
                recovered_task_ids=[task.task_id for task in incomplete_tasks],
            ).info(
                f"Recovered {len(incomplete_tasks)} incomplete task(s) from previous session",
            )
