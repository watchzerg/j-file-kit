"""初始化器实现

实现任务前置处理功能，如状态更新、配置验证、资源初始化等。
初始化器在任务开始执行前调用，如果初始化失败，将阻止任务继续执行。

这些处理器位于服务层，可以依赖infrastructure层。
"""

import logging
import os

from ...infrastructure.filesystem.operations import create_directory
from ...interfaces.processors import Initializer
from ...interfaces.repositories import TaskRepository
from ...models import ProcessorResult, TaskStatus
from ...models.config import AppConfig
from ...utils.config_utils import validate_global_config


class TaskStatusInitializer(Initializer):
    """任务状态初始化器

    更新任务状态为 RUNNING。
    这是任务执行前的第一个初始化步骤，确保任务状态正确更新。

    设计意图：
    - 在任务开始执行前更新状态，确保状态一致性
    - 如果状态更新失败，任务不应继续执行

    注意：这是任务级别的状态初始化器，不特定于文件处理任务。
    """

    def __init__(
        self,
        task_id: int,
        task_repository: TaskRepository,
    ) -> None:
        """初始化任务状态初始化器

        Args:
            task_id: 任务ID
            task_repository: 任务仓储实例
        """
        super().__init__("TaskStatusInitializer")
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


class TaskConfigValidatorInitializer(Initializer):
    """任务配置验证初始化器

    验证任务配置的有效性，仅验证配置本身。
    确保配置正确后才能开始执行任务。

    设计意图：
    - 在任务执行前验证配置，避免执行过程中才发现配置错误
    - 验证项包括：配置项是否设置、路径格式是否有效、路径不冲突
    - 不检查目录存在性，目录存在性检查和创建由 TaskResourceInitializer 负责

    注意：这是任务级别的配置验证初始化器，不特定于文件处理任务。
    """

    def __init__(
        self,
        config: AppConfig,
    ) -> None:
        """初始化任务配置验证初始化器

        Args:
            config: 应用配置
        """
        super().__init__("TaskConfigValidatorInitializer")
        self.config = config
        self._logger = logging.getLogger(__name__)

    def initialize(self) -> ProcessorResult:
        """初始化处理

        验证任务配置的有效性（仅配置本身，不检查目录存在性）。
        使用统一的验证函数，避免代码重复。

        Returns:
            处理结果，成功或错误
        """
        errors = validate_global_config(self.config.global_)

        if errors:
            error_msg = "配置验证失败:\n" + "\n".join(f"  - {e}" for e in errors)
            self._logger.error(error_msg)
            return ProcessorResult.error(error_msg)

        self._logger.info("配置验证通过")
        return ProcessorResult.success("配置验证通过")


class TaskResourceInitializer(Initializer):
    """任务资源初始化器

    确保任务所需的资源（目录）已准备就绪。
    负责目录存在性检查和静默创建，验证目录权限。

    设计意图：
    - 在任务执行前确保所有必需的目录已准备好
    - 如果目录创建或权限验证失败，任务不应继续执行
    - 目录存在性检查和创建是资源初始化的职责，而非配置验证

    注意：这是任务级别的资源初始化器，不特定于文件处理任务。
    """

    def __init__(
        self,
        config: AppConfig,
    ) -> None:
        """初始化任务资源初始化器

        Args:
            config: 应用配置（用于访问GlobalConfig中的目录）
        """
        super().__init__("TaskResourceInitializer")
        self.config = config
        self._logger = logging.getLogger(__name__)

    def initialize(self) -> ProcessorResult:
        """初始化处理

        检查目录存在性，不存在则静默创建；验证目录权限。

        Returns:
            处理结果，成功或错误
        """
        errors: list[str] = []

        # 需要初始化的目录（从GlobalConfig获取，包括inbox_dir）
        all_dirs = {
            "inbox_dir": self.config.global_.inbox_dir,
            "sorted_dir": self.config.global_.sorted_dir,
            "unsorted_dir": self.config.global_.unsorted_dir,
            "archive_dir": self.config.global_.archive_dir,
            "misc_dir": self.config.global_.misc_dir,
        }

        for dir_name, dir_path in all_dirs.items():
            if dir_path is None:
                continue  # 跳过未设置的目录

            try:
                # 检查目录是否存在，不存在则静默创建
                if not dir_path.exists():
                    create_directory(dir_path, parents=True)
                    self._logger.info(f"已创建目录: {dir_name}={dir_path}")
                elif not dir_path.is_dir():
                    errors.append(f"{dir_name} 路径不是目录: {dir_path}")
                    continue

                # 验证目录权限
                # inbox_dir 需要可读权限，其他目录需要可写权限
                if dir_name == "inbox_dir":
                    if not os.access(dir_path, os.R_OK):
                        errors.append(f"{dir_name} 不可读: {dir_path}")
                else:
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
