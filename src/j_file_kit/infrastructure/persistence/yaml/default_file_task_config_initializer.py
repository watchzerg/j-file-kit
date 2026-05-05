"""默认 file task 配置 YAML 初始化器。

在 YAML 配置文件不存在时，从默认配置生成并写入。
"""

import os
import tempfile
from pathlib import Path

import yaml

from j_file_kit.app.file_task.domain.task_config import TaskConfig


class DefaultFileTaskConfigInitializer:
    """默认 file task 配置 YAML 初始化器。

    默认配置由组合根提供，本类仅在 YAML 文件不存在时创建并写入默认数据。
    """

    def __init__(
        self,
        config_path: Path,
        default_task_configs: list[TaskConfig],
    ) -> None:
        """初始化默认配置初始化器。

        Args:
            config_path: YAML 配置文件路径
            default_task_configs: 默认任务配置列表
        """
        self._config_path = config_path
        self._default_task_configs = default_task_configs

    def initialize(self) -> None:
        """初始化默认 file task 配置 YAML 文件。

        如果文件已存在则跳过，不覆盖用户修改。
        """
        if self._config_path.exists():
            return

        data: dict[str, object] = {}
        for task_config in self._default_task_configs:
            data[task_config.type] = {
                "enabled": task_config.enabled,
                "config": task_config.config,
            }

        parent = self._config_path.parent
        parent.mkdir(parents=True, exist_ok=True)

        fd, tmp_path = tempfile.mkstemp(dir=parent, suffix=".yaml.tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                yaml.dump(
                    data,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                )
            os.replace(tmp_path, self._config_path)
        except BaseException:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
