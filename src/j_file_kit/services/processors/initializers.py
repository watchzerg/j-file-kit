"""初始化器实现

实现任务前置处理功能，如状态更新、配置验证、资源初始化等。
初始化器在任务开始执行前调用，如果初始化失败，将阻止任务继续执行。

这些处理器位于服务层，可以依赖infrastructure层。
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

from ...interfaces.processors import Initializer
from ...models import ProcessorResult, TaskStatus

if TYPE_CHECKING:
    from ...infrastructure.config.config import TaskConfig
    from ...infrastructure.persistence import TaskRepository


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
    ) -> None:
        """初始化文件任务配置验证初始化器

        Args:
            config: 任务配置
        """
        super().__init__("FileConfigValidatorInitializer")
        self.config = config
        self._logger = logging.getLogger(__name__)

    def _validate_inbox_dir(self) -> list[str]:
        """验证inbox_dir

        Returns:
            错误列表
        """
        errors: list[str] = []
        inbox_dir = self.config.global_.inbox_dir
        if inbox_dir is None:
            errors.append("待处理目录（inbox_dir）未设置")
        elif not inbox_dir.exists():
            errors.append(f"待处理目录不存在: {inbox_dir}")
        elif not inbox_dir.is_dir():
            errors.append(f"待处理目录不是目录: {inbox_dir}")
        elif not os.access(inbox_dir, os.R_OK):
            errors.append(f"待处理目录不可读: {inbox_dir}")
        return errors

    def _validate_other_dirs(self) -> list[str]:
        """验证其他目录

        Returns:
            错误列表
        """
        errors: list[str] = []
        target_dirs = {
            "sorted_dir": self.config.global_.sorted_dir,
            "unsorted_dir": self.config.global_.unsorted_dir,
            "archive_dir": self.config.global_.archive_dir,
            "misc_dir": self.config.global_.misc_dir,
        }

        for dir_name, dir_path in target_dirs.items():
            if dir_path is not None:
                if not dir_path.exists():
                    errors.append(f"{dir_name} 不存在: {dir_path}")
                elif not dir_path.is_dir():
                    errors.append(f"{dir_name} 不是目录: {dir_path}")
        return errors

    def _check_dir_conflicts(self) -> list[str]:
        """检查目录路径冲突

        Returns:
            错误列表
        """
        errors: list[str] = []
        all_dirs = [
            ("inbox_dir", self.config.global_.inbox_dir),
            ("sorted_dir", self.config.global_.sorted_dir),
            ("unsorted_dir", self.config.global_.unsorted_dir),
            ("archive_dir", self.config.global_.archive_dir),
            ("misc_dir", self.config.global_.misc_dir),
        ]
        resolved_paths: dict[Path, list[str]] = {}
        for dir_name, dir_path in all_dirs:
            if dir_path is not None:
                resolved = dir_path.resolve()
                if resolved in resolved_paths:
                    resolved_paths[resolved].append(dir_name)
                else:
                    resolved_paths[resolved] = [dir_name]

        for resolved_path, dir_names in resolved_paths.items():
            if len(dir_names) > 1:
                errors.append(
                    f"目录路径冲突: {', '.join(dir_names)} 都指向同一路径 {resolved_path}"
                )
        return errors

    def initialize(self) -> ProcessorResult:
        """初始化处理

        验证文件任务配置的有效性。

        Returns:
            处理结果，成功或错误
        """
        errors: list[str] = []
        errors.extend(self._validate_inbox_dir())
        errors.extend(self._validate_other_dirs())
        errors.extend(self._check_dir_conflicts())

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
        config: TaskConfig,
    ) -> None:
        """初始化文件任务资源初始化器

        Args:
            config: 任务配置（用于访问GlobalConfig中的目录）
        """
        super().__init__("FileResourceInitializer")
        self.config = config
        self._logger = logging.getLogger(__name__)

    def initialize(self) -> ProcessorResult:
        """初始化处理

        确保目标目录存在且可写。

        Returns:
            处理结果，成功或错误
        """
        from ...infrastructure.filesystem.operations import (
            create_directory,
        )

        errors: list[str] = []

        # 需要初始化的目录（从GlobalConfig获取）
        target_dirs = {
            "sorted_dir": self.config.global_.sorted_dir,
            "unsorted_dir": self.config.global_.unsorted_dir,
            "archive_dir": self.config.global_.archive_dir,
            "misc_dir": self.config.global_.misc_dir,
        }

        for dir_name, dir_path in target_dirs.items():
            if dir_path is None:
                continue  # 跳过未设置的目录

            try:
                # 直接创建目录（静默创建，已存在时不抛出异常）
                create_directory(dir_path, parents=True)

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
