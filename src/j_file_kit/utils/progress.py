"""进度追踪模块

提供实时进度显示和统计信息维护。
"""

from __future__ import annotations

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..core.models import TaskStats


class ProgressTracker:
    """进度追踪器
    
    提供实时进度显示和统计信息维护。
    统计信息未来可能存入数据库或日志，但不与日志系统绑定。
    """
    
    def __init__(self, console: Console):
        """初始化进度追踪器
        
        Args:
            console: Rich 控制台实例
        """
        self.console = console
        self.stats = TaskStats()
        self.progress: Progress | None = None
        self.task = None
    
    def start_progress(self) -> None:
        """开始进度显示（未知总数模式）"""
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        )
        self.task = self.progress.add_task("处理文件", total=None)
        self.progress.start()
    
    def update_progress(self, current_file: str | None = None) -> None:
        """更新进度
        
        Args:
            current_file: 当前处理文件
        """
        self.stats.update(current_file)
        
        if self.progress and self.task is not None:
            self.progress.update(
                self.task,
                advance=1,
                description=f"已处理 {self.stats.processed_files} 个文件"
            )
    
    def stop_progress(self) -> None:
        """停止进度显示"""
        if self.progress:
            self.progress.stop()
            self.progress = None
            self.task = None

