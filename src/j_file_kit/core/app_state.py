"""应用状态管理

管理应用的全局状态，包括配置和任务管理器。
"""

from __future__ import annotations

import os
from pathlib import Path

from .config import (
    TaskConfig,
    create_default_config,
    ensure_directories_exist,
    load_config,
    save_config,
)
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

        config_path = Path(config_path)

        # 如果配置文件不存在，创建默认配置文件
        if not config_path.exists():
            default_config = create_default_config()
            save_config(default_config, config_path)

        # 加载配置
        self.config: TaskConfig = load_config(config_path)
        self._config_path = config_path

        # 确保所有目录存在
        ensure_directories_exist(self.config)

        self.task_manager: TaskManager = TaskManager()

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
