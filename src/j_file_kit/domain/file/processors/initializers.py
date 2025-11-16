"""初始化器实现

实现任务前置处理功能，如状态更新、配置验证、资源初始化等。
初始化器在任务开始执行前调用，如果初始化失败，将阻止任务继续执行。
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

from ...models import ProcessorResult, TaskStatus
from ...processor import Initializer

if TYPE_CHECKING:
    from ....infrastructure.config.config import FileOrganizeConfig, TaskConfig
    from ....infrastructure.persistence import TaskRepository


class FileTaskStatusInitializer(Initializer):
    """文件任务状态初始化器

    更新任务状态为 RUNNING。
    这是任务执行前的第一个初始化步骤，确保任务状态正确更新。

    设计意图：
    - 在任务开始执行前更新状态，确保状态一致性
    - 如果状态更新失败，任务不应继续执行
    """

    def __init__(
        self,
        task_id: int,
        task_repository: TaskRepository,
    ) -> None:
        """初始化文件任务状态初始化器

        Args:
            task_id: 任务ID
            task_repository: 任务仓储实例
        """
        super().__init__("FileTaskStatusInitializer")
        self.task_id = task_id
        self.task_repository = task_repository
        self._logger = logging.getLogger(__name__)

    def initialize(self) -> ProcessorResult:
        """初始化处理

        更新任务状态为 RUNNING。

        Returns:
            处理结果，成功或错误
        """
        try:
            self.task_repository.update_task(self.task_id, status=TaskStatus.RUNNING)
            self._logger.info(f"任务状态已更新为 RUNNING: task_id={self.task_id}")
            return ProcessorResult.success("任务状态已更新为 RUNNING")
        except Exception as e:
            error_msg = f"更新任务状态失败: {str(e)}"
            self._logger.error(error_msg, exc_info=True)
            return ProcessorResult.error(error_msg)


class FileConfigValidatorInitializer(Initializer):
    """文件任务配置验证初始化器

    验证文件任务配置的有效性，包括扫描路径和目标目录路径。
    确保配置正确后才能开始执行任务。

    设计意图：
    - 在任务执行前验证配置，避免执行过程中才发现配置错误
    - 验证项包括：扫描路径存在且可访问、目标目录路径有效、路径不冲突
    """

    def __init__(
        self,
        config: TaskConfig,
        file_config: FileOrganizeConfig,
    ) -> None:
        """初始化文件任务配置验证初始化器

        Args:
            config: 任务配置
            file_config: 文件整理任务配置
        """
        super().__init__("FileConfigValidatorInitializer")
        self.config = config
        self.file_config = file_config
        self._logger = logging.getLogger(__name__)

    def initialize(self) -> ProcessorResult:
        """初始化处理

        验证文件任务配置的有效性。

        Returns:
            处理结果，成功或错误
        """
        errors: list[str] = []

        # 验证扫描路径
        for scan_root in self.config.global_.scan_roots:
            if not scan_root.exists():
                errors.append(f"扫描路径不存在: {scan_root}")
            elif not scan_root.is_dir():
                errors.append(f"扫描路径不是目录: {scan_root}")
            elif not os.access(scan_root, os.R_OK):
                errors.append(f"扫描路径不可读: {scan_root}")

        # 验证目标目录路径
        target_dirs = {
            "organized_dir": self.file_config.organized_dir,
            "unorganized_dir": self.file_config.unorganized_dir,
            "archive_dir": self.file_config.archive_dir,
            "misc_dir": self.file_config.misc_dir,
        }

        # 验证目录路径不冲突（使用集合去重，检查是否有重复的规范化路径）
        resolved_paths: dict[Path, list[str]] = {}
        for dir_name, dir_path in target_dirs.items():
            resolved = dir_path.resolve()
            if resolved in resolved_paths:
                resolved_paths[resolved].append(dir_name)
            else:
                resolved_paths[resolved] = [dir_name]

        # 检查冲突
        for resolved_path, dir_names in resolved_paths.items():
            if len(dir_names) > 1:
                errors.append(
                    f"目录路径冲突: {', '.join(dir_names)} 都指向同一路径 {resolved_path}"
                )

        if errors:
            error_msg = "配置验证失败:\n" + "\n".join(f"  - {e}" for e in errors)
            self._logger.error(error_msg)
            return ProcessorResult.error(error_msg)

        self._logger.info("配置验证通过")
        return ProcessorResult.success("配置验证通过")


class FileResourceInitializer(Initializer):
    """文件任务资源初始化器

    确保任务所需的资源（目录）已准备就绪。
    验证目标目录是否存在，不存在则创建；验证目录权限（可写）。

    设计意图：
    - 在任务执行前确保所有必需的目录已准备好
    - 如果目录创建或权限验证失败，任务不应继续执行
    """

    def __init__(
        self,
        file_config: FileOrganizeConfig,
    ) -> None:
        """初始化文件任务资源初始化器

        Args:
            file_config: 文件整理任务配置
        """
        super().__init__("FileResourceInitializer")
        self.file_config = file_config
        self._logger = logging.getLogger(__name__)

    def initialize(self) -> ProcessorResult:
        """初始化处理

        确保目标目录存在且可写。

        Returns:
            处理结果，成功或错误
        """
        from ....infrastructure.filesystem.operations import (
            create_directory,
            path_exists,
        )

        errors: list[str] = []

        # 需要初始化的目录
        target_dirs = {
            "organized_dir": self.file_config.organized_dir,
            "unorganized_dir": self.file_config.unorganized_dir,
            "archive_dir": self.file_config.archive_dir,
            "misc_dir": self.file_config.misc_dir,
        }

        for dir_name, dir_path in target_dirs.items():
            try:
                # 如果目录不存在，创建它
                if not path_exists(dir_path):
                    self._logger.info(f"创建目录: {dir_path}")
                    create_directory(dir_path, parents=True, exist_ok=True)

                # 验证目录权限（可写）
                if not os.access(dir_path, os.W_OK):
                    errors.append(f"{dir_name} 不可写: {dir_path}")

            except OSError as e:
                errors.append(f"创建或验证 {dir_name} 失败: {dir_path}, 错误: {str(e)}")

        if errors:
            error_msg = "资源初始化失败:\n" + "\n".join(f"  - {e}" for e in errors)
            self._logger.error(error_msg)
            return ProcessorResult.error(error_msg)

        self._logger.info("资源初始化完成")
        return ProcessorResult.success("资源初始化完成")
