"""终结器实现

实现全局后处理功能，如生成报告、统计信息收集等。
终结器在所有文件处理完成后执行。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ...infrastructure.filesystem.operations import (
    create_directory,
    write_text_file,
)
from ..models import ProcessingContext, ProcessorResult, TaskReport
from ..processor import Finalizer


class ReportGenerator(Finalizer):
    """报告生成器

    生成处理结果报告。
    """

    def __init__(self, report_dir: Path, report: TaskReport):
        """初始化报告生成器

        Args:
            report_dir: 报告目录
            report: 任务报告
        """
        super().__init__("ReportGenerator")
        self.report_dir = report_dir
        self.report = report

    def process(self, ctx: ProcessingContext) -> ProcessorResult:
        """处理单个文件（终结器通常不处理单个文件）

        Args:
            ctx: 处理上下文

        Returns:
            处理结果
        """
        return ProcessorResult.skip("终结器不处理单个文件")

    def finalize(self) -> ProcessorResult:
        """执行全局终结处理

        Returns:
            处理结果
        """
        try:
            # 确保报告目录存在
            create_directory(self.report_dir, parents=True, exist_ok=True)

            # 生成 Markdown 报告
            report_file = self.report_dir / f"{self.report.task_name}_report.md"
            self._generate_markdown_report(report_file)

            # 生成 JSON 报告
            json_file = self.report_dir / f"{self.report.task_name}_report.json"
            self._generate_json_report(json_file)

            return ProcessorResult.success(
                f"报告生成成功: {report_file.name}, {json_file.name}",
                {"markdown_report": str(report_file), "json_report": str(json_file)},
            )

        except Exception as e:
            return ProcessorResult.error(f"报告生成失败: {str(e)}")

    def _generate_markdown_report(self, report_file: Path) -> None:
        """生成 Markdown 报告

        Args:
            report_file: 报告文件路径
        """
        content = f"# 任务报告: {self.report.task_name}\n\n"
        start_time_str = self.report.start_time.strftime("%Y-%m-%d %H:%M:%S")
        content += f"**开始时间**: {start_time_str}\n"
        content += (
            f"**结束时间**: {self.report.end_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
        content += f"**总耗时**: {self.report.duration_seconds:.2f} 秒\n\n"

        content += "## 统计信息\n\n"
        content += f"- **总文件数**: {self.report.total_files}\n"
        content += f"- **成功文件数**: {self.report.success_files}\n"
        content += f"- **失败文件数**: {self.report.error_files}\n"
        content += f"- **跳过文件数**: {self.report.skipped_files}\n"
        content += f"- **警告文件数**: {self.report.warning_files}\n"
        content += f"- **成功率**: {self.report.success_rate:.2%}\n"
        content += f"- **错误率**: {self.report.error_rate:.2%}\n\n"

        # 注意：详细结果已存储在数据库中，可通过 API 查询
        content += "## 说明\n\n"
        content += "详细结果已存储在数据库中，可通过 HTTP API 查询。\n"

        write_text_file(report_file, content)

    def _generate_json_report(self, json_file: Path) -> None:
        """生成 JSON 报告

        Args:
            json_file: JSON 文件路径
        """
        report_data = {
            "task_name": self.report.task_name,
            "start_time": self.report.start_time.isoformat(),
            "end_time": self.report.end_time.isoformat(),
            "duration_seconds": self.report.duration_seconds,
            "statistics": {
                "total_files": self.report.total_files,
                "success_files": self.report.success_files,
                "error_files": self.report.error_files,
                "skipped_files": self.report.skipped_files,
                "warning_files": self.report.warning_files,
                "success_rate": self.report.success_rate,
                "error_rate": self.report.error_rate,
            },
            "note": "详细结果已存储在数据库中，可通过 HTTP API 查询",
        }

        content = json.dumps(report_data, ensure_ascii=False, indent=2)
        write_text_file(json_file, content)


class StatisticsCollector(Finalizer):
    """统计信息收集器

    收集和汇总处理统计信息。
    """

    def __init__(self) -> None:
        """初始化统计信息收集器"""
        super().__init__("StatisticsCollector")
        self.stats: dict[str, Any] = {
            "file_types": {},
            "serial_ids": {},
            "errors": [],
            "warnings": [],
        }

    def process(self, ctx: ProcessingContext) -> ProcessorResult:
        """处理单个文件（终结器通常不处理单个文件）

        Args:
            ctx: 处理上下文

        Returns:
            处理结果
        """
        return ProcessorResult.skip("终结器不处理单个文件")

    def finalize(self) -> ProcessorResult:
        """执行全局终结处理

        Returns:
            处理结果
        """
        try:
            # 这里可以添加统计信息收集逻辑
            # 例如：分析文件类型分布、番号分布等

            return ProcessorResult.success("统计信息收集完成", {"stats": self.stats})

        except Exception as e:
            return ProcessorResult.error(f"统计信息收集失败: {str(e)}")
