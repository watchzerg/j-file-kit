"""任务管理器

管理任务的执行、状态跟踪和取消。
"""

from __future__ import annotations

import threading
import uuid
from datetime import datetime

from .models import (
    Task,
    TaskAlreadyRunningError,
    TaskCancelledError,
    TaskNotFoundError,
    TaskStatus,
)
from .task import BaseTask


class TaskManager:
    """任务管理器

    负责管理任务的执行、状态跟踪和取消。
    同一时间只允许一个任务运行。
    """

    def __init__(self) -> None:
        """初始化任务管理器"""
        self._tasks: dict[str, Task] = {}
        self._lock = threading.Lock()
        self._running_task_id: str | None = None
        self._cancelled_events: dict[str, threading.Event] = {}

    def start_task(self, task: BaseTask, dry_run: bool = False) -> str:
        """启动任务

        Args:
            task: 要执行的任务
            dry_run: 是否为预览模式

        Returns:
            任务ID

        Raises:
            TaskAlreadyRunningError: 如果已有任务正在运行
        """
        with self._lock:
            # 检查是否有运行中的任务
            if self._running_task_id is not None:
                running_task = self._tasks.get(self._running_task_id)
                if running_task and running_task.status == TaskStatus.RUNNING:
                    raise TaskAlreadyRunningError(self._running_task_id)

            # 创建新任务
            task_id = str(uuid.uuid4())
            cancelled_event = threading.Event()
            self._cancelled_events[task_id] = cancelled_event

            task_model = Task(
                task_id=task_id,
                task_name=task.task_name,
                status=TaskStatus.PENDING,
                start_time=datetime.now(),
                end_time=None,
                error_message=None,
                report=None,
            )
            self._tasks[task_id] = task_model
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
        task_id: str,
        task: BaseTask,
        dry_run: bool,
        cancelled_event: threading.Event,
    ) -> None:
        """执行任务（内部方法）

        Args:
            task_id: 任务ID
            task: 要执行的任务
            dry_run: 是否为预览模式
            cancelled_event: 取消事件
        """
        try:
            # 更新状态为运行中
            with self._lock:
                task_model = self._tasks.get(task_id)
                if task_model:
                    task_model.status = TaskStatus.RUNNING

            # 执行任务
            report = task.run(dry_run=dry_run, cancelled_event=cancelled_event)

            # 检查是否被取消
            if cancelled_event.is_set():
                with self._lock:
                    task_model = self._tasks.get(task_id)
                    if task_model:
                        task_model.status = TaskStatus.CANCELLED
                        task_model.end_time = datetime.now()
                return

            # 任务完成
            with self._lock:
                task_model = self._tasks.get(task_id)
                if task_model:
                    task_model.status = TaskStatus.COMPLETED
                    task_model.end_time = datetime.now()
                    task_model.report = report

        except Exception as e:
            # 任务失败
            with self._lock:
                task_model = self._tasks.get(task_id)
                if task_model:
                    task_model.status = TaskStatus.FAILED
                    task_model.end_time = datetime.now()
                    task_model.error_message = str(e)
        finally:
            # 清理运行中的任务ID
            with self._lock:
                if self._running_task_id == task_id:
                    self._running_task_id = None
                # 清理取消事件
                self._cancelled_events.pop(task_id, None)

    def cancel_task(self, task_id: str) -> None:
        """取消任务

        Args:
            task_id: 任务ID

        Raises:
            TaskNotFoundError: 如果任务不存在
            TaskCancelledError: 如果任务已完成、失败或已取消
        """
        with self._lock:
            task_model = self._tasks.get(task_id)
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
                cancelled_event = self._cancelled_events.get(task_id)
                if cancelled_event:
                    cancelled_event.set()
                task_model.status = TaskStatus.CANCELLED
                task_model.end_time = datetime.now()
            elif task_model.status == TaskStatus.PENDING:
                # 如果任务还在等待，直接标记为取消
                task_model.status = TaskStatus.CANCELLED
                task_model.end_time = datetime.now()

    def get_task(self, task_id: str) -> Task:
        """获取任务信息

        Args:
            task_id: 任务ID

        Returns:
            任务模型

        Raises:
            TaskNotFoundError: 如果任务不存在
        """
        with self._lock:
            task_model = self._tasks.get(task_id)
            if not task_model:
                raise TaskNotFoundError(task_id)
            return task_model

    def list_tasks(self) -> list[Task]:
        """列出所有任务

        Returns:
            任务列表
        """
        with self._lock:
            return list(self._tasks.values())
