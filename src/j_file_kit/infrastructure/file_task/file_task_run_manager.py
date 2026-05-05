"""文件任务执行管理器

管理文件任务执行实例的生命周期、状态跟踪和取消。
同一时间只允许一个执行实例运行。
"""

import threading
from datetime import datetime

from loguru import logger

from j_file_kit.app.file_task.domain.ports import FileTaskRunRepository
from j_file_kit.app.file_task.domain.task_errors import (
    FileTaskAlreadyRunningError,
    FileTaskCancelledError,
    FileTaskNotFoundError,
)
from j_file_kit.app.file_task.domain.task_run import (
    FileTaskRun,
    FileTaskRunStatus,
    FileTaskTriggerType,
)
from j_file_kit.app.file_task.domain.task_runner import FileTaskRunner


def generate_run_name(
    task_type: str,
    trigger_type: FileTaskTriggerType,
    start_time: datetime,
) -> str:
    """生成执行实例可读名称

    格式: {task_type}-{trigger_type}-{YYYYMMDDHHMMSSmmm}
    示例: jav_video_organizer-manual-20241215143052123

    Args:
        task_type: 任务类型
        trigger_type: 触发类型
        start_time: 开始时间

    Returns:
        执行实例名称
    """
    date_time_str = start_time.strftime("%Y%m%d%H%M%S")
    millisecond = f"{start_time.microsecond // 1000:03d}"
    return f"{task_type}-{trigger_type.value}-{date_time_str}{millisecond}"


class FileTaskRunManager:
    """文件任务执行管理器

    负责管理文件任务执行实例的生命周期、状态跟踪和取消。
    同一时间只允许一个执行实例运行。

    设计说明：
    - 执行状态以数据库为权威来源，内存中只保存运行中的 run_id 和取消事件
    - 启动时执行崩溃恢复：将历史遗留的 PENDING/RUNNING 实例标记为 FAILED
    """

    def __init__(
        self,
        file_task_run_repository: FileTaskRunRepository,
    ) -> None:
        """初始化文件任务执行管理器

        Args:
            file_task_run_repository: 执行实例仓储
        """
        self.file_task_run_repository = file_task_run_repository
        self._lock = threading.Lock()
        self._running_run_id: int | None = None
        self._cancellation_event: threading.Event | None = None

        self._recover_from_crash()

    def start_run(
        self,
        task: FileTaskRunner,
        trigger_type: FileTaskTriggerType = FileTaskTriggerType.MANUAL,
        dry_run: bool = False,
    ) -> int:
        """启动执行实例，返回 run_id

        Args:
            task: 要执行的任务
            trigger_type: 触发类型，默认为手动
            dry_run: 是否为预览模式

        Returns:
            执行实例ID

        Raises:
            FileTaskAlreadyRunningError: 如果已有执行实例正在运行
        """
        with self._lock:
            running_run = self.file_task_run_repository.get_running_run()
            if running_run:
                raise FileTaskAlreadyRunningError(running_run.run_id)

            start_time = datetime.now()

            run_name = generate_run_name(
                task_type=task.task_type,
                trigger_type=trigger_type,
                start_time=start_time,
            )

            run_id = self.file_task_run_repository.create_run(
                run_name=run_name,
                task_type=task.task_type,
                trigger_type=trigger_type,
                status=FileTaskRunStatus.PENDING,
                start_time=start_time,
            )

            cancellation_event = threading.Event()
            self._cancellation_event = cancellation_event
            self._running_run_id = run_id

            thread = threading.Thread(
                target=self._execute_run,
                args=(run_id, task, dry_run, cancellation_event),
                daemon=True,
            )
            thread.start()

            return run_id

    def _execute_run(
        self,
        run_id: int,
        task: FileTaskRunner,
        dry_run: bool,
        cancellation_event: threading.Event,
    ) -> None:
        """执行任务（后台线程入口）

        Args:
            run_id: 执行实例ID
            task: 要执行的任务
            dry_run: 是否为预览模式
            cancellation_event: 取消事件
        """
        try:
            self.file_task_run_repository.update_run(
                run_id,
                status=FileTaskRunStatus.RUNNING,
            )

            statistics = task.run(
                run_id=run_id,
                dry_run=dry_run,
                cancellation_event=cancellation_event,
            )

            if cancellation_event.is_set():
                self.file_task_run_repository.update_run(
                    run_id,
                    status=FileTaskRunStatus.CANCELLED,
                    end_time=datetime.now(),
                )
                return

            self.file_task_run_repository.update_run(
                run_id,
                status=FileTaskRunStatus.COMPLETED,
                end_time=datetime.now(),
                statistics=statistics.model_dump(exclude_none=True),
            )

        except Exception as e:
            self.file_task_run_repository.update_run(
                run_id,
                status=FileTaskRunStatus.FAILED,
                end_time=datetime.now(),
                error_message=str(e),
            )
        finally:
            with self._lock:
                if self._running_run_id == run_id:
                    self._running_run_id = None
                    self._cancellation_event = None

    def cancel_run(self, run_id: int) -> None:
        """取消执行实例

        Args:
            run_id: 执行实例ID

        Raises:
            FileTaskNotFoundError: 如果执行实例不存在
            FileTaskCancelledError: 如果执行实例已完成、失败或已取消
        """
        with self._lock:
            run = self.file_task_run_repository.get_run(run_id)
            if not run:
                raise FileTaskNotFoundError(run_id)

            if run.status in (
                FileTaskRunStatus.COMPLETED,
                FileTaskRunStatus.FAILED,
                FileTaskRunStatus.CANCELLED,
            ):
                raise FileTaskCancelledError(run_id)

            if run.status == FileTaskRunStatus.RUNNING:
                if self._cancellation_event:
                    self._cancellation_event.set()
                self.file_task_run_repository.update_run(
                    run_id,
                    status=FileTaskRunStatus.CANCELLED,
                    end_time=datetime.now(),
                )
            elif run.status == FileTaskRunStatus.PENDING:
                self.file_task_run_repository.update_run(
                    run_id,
                    status=FileTaskRunStatus.CANCELLED,
                    end_time=datetime.now(),
                )

    def get_run(self, run_id: int) -> FileTaskRun:
        """获取执行实例信息

        Args:
            run_id: 执行实例ID

        Returns:
            执行实例记录

        Raises:
            FileTaskNotFoundError: 如果执行实例不存在
        """
        run = self.file_task_run_repository.get_run(run_id)
        if run is None:
            raise FileTaskNotFoundError(run_id)
        return run

    def list_runs(self) -> list[FileTaskRun]:
        """列出所有执行实例（按开始时间降序）

        Returns:
            执行实例列表
        """
        return self.file_task_run_repository.list_runs()

    def _recover_from_crash(self) -> None:
        """从崩溃中恢复：将历史遗留的 PENDING/RUNNING 实例标记为 FAILED

        在系统重启后，数据库中残留的 PENDING 或 RUNNING 实例无法继续执行，
        统一标记为 FAILED 并记录恢复日志。
        """
        with self._lock:
            incomplete_runs = (
                self.file_task_run_repository.get_pending_or_running_runs()
            )

            if not incomplete_runs:
                return

            recovery_time = datetime.now()
            error_message = "Task interrupted due to system restart"

            for run in incomplete_runs:
                self.file_task_run_repository.update_run(
                    run_id=run.run_id,
                    status=FileTaskRunStatus.FAILED,
                    end_time=recovery_time,
                    error_message=error_message,
                )

            self._running_run_id = None
            self._cancellation_event = None

            logger.bind(
                recovered_run_ids=[run.run_id for run in incomplete_runs],
            ).info(
                f"Recovered {len(incomplete_runs)} incomplete run(s) from previous session",
            )
