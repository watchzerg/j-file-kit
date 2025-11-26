"""执行器实现

实现文件操作功能，如文件移动、删除等。
执行器根据PathEntryContext中的action决策执行相应的文件操作。

这些处理器位于服务层，可以依赖infrastructure层。
"""

from pathlib import Path

from j_file_kit.app.file_task.ports import FileProcessorRepository
from j_file_kit.infrastructure.filesystem.operations import (
    create_directory,
    delete_directory,
    delete_file,
    is_directory_empty,
    move_file_with_conflict_resolution,
)
from j_file_kit.shared.interfaces.processors.item import Executor
from j_file_kit.shared.models.contexts import PathEntryContext
from j_file_kit.shared.models.operations import OperationType
from j_file_kit.shared.models.path_entry import (
    PathEntryAction,
    PathEntryInfo,
    PathEntryType,
)
from j_file_kit.shared.models.results import ProcessorResult


class UnifiedFileExecutor(Executor):
    """统一文件执行器

    根据 PathEntryContext 中的 action 决策，执行相应的操作。
    只负责执行，不关心路径如何生成（路径由 analyzer 组装完成）。
    只处理文件类型的路径项。
    """

    def __init__(
        self,
        file_processor_repository: FileProcessorRepository | None = None,
    ) -> None:
        """初始化统一文件执行器

        Args:
            file_processor_repository: 文件处理操作仓储
        """
        super().__init__("UnifiedFileExecutor")
        self.file_processor_repository = file_processor_repository

    def process(self, ctx: PathEntryContext) -> ProcessorResult:  # type: ignore[override]
        """根据动作类型执行操作

        Args:
            ctx: 处理上下文

        Returns:
            执行结果
        """
        # 类型检查：只处理文件类型的项
        if ctx.item_type != PathEntryType.FILE:
            return ProcessorResult.skip("不是文件，跳过")

        if not ctx.action:
            return ProcessorResult.skip("未决策动作")

        if ctx.action in [
            PathEntryAction.MOVE_TO_SORTED,
            PathEntryAction.MOVE_TO_UNSORTED,
            PathEntryAction.MOVE_TO_ARCHIVE,
            PathEntryAction.MOVE_TO_MISC,
        ]:
            return self._move_file(ctx)
        elif ctx.action == PathEntryAction.DELETE:
            return self._delete(ctx)
        elif ctx.action == PathEntryAction.SKIP:
            return ProcessorResult.skip("跳过处理")
        else:
            return ProcessorResult.error(f"未知动作类型: {ctx.action}")

    def _move_file(self, ctx: PathEntryContext) -> ProcessorResult:
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

            # 直接创建目录（静默创建，已存在时不抛出异常）
            create_directory(ctx.target_path.parent, parents=True)

            # 保存原始路径（用于事务日志）
            old_path = ctx.item_info.path

            # 执行移动（自动处理路径冲突）
            final_path = move_file_with_conflict_resolution(old_path, ctx.target_path)

            # 更新上下文
            ctx.item_info = PathEntryInfo.from_path(final_path, PathEntryType.FILE)

            # 记录操作日志
            if self.file_processor_repository:
                self.file_processor_repository.create_operation(
                    OperationType.MOVE,
                    old_path,
                    final_path,
                    file_item_id=ctx.item_result_id,
                    file_type=ctx.file_type.value if ctx.file_type else None,
                    serial_id=str(ctx.serial_id) if ctx.serial_id else None,
                )

            description = ctx.action.description
            return ProcessorResult.success(
                f"移动到{description}: {final_path}",
                {"old_path": str(old_path), "new_path": str(final_path)},
            )

        except Exception as e:
            description = ctx.action.description
            return ProcessorResult.error(f"移动到{description}失败: {str(e)}")

    def _delete(self, ctx: PathEntryContext) -> ProcessorResult:
        """删除文件

        Args:
            ctx: 处理上下文

        Returns:
            执行结果
        """
        try:
            # 执行删除（文件不存在时静默成功）
            delete_file(ctx.item_info.path)

            # 记录操作日志
            if self.file_processor_repository:
                self.file_processor_repository.create_operation(
                    OperationType.DELETE,
                    ctx.item_info.path,
                    None,
                    file_item_id=ctx.item_result_id,
                    file_type=ctx.file_type.value if ctx.file_type else None,
                    serial_id=str(ctx.serial_id) if ctx.serial_id else None,
                )

            return ProcessorResult.success(f"文件删除成功: {ctx.item_info.path.name}")

        except Exception as e:
            return ProcessorResult.error(f"文件删除失败: {str(e)}")


class EmptyDirectoryExecutor(Executor):
    """空目录清理执行器

    在文件处理流程中同步清理空文件夹，利用自底向上遍历确保子目录先于父目录被处理。
    现在使用类型信息而不是运行时检查，提供更好的类型安全。

    设计意图：在遍历过程中同步清理空文件夹，利用自底向上遍历顺序确保空文件夹及时清理。
    目录操作不再记录到操作日志中。

    注意：这是目录处理执行器，不使用 File 前缀，因为其处理的是目录而非文件。
    """

    def __init__(
        self,
        scan_root: Path | None,
    ) -> None:
        """初始化空目录清理执行器

        Args:
            scan_root: 扫描根目录（该目录本身不会被删除）
        """
        super().__init__("EmptyDirectoryExecutor")
        self.scan_root = scan_root

    def process(self, ctx: PathEntryContext) -> ProcessorResult:  # type: ignore[override]
        """处理目录清理

        使用类型信息检查是否为目录，如果是目录且为空，则删除。

        Args:
            ctx: 处理上下文

        Returns:
            处理结果
        """
        # 使用类型信息检查而不是运行时检查
        if ctx.item_type != PathEntryType.DIRECTORY:
            return ProcessorResult.skip("不是目录，跳过")

        path = ctx.item_info.path

        # 检查目录是否为scan_root（完全匹配，保护扫描根目录不被删除）
        # 使用resolve()确保规范化路径比较，处理符号链接和相对路径
        if self.scan_root and path.resolve() == self.scan_root.resolve():
            return ProcessorResult.skip("扫描根目录，跳过")

        # 检查目录是否为空
        if not is_directory_empty(path):
            return ProcessorResult.skip("目录不为空，跳过")

        try:
            # 删除空目录
            delete_directory(path)

            return ProcessorResult.success(f"空目录删除成功: {path.name}")

        except Exception as e:
            # 目录清理是辅助操作，不应影响主流程（文件处理）
            # 返回错误但不抛出异常，不中断流程
            return ProcessorResult.error(f"空目录删除失败: {str(e)}")
