"""执行器实现

实现文件操作功能，如文件移动、删除等。
执行器根据FileContext中的action决策执行相应的文件操作。

这些处理器位于服务层，可以依赖infrastructure层。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ...infrastructure.filesystem.operations import (
    create_directory,
    delete_directory,
    delete_file,
    is_directory,
    is_directory_empty,
    move_file_with_conflict_resolution,
    path_exists,
)
from ...interfaces.processors import Executor
from ...models import FileAction, FileContext, ProcessorResult


class UnifiedFileExecutor(Executor):
    """统一文件执行器

    根据 FileContext 中的 action 决策，执行相应的操作。
    只负责执行，不关心路径如何生成（路径由 analyzer 组装完成）。
    """

    def __init__(self, operation_repository: Any = None) -> None:
        """初始化统一文件执行器

        Args:
            operation_repository: 操作记录仓储
        """
        super().__init__("UnifiedFileExecutor")
        self.operation_repository = operation_repository

    def process(self, ctx: FileContext) -> ProcessorResult:  # type: ignore[override]
        """根据动作类型执行操作

        Args:
            ctx: 处理上下文

        Returns:
            执行结果
        """
        if not ctx.action:
            return ProcessorResult.skip("未决策动作")

        if ctx.action in [
            FileAction.MOVE_TO_ORGANIZED,
            FileAction.MOVE_TO_UNORGANIZED,
            FileAction.MOVE_TO_ARCHIVE,
            FileAction.MOVE_TO_MISC,
        ]:
            return self._move_file(ctx)
        elif ctx.action == FileAction.DELETE:
            return self._delete(ctx)
        elif ctx.action == FileAction.SKIP:
            return ProcessorResult.skip("跳过处理")
        else:
            return ProcessorResult.error(f"未知动作类型: {ctx.action}")

    def _move_file(self, ctx: FileContext) -> ProcessorResult:
        """移动文件（统一方法）

        所有移动操作都使用此方法，完全无脑执行。

        Args:
            ctx: 处理上下文

        Returns:
            执行结果
        """
        if not ctx.action:
            return ProcessorResult.error("动作未设置")

        try:
            if not ctx.target_path:
                return ProcessorResult.error("目标路径未设置")

            # 检查源文件是否存在
            if not path_exists(ctx.file_info.path):
                return ProcessorResult.error("源文件不存在")

            # 创建目录（如果不存在）
            create_directory(ctx.target_path.parent, parents=True, exist_ok=True)

            # 保存原始路径（用于事务日志）
            old_path = ctx.file_info.path

            # 执行移动（自动处理路径冲突）
            final_path = move_file_with_conflict_resolution(old_path, ctx.target_path)

            # 更新上下文
            ctx.file_info = ctx.file_info.model_copy(update={"path": final_path})

            # 构建日志元数据
            log_metadata = {
                "action": ctx.action.value,
                "file_type": ctx.file_type.value if ctx.file_type else None,
            }
            # organized 操作额外记录 serial_id
            if ctx.action == FileAction.MOVE_TO_ORGANIZED and ctx.serial_id:
                log_metadata["serial_id"] = str(ctx.serial_id)

            # 记录操作日志
            if self.operation_repository:
                self.operation_repository.log_move(
                    old_path,
                    final_path,
                    log_metadata,
                    item_result_id=ctx.item_result_id,
                )

            description = ctx.action.description
            return ProcessorResult.success(
                f"移动到{description}: {final_path}",
                {"old_path": str(old_path), "new_path": str(final_path)},
            )

        except Exception as e:
            description = ctx.action.description
            return ProcessorResult.error(f"移动到{description}失败: {str(e)}")

    def _delete(self, ctx: FileContext) -> ProcessorResult:
        """删除文件

        Args:
            ctx: 处理上下文

        Returns:
            执行结果
        """
        try:
            # 执行删除（文件不存在时静默成功）
            delete_file(ctx.file_info.path, missing_ok=True)

            # 记录操作日志
            if self.operation_repository:
                self.operation_repository.log_delete(
                    ctx.file_info.path,
                    {
                        "action": "delete",
                        "file_type": ctx.file_type.value if ctx.file_type else None,
                    },
                    item_result_id=ctx.item_result_id,
                )

            return ProcessorResult.success(f"文件删除成功: {ctx.file_info.path.name}")

        except Exception as e:
            return ProcessorResult.error(f"文件删除失败: {str(e)}")


class FileEmptyDirectoryExecutor(Executor):
    """空目录清理执行器

    在文件处理流程中同步清理空文件夹，利用自底向上遍历确保子目录先于父目录被处理。
    通过路径判断而不是修改FileContext类型，保持类型系统简单。
    设计意图：在遍历过程中同步清理空文件夹，利用自底向上遍历顺序确保空文件夹及时清理。
    """

    def __init__(
        self, scan_root: Path | None, operation_repository: Any | None = None
    ) -> None:
        """初始化空目录清理执行器

        Args:
            scan_root: 扫描根目录（该目录本身不会被删除）
            operation_repository: 操作记录仓储
        """
        super().__init__("FileEmptyDirectoryExecutor")
        self.scan_root = scan_root
        self.operation_repository = operation_repository

    def process(self, ctx: FileContext) -> ProcessorResult:  # type: ignore[override]
        """处理目录清理

        通过路径判断是否为目录，如果是目录且为空，则删除。
        目录清理是轻量级操作，不需要完整的上下文信息，因此通过路径判断而不是修改FileContext类型。

        Args:
            ctx: 处理上下文（通过ctx.file_info.path获取路径）

        Returns:
            处理结果
        """
        path = ctx.file_info.path

        # 检查路径是否为目录（通过路径判断，不修改FileContext类型）
        if not is_directory(path):
            return ProcessorResult.skip("不是目录，跳过")

        # 检查目录是否为scan_root（完全匹配，保护扫描根目录不被删除）
        # 使用resolve()确保规范化路径比较，处理符号链接和相对路径
        if self.scan_root and path.resolve() == self.scan_root.resolve():
            return ProcessorResult.skip("扫描根目录，跳过")

        # 检查目录是否为空
        if not is_directory_empty(path):
            return ProcessorResult.skip("目录不为空，跳过")

        try:
            # 删除空目录
            delete_directory(path, missing_ok=True)

            # 记录操作日志
            if self.operation_repository:
                self.operation_repository.log_delete_dir(
                    path,
                    {"action": "delete_empty_dir"},
                    item_result_id=ctx.item_result_id,
                )

            return ProcessorResult.success(f"空目录删除成功: {path.name}")

        except Exception as e:
            # 目录清理是辅助操作，不应影响主流程（文件处理）
            # 返回错误但不抛出异常，不中断流程
            return ProcessorResult.error(f"空目录删除失败: {str(e)}")
