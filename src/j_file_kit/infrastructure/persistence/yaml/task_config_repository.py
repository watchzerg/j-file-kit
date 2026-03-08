"""YAML 任务配置仓储实现。

将任务配置持久化到 YAML 文件，实现 TaskConfigRepository Protocol。
每个顶层 key 对应一个 task type。
"""

import os
import tempfile
from pathlib import Path
from typing import Any

import yaml

from j_file_kit.app.task_config.domain.models import TaskConfig


class TaskConfigRepositoryImpl:
    """YAML 任务配置仓储实现。

    读写 YAML 文件来存储任务配置。
    写入使用原子操作（临时文件 + os.replace）确保数据安全。
    """

    def __init__(self, config_path: Path) -> None:
        """初始化 YAML 任务配置仓储。

        Args:
            config_path: YAML 配置文件路径
        """
        self._config_path = config_path

    def _read_yaml(self) -> dict[str, Any]:
        """读取并解析 YAML 文件。

        Returns:
            解析后的字典

        Raises:
            ValueError: YAML 解析失败时给出清晰错误信息
        """
        try:
            content = self._config_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return {}

        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise ValueError(f"YAML 配置文件解析失败 ({self._config_path}): {e}") from e

        if data is None:
            return {}
        if not isinstance(data, dict):
            raise ValueError(
                f"YAML 配置文件格式错误: 顶层应为字典，实际为 {type(data).__name__}",
            )
        return dict(data)

    def _write_yaml(self, data: dict[str, Any]) -> None:
        """原子写入 YAML 文件。

        先写入临时文件，再 os.replace 替换，避免写入中途崩溃导致文件损坏。

        Args:
            data: 要写入的字典数据
        """
        parent = self._config_path.parent
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

    def get_by_type(self, task_type: str) -> TaskConfig | None:
        """根据任务类型获取任务配置。

        Args:
            task_type: 任务类型

        Returns:
            任务配置对象，如果不存在则返回 None
        """
        data = self._read_yaml()
        entry = data.get(task_type)
        if entry is None:
            return None

        return TaskConfig(
            type=task_type,
            enabled=entry["enabled"],
            config=entry["config"],
        )

    def update(self, config: TaskConfig) -> None:
        """更新任务配置。

        Args:
            config: 任务配置对象

        Raises:
            ValueError: 如果任务不存在
        """
        data = self._read_yaml()
        if config.type not in data:
            raise ValueError(f"任务配置不存在: {config.type}")

        data[config.type] = {
            "enabled": config.enabled,
            "config": config.config,
        }
        self._write_yaml(data)
