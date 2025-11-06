"""结构化日志模块

提供 JSON Lines 格式的结构化日志功能。
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console

from ..core.models import TaskResult


class StructuredLogger:
    """结构化日志记录器

    提供 JSON Lines 格式的日志记录功能，便于后续分析和处理。
    """

    def __init__(self, log_dir: Path, task_name: str):
        """初始化日志记录器

        Args:
            log_dir: 日志目录
            task_name: 任务名称
        """
        self.log_dir = log_dir
        self.task_name = task_name
        self.task_id = str(uuid.uuid4())[:8]
        self.log_file = log_dir / f"{task_name}_{self.task_id}.jsonl"

        # 确保日志目录存在
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # 创建日志文件（如果不存在）
        self.log_file.touch(exist_ok=True)

        # Rich 控制台
        self.console = Console()

    def _write_log(
        self, level: str, message: str, data: dict[str, Any] | None = None
    ) -> None:
        """写入日志记录

        Args:
            level: 日志级别
            message: 日志消息
            data: 附加数据
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "task_id": self.task_id,
            "task_name": self.task_name,
            "level": level,
            "message": message,
            "data": data or {},
        }

        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    def info(self, message: str, data: dict[str, Any] | None = None) -> None:
        """记录信息日志"""
        self._write_log("INFO", message, data)
        self.console.print(f"[green]INFO[/green]: {message}")

    def warning(self, message: str, data: dict[str, Any] | None = None) -> None:
        """记录警告日志"""
        self._write_log("WARNING", message, data)
        self.console.print(f"[yellow]WARNING[/yellow]: {message}")

    def error(self, message: str, data: dict[str, Any] | None = None) -> None:
        """记录错误日志"""
        self._write_log("ERROR", message, data)
        self.console.print(f"[red]ERROR[/red]: {message}")

    def debug(self, message: str, data: dict[str, Any] | None = None) -> None:
        """记录调试日志"""
        self._write_log("DEBUG", message, data)
        self.console.print(f"[blue]DEBUG[/blue]: {message}")

    def log_file_result(self, result: TaskResult) -> None:
        """记录文件处理结果

        Args:
            result: 文件处理结果
        """
        data = {
            "file_path": str(result.file_info.path),
            "file_type": result.context.file_type,
            "serial_id": result.context.serial_id,
            "success": result.success,
            "has_errors": result.has_errors,
            "has_warnings": result.has_warnings,
            "was_skipped": result.was_skipped,
            "duration_ms": result.total_duration_ms,
            "processor_count": len(result.processor_results),
        }

        if result.error_message:
            data["error_message"] = result.error_message

        self._write_log("FILE_RESULT", f"处理文件: {result.file_info.path.name}", data)

    def log_task_start(self, scan_root: str) -> None:
        """记录任务开始"""
        data = {"scan_root": scan_root}
        self._write_log("TASK_START", f"开始任务: {self.task_name}", data)
        self.console.print(f"[bold green]开始任务: {self.task_name}[/bold green]")
        self.console.print(f"扫描目录: {scan_root}")
        self.console.print("流式处理模式")

    def log_task_end(self, report: Any) -> None:
        """记录任务结束"""
        data = {
            "total_files": report.total_files,
            "success_files": report.success_files,
            "error_files": report.error_files,
            "skipped_files": report.skipped_files,
            "warning_files": report.warning_files,
            "success_rate": report.success_rate,
            "duration_seconds": report.duration_seconds,
        }
        self._write_log("TASK_END", f"任务完成: {self.task_name}", data)
        self.console.print(f"[bold green]任务完成: {self.task_name}[/bold green]")
        self.console.print(f"总文件数: {report.total_files}")
        self.console.print(f"成功: {report.success_files}")
        self.console.print(f"失败: {report.error_files}")
        self.console.print(f"跳过: {report.skipped_files}")
        self.console.print(f"成功率: {report.success_rate:.2%}")
        self.console.print(f"耗时: {report.duration_seconds:.2f}秒")
