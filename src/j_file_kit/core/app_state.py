"""应用状态管理

管理应用的全局状态，包括配置和任务管理器。
"""

from __future__ import annotations

import os
from pathlib import Path

from .config import TaskConfig, load_config
from .task_manager import TaskManager


class AppState:
    """应用状态

    管理应用的全局状态，包括配置和任务管理器。
    """

    def __init__(self, config_path: str | Path | None = None):
        """初始化应用状态

        Args:
            config_path: 配置文件路径，如果为 None 则从环境变量或默认路径加载
        """
        if config_path is None:
            config_path = os.getenv("J_FILE_KIT_CONFIG", "configs/task_config.yaml")

        self.config: TaskConfig = load_config(config_path)
        self.task_manager: TaskManager = TaskManager()
