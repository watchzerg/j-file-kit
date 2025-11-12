"""执行器模块

实现文件操作功能，如重命名、移动等。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..core.models import FileType, ProcessingContext, ProcessorResult
from ..core.processor import Executor
from ..utils.file_utils import resolve_unique_path


class FileRenamer(Executor):
    """文件重命名执行器

    根据分析结果执行文件重命名操作。
    """

    def __init__(self, transaction_log: Any = None) -> None:
        """初始化文件重命名器

        Args:
            transaction_log: 事务日志记录器
        """
        super().__init__("FileRenamer")
        self.transaction_log = transaction_log

    def process(self, ctx: ProcessingContext) -> ProcessorResult:
        """执行文件重命名

        Args:
            ctx: 处理上下文

        Returns:
            执行结果
        """
        try:
            # 检查是否需要重命名
            if not ctx.target_path or ctx.target_path == ctx.file_info.path:
                return ProcessorResult.skip("无需重命名")

            # 检查源文件是否存在
            if not ctx.file_info.path.exists():
                return ProcessorResult.error("源文件不存在")

            # 解析唯一路径（处理重名冲突）
            unique_path = resolve_unique_path(ctx.target_path)

            # 执行重命名
            ctx.file_info.path.rename(unique_path)

            # 记录事务日志
            if self.transaction_log:
                entry = self.transaction_log.create_rename_entry(
                    ctx.file_info.path,
                    unique_path,
                    {"serial_id": str(ctx.serial_id) if ctx.serial_id else None},
                )
                self.transaction_log.write_entry(entry)

            # 更新上下文中的文件信息
            ctx.file_info = ctx.file_info.model_copy(update={"path": unique_path})

            return ProcessorResult.success(
                f"文件重命名成功: {ctx.file_info.path.name} -> {unique_path.name}",
                {"old_path": str(ctx.file_info.path), "new_path": str(unique_path)},
            )

        except Exception as e:
            return ProcessorResult.error(f"文件重命名失败: {str(e)}")


class FileMover(Executor):
    """文件移动执行器

    根据分析结果执行文件移动操作。
    """

    def __init__(self, target_dir: Path, transaction_log: Any = None) -> None:
        """初始化文件移动器

        Args:
            target_dir: 目标目录
            transaction_log: 事务日志记录器
        """
        super().__init__("FileMover")
        self.target_dir = target_dir
        self.transaction_log = transaction_log

    def process(self, ctx: ProcessingContext) -> ProcessorResult:
        """执行文件移动

        Args:
            ctx: 处理上下文

        Returns:
            执行结果
        """
        try:
            # 检查是否需要移动
            if not self._should_move(ctx):
                return ProcessorResult.skip("无需移动")

            # 检查源文件是否存在
            if not ctx.file_info.path.exists():
                return ProcessorResult.error("源文件不存在")

            # 确保目标目录存在
            self.target_dir.mkdir(parents=True, exist_ok=True)

            # 生成目标路径
            target_path = self.target_dir / ctx.file_info.path.name
            unique_path = resolve_unique_path(target_path)

            # 执行移动
            ctx.file_info.path.rename(unique_path)

            # 记录事务日志
            if self.transaction_log:
                entry = self.transaction_log.create_move_entry(
                    ctx.file_info.path,
                    unique_path,
                    {
                        "file_type": ctx.file_type,
                        "serial_id": str(ctx.serial_id) if ctx.serial_id else None,
                    },
                )
                self.transaction_log.write_entry(entry)

            # 更新上下文中的文件信息
            ctx.file_info = ctx.file_info.model_copy(update={"path": unique_path})

            return ProcessorResult.success(
                f"文件移动成功: {ctx.file_info.path.name} -> {unique_path}",
                {"old_path": str(ctx.file_info.path), "new_path": str(unique_path)},
            )

        except Exception as e:
            return ProcessorResult.error(f"文件移动失败: {str(e)}")

    def _should_move(self, ctx: ProcessingContext) -> bool:
        """判断是否需要移动文件

        Args:
            ctx: 处理上下文

        Returns:
            是否需要移动
        """
        # 非视频/图片文件需要移动
        if ctx.file_type == FileType.OTHER:
            return True

        # 视频/图片文件但没有番号需要移动
        if ctx.file_type in [FileType.VIDEO, FileType.IMAGE] and not ctx.serial_id:
            return True

        return False


class FileDeleter(Executor):
    """文件删除执行器

    执行文件删除操作。
    """

    def __init__(self, transaction_log: Any = None) -> None:
        """初始化文件删除器

        Args:
            transaction_log: 事务日志记录器
        """
        super().__init__("FileDeleter")
        self.transaction_log = transaction_log

    def process(self, ctx: ProcessingContext) -> ProcessorResult:
        """执行文件删除

        Args:
            ctx: 处理上下文

        Returns:
            执行结果
        """
        try:
            # 检查源文件是否存在
            if not ctx.file_info.path.exists():
                return ProcessorResult.skip("文件不存在，无需删除")

            # 记录事务日志
            if self.transaction_log:
                entry = self.transaction_log.create_delete_entry(
                    ctx.file_info.path,
                    {
                        "file_type": ctx.file_type,
                        "serial_id": str(ctx.serial_id) if ctx.serial_id else None,
                    },
                )

            # 执行删除
            ctx.file_info.path.unlink()

            # 标记事务完成
            if self.transaction_log:
                self.transaction_log.write_entry(entry)

            return ProcessorResult.success(f"文件删除成功: {ctx.file_info.path.name}")

        except Exception as e:
            return ProcessorResult.error(f"文件删除失败: {str(e)}")


class DirectoryCreator(Executor):
    """目录创建执行器

    创建必要的目录结构。
    """

    def __init__(self, transaction_log: Any = None) -> None:
        """初始化目录创建器

        Args:
            transaction_log: 事务日志记录器
        """
        super().__init__("DirectoryCreator")
        self.transaction_log = transaction_log

    def process(self, ctx: ProcessingContext) -> ProcessorResult:
        """执行目录创建

        Args:
            ctx: 处理上下文

        Returns:
            执行结果
        """
        try:
            # 检查是否需要创建目录
            target_dir = ctx.custom_data.get("target_dir")
            if not target_dir:
                return ProcessorResult.skip("无需创建目录")

            target_path = Path(target_dir)

            # 记录事务日志
            if self.transaction_log:
                entry = self.transaction_log.create_dir_entry(
                    target_path, {"purpose": ctx.custom_data.get("purpose", "unknown")}
                )

            # 创建目录（exist_ok=True 处理目录已存在和并发情况）
            target_path.mkdir(parents=True, exist_ok=True)

            # 标记事务完成
            if self.transaction_log:
                self.transaction_log.write_entry(entry)

            return ProcessorResult.success(f"目录创建成功: {target_path}")

        except Exception as e:
            return ProcessorResult.error(f"目录创建失败: {str(e)}")
