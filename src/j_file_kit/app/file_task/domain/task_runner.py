"""文件任务执行器协议（FileTaskRunner）

具体 Organizer 实现本协议；`FileTaskRunManager` 与 HTTP API 通过 `task_type` 分发到对应实现。
"""

import threading
from typing import Protocol

from j_file_kit.app.file_task.domain.task_run import FileTaskRunStatistics


class FileTaskRunner(Protocol):
    """可执行任务用例的协议：具体任务类（如 `JavVideoOrganizer`）在构造期注入仓储与配置来源，`run` 仅收运行时参数。

    契约：
        - `task_type`：与 YAML / 常量 `TASK_TYPE_*` 一致，供并发调度按类型串行或查找实现类。
        - `run(run_id, dry_run, cancellation_event)`：执行一次完整用例并返回 `FileTaskRunStatistics`；
          实现通常委托 `FilePipeline`，但协议不强行规定。

    依赖注入：`run` 不再传 repository，改为实现类 `__init__` 已持有端口，便于测试替换实现。
    """

    @property
    def task_type(self) -> str:
        """与 `TaskConfig.type` 相同的任务 slug（如 `jav_video_organizer`）。"""
        ...

    def run(
        self,
        run_id: int,
        dry_run: bool = False,
        cancellation_event: threading.Event | None = None,
    ) -> FileTaskRunStatistics:
        """执行一次任务并得到统计；`dry_run` 时执行器只做分析与预览性的 Decision 落地，不写真实文件移动/删除。

        `cancellation_event` 由管理器创建，长任务应在循环中轮询以便提前退出（如 `FilePipeline.run`）。
        """
        ...
