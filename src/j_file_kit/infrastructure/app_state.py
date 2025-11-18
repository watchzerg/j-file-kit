"""应用状态管理

管理应用的全局状态，包括配置和任务管理器。
在应用启动时初始化，提供统一的配置和任务管理接口。
"""

from __future__ import annotations

import os
from pathlib import Path

from ..services.task_manager import TaskManager
from .config.config import TaskConfig, load_config_from_db
from .filesystem.operations import create_directory
from .persistence import ConfigRepository, SQLiteConnectionManager, TaskRepository


class AppState:
    """应用状态

    管理应用的全局状态，包括配置和任务管理器。
    """

    def __init__(self) -> None:
        """初始化应用状态

        从环境变量 J_FILE_KIT_BASE_DIR 读取基础目录（默认 `.app-data`），
        确定固定路径，创建配置仓储，从数据库加载配置。
        """
        # 从环境变量读取基础目录
        self.base_dir = Path(os.getenv("J_FILE_KIT_BASE_DIR", ".app-data"))

        # 确定固定路径
        self.db_path = self.base_dir / "sqlite" / "j_file_kit.db"
        self.log_dir = self.base_dir / "logs"
        self.report_dir = self.base_dir / "reports"

        # 创建必要的目录
        create_directory(self.base_dir / "sqlite", parents=True)
        create_directory(self.log_dir, parents=True)

        # 创建 SQLite 连接管理器（表结构在 __init__ 中自动创建）
        self.sqlite_conn = SQLiteConnectionManager(self.db_path)

        # 创建配置仓储（会自动初始化默认配置）
        self.config_repository = ConfigRepository(self.sqlite_conn)

        # 从数据库加载配置
        self.config: TaskConfig = load_config_from_db(self.sqlite_conn)

        # 创建任务仓储
        self.task_repository = TaskRepository(self.sqlite_conn)

        # 创建任务管理器
        self.task_manager: TaskManager = TaskManager(
            self.task_repository, self.sqlite_conn
        )

    def reload_config(self) -> None:
        """重新加载配置并更新内存中的配置

        从数据库重新加载配置。

        Raises:
            ValueError: 如果配置加载失败
        """
        self.config = load_config_from_db(self.sqlite_conn)
