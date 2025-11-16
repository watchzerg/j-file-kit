"""结构化日志

提供 JSON Lines 格式的结构化日志功能。
记录任务执行过程中的所有事件，便于后续分析和调试。
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from ...domain.models import FileItemResult
from ..filesystem.operations import (
    append_text_file,
    create_directory,
    path_exists,
    write_text_file,
)


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
        create_directory(self.log_dir, parents=True, exist_ok=True)

        # 创建日志文件（如果不存在）
        if not path_exists(self.log_file):
            write_text_file(self.log_file, "")

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

        append_text_file(
            self.log_file, json.dumps(log_entry, ensure_ascii=False) + "\n"
        )

    def info(self, message: str, data: dict[str, Any] | None = None) -> None:
        """记录信息日志"""
        self._write_log("INFO", message, data)

    def warning(self, message: str, data: dict[str, Any] | None = None) -> None:
        """记录警告日志"""
        self._write_log("WARNING", message, data)

    def error(self, message: str, data: dict[str, Any] | None = None) -> None:
        """记录错误日志"""
        self._write_log("ERROR", message, data)

    def debug(self, message: str, data: dict[str, Any] | None = None) -> None:
        """记录调试日志"""
        self._write_log("DEBUG", message, data)

    def log_item_result(self, result: FileItemResult) -> None:
        """记录item处理结果

        Args:
            result: 文件item处理结果
        """
        data = {
            "file_path": str(result.file_info.path),
            "file_type": result.context.file_type,
            "serial_id": str(result.context.serial_id)
            if result.context.serial_id
            else None,
            "success": result.success,
            "has_errors": result.has_errors,
            "has_warnings": result.has_warnings,
            "was_skipped": result.was_skipped,
            "duration_ms": result.total_duration_ms,
            "processor_count": len(result.processor_results),
        }

        if result.error_message:
            data["error_message"] = result.error_message

        self._write_log("ITEM_RESULT", f"处理文件: {result.file_info.path.name}", data)

    def log_task_start(self, scan_root: str) -> None:
        """记录任务开始"""
        data = {"scan_root": scan_root}
        self._write_log("TASK_START", f"开始任务: {self.task_name}", data)

    def log_task_end(self, report: Any) -> None:
        """记录任务结束"""
        data = {
            "total_items": report.total_items,
            "success_items": report.success_items,
            "error_items": report.error_items,
            "skipped_items": report.skipped_items,
            "warning_items": report.warning_items,
            "success_rate": report.success_rate,
            "duration_seconds": report.duration_seconds,
        }
        self._write_log("TASK_END", f"任务完成: {self.task_name}", data)
