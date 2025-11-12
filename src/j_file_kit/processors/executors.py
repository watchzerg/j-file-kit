"""执行器模块

实现文件操作功能，如重命名、移动等。
"""

from __future__ import annotations

from typing import Any

from ..core.models import FileAction, ProcessingContext, ProcessorResult
from ..core.processor import Executor
from ..utils.file_utils import resolve_unique_path


class UnifiedFileExecutor(Executor):
    """统一文件执行器

    根据 ProcessingContext 中的 action 决策，执行相应的操作。
    """

    def __init__(self, transaction_log: Any = None) -> None:
        """初始化统一文件执行器

        Args:
            transaction_log: 事务日志记录器
        """
        super().__init__("UnifiedFileExecutor")
        self.transaction_log = transaction_log

    def process(self, ctx: ProcessingContext) -> ProcessorResult:
        """根据动作类型执行操作

        Args:
            ctx: 处理上下文

        Returns:
            执行结果
        """
        if not ctx.action:
            return ProcessorResult.skip("未决策动作")

        if ctx.action == FileAction.MOVE_TO_ORGANIZED:
            return self._move_to_organized(ctx)
        elif ctx.action == FileAction.MOVE_TO_UNORGANIZED:
            return self._move_to_static_dir(ctx)
        elif ctx.action == FileAction.MOVE_TO_ARCHIVE:
            return self._move_to_static_dir(ctx)
        elif ctx.action == FileAction.MOVE_TO_MISC:
            return self._move_to_static_dir(ctx)
        elif ctx.action == FileAction.DELETE:
            return self._delete(ctx)
        elif ctx.action == FileAction.SKIP:
            return ProcessorResult.skip("跳过处理")
        else:
            return ProcessorResult.error(f"未知动作类型: {ctx.action}")

    def _move_to_organized(self, ctx: ProcessingContext) -> ProcessorResult:
        """移动到整理目录（需要创建动态目录结构）

        Args:
            ctx: 处理上下文

        Returns:
            执行结果
        """
        try:
            if not ctx.target_dir:
                return ProcessorResult.error("目标路径未设置")

            # 检查源文件是否存在
            if not ctx.file_info.path.exists():
                return ProcessorResult.error("源文件不存在")

            # 直接创建目录（不需要检查是否存在）
            ctx.target_dir.parent.mkdir(parents=True, exist_ok=True)

            # 处理重名冲突
            unique_path = resolve_unique_path(ctx.target_dir)

            # 保存原始路径（用于事务日志）
            old_path = ctx.file_info.path

            # 执行移动
            old_path.rename(unique_path)

            # 更新上下文
            ctx.file_info = ctx.file_info.model_copy(update={"path": unique_path})

            # 记录事务日志
            if self.transaction_log:
                self.transaction_log.log_move(
                    old_path,
                    unique_path,
                    {
                        "action": FileAction.MOVE_TO_ORGANIZED.value,
                        "serial_id": str(ctx.serial_id) if ctx.serial_id else None,
                        "file_type": ctx.file_type.value if ctx.file_type else None,
                    },
                )

            return ProcessorResult.success(
                f"移动到整理目录: {unique_path}",
                {"old_path": str(old_path), "new_path": str(unique_path)},
            )

        except Exception as e:
            return ProcessorResult.error(f"移动到整理目录失败: {str(e)}")

    def _move_to_static_dir(self, ctx: ProcessingContext) -> ProcessorResult:
        """移动到静态目录（通用方法）

        Args:
            ctx: 处理上下文

        Returns:
            执行结果
        """
        if not ctx.action:
            return ProcessorResult.error("动作未设置")

        try:
            if not ctx.target_dir:
                return ProcessorResult.error("目标目录未设置")

            # 检查源文件是否存在
            if not ctx.file_info.path.exists():
                return ProcessorResult.error("源文件不存在")

            # 生成目标路径
            target_path = ctx.target_dir / ctx.file_info.path.name
            unique_path = resolve_unique_path(target_path)

            # 保存原始路径（用于事务日志）
            old_path = ctx.file_info.path

            # 执行移动
            old_path.rename(unique_path)

            # 更新上下文
            ctx.file_info = ctx.file_info.model_copy(update={"path": unique_path})

            # 记录事务日志
            if self.transaction_log:
                self.transaction_log.log_move(
                    old_path,
                    unique_path,
                    {
                        "action": ctx.action.value,
                        "file_type": ctx.file_type.value if ctx.file_type else None,
                    },
                )

            description = ctx.action.description
            return ProcessorResult.success(
                f"移动到{description}: {unique_path}",
                {"old_path": str(old_path), "new_path": str(unique_path)},
            )

        except Exception as e:
            description = ctx.action.description if ctx.action else "目标目录"
            return ProcessorResult.error(f"移动到{description}失败: {str(e)}")

    def _delete(self, ctx: ProcessingContext) -> ProcessorResult:
        """删除文件

        Args:
            ctx: 处理上下文

        Returns:
            执行结果
        """
        try:
            # 执行删除（文件不存在时静默成功）
            ctx.file_info.path.unlink(missing_ok=True)

            # 记录事务日志
            if self.transaction_log:
                self.transaction_log.log_delete(
                    ctx.file_info.path,
                    {
                        "action": "delete",
                        "file_type": ctx.file_type.value if ctx.file_type else None,
                    },
                )

            return ProcessorResult.success(f"文件删除成功: {ctx.file_info.path.name}")

        except Exception as e:
            return ProcessorResult.error(f"文件删除失败: {str(e)}")
