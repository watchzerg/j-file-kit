"""应用状态管理

管理应用的全局状态，包括配置和任务管理器。
在应用启动时初始化，提供统一的配置和任务管理接口。
"""

from __future__ import annotations

import os
from pathlib import Path

from ..services.task_manager import TaskManager
from .config.config import (
    TaskConfig,
    create_default_config,
    ensure_directories_exist,
    load_config,
    save_config,
)
from .filesystem.operations import path_exists
from .persistence.db import DatabaseManager


class AppState:
    """应用状态

    管理应用的全局状态，包括配置和任务管理器。
    """

    def __init__(self) -> None:
        """初始化应用状态

        从环境变量 J_FILE_KIT_CONFIG 或默认路径 configs/task_config.yaml 加载配置。
        """
        config_path = Path(os.getenv("J_FILE_KIT_CONFIG", "configs/task_config.yaml"))

        # 如果配置文件不存在，创建默认配置文件
        if not path_exists(config_path):
            default_config = create_default_config()
            save_config(default_config, config_path)

        # 加载配置
        self.config: TaskConfig = load_config(config_path)
        self._config_path = config_path

        # 确保所有目录存在
        ensure_directories_exist(self.config)

        # 创建数据库管理器（表结构在 __init__ 中自动创建）
        self.db_manager = DatabaseManager(self.config.global_.db_path)

        # 创建任务管理器
        self.task_manager: TaskManager = TaskManager(self.db_manager)

    def reload_config(self) -> None:
        """重新加载配置文件并更新内存中的配置

        Raises:
            FileNotFoundError: 配置文件不存在
            yaml.YAMLError: YAML 解析错误
            ValidationError: 配置验证失败
            OSError: 目录创建失败
        """
        self.config = load_config(self._config_path)
        ensure_directories_exist(self.config)
