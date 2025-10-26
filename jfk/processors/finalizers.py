"""终结器模块

实现全局后处理功能，如清理空目录、生成报告等。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..core.models import ProcessingContext, ProcessorResult, TaskReport
from ..core.processor import Finalizer
from ..utils.file_utils import find_empty_dirs, safe_remove_empty_dirs


class EmptyDirCleaner(Finalizer):
    """空目录清理器
    
    清理处理过程中产生的空目录。
    """
    
    def __init__(self, root_path: Path, transaction_log=None):
        """初始化空目录清理器
        
        Args:
            root_path: 根目录路径
            transaction_log: 事务日志记录器
        """
        super().__init__("EmptyDirCleaner")
        self.root_path = root_path
        self.transaction_log = transaction_log
    
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
            # 查找空目录
            empty_dirs = find_empty_dirs(self.root_path)
            
            if not empty_dirs:
                return ProcessorResult.success("没有发现空目录")
            
            # 记录事务日志
            if self.transaction_log:
                for dir_path in empty_dirs:
                    self.transaction_log.log_delete_dir(
                        dir_path,
                        {"purpose": "cleanup_empty_dir"}
                    )
            
            # 删除空目录
            removed_dirs = safe_remove_empty_dirs(empty_dirs)
            
            # 标记事务完成
            if self.transaction_log:
                for dir_path in removed_dirs:
                    # 这里需要根据实际的事务ID来标记完成
                    pass
            
            return ProcessorResult.success(
                f"清理了 {len(removed_dirs)} 个空目录",
                {"removed_dirs": [str(d) for d in removed_dirs]}
            )
            
        except Exception as e:
            return ProcessorResult.error(f"空目录清理失败: {str(e)}")


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
            self.report_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成 Markdown 报告
            report_file = self.report_dir / f"{self.report.task_name}_report.md"
            self._generate_markdown_report(report_file)
            
            # 生成 JSON 报告
            json_file = self.report_dir / f"{self.report.task_name}_report.json"
            self._generate_json_report(json_file)
            
            return ProcessorResult.success(
                f"报告生成成功: {report_file.name}, {json_file.name}",
                {"markdown_report": str(report_file), "json_report": str(json_file)}
            )
            
        except Exception as e:
            return ProcessorResult.error(f"报告生成失败: {str(e)}")
    
    def _generate_markdown_report(self, report_file: Path) -> None:
        """生成 Markdown 报告
        
        Args:
            report_file: 报告文件路径
        """
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(f"# 任务报告: {self.report.task_name}\n\n")
            f.write(f"**开始时间**: {self.report.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**结束时间**: {self.report.end_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**总耗时**: {self.report.duration_seconds:.2f} 秒\n\n")
            
            f.write("## 统计信息\n\n")
            f.write(f"- **总文件数**: {self.report.total_files}\n")
            f.write(f"- **成功文件数**: {self.report.success_files}\n")
            f.write(f"- **失败文件数**: {self.report.error_files}\n")
            f.write(f"- **跳过文件数**: {self.report.skipped_files}\n")
            f.write(f"- **警告文件数**: {self.report.warning_files}\n")
            f.write(f"- **成功率**: {self.report.success_rate:.2%}\n")
            f.write(f"- **错误率**: {self.report.error_rate:.2%}\n\n")
            
            # 详细结果
            if self.report.results:
                f.write("## 详细结果\n\n")
                f.write("| 文件 | 状态 | 耗时(ms) | 消息 |\n")
                f.write("|------|------|----------|------|\n")
                
                for result in self.report.results:
                    status = "✅ 成功" if result.success else "❌ 失败"
                    if result.was_skipped:
                        status = "⏭️ 跳过"
                    elif result.has_warnings:
                        status = "⚠️ 警告"
                    
                    f.write(f"| {result.file_info.path.name} | {status} | {result.total_duration_ms:.1f} | {result.error_message or 'OK'} |\n")
    
    def _generate_json_report(self, json_file: Path) -> None:
        """生成 JSON 报告
        
        Args:
            json_file: JSON 文件路径
        """
        import json
        
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
                "error_rate": self.report.error_rate
            },
            "results": [
                {
                    "file_path": str(result.file_info.path),
                    "file_name": result.file_info.name,
                    "file_type": result.context.file_type,
                    "serial_id": result.context.serial_id,
                    "success": result.success,
                    "has_errors": result.has_errors,
                    "has_warnings": result.has_warnings,
                    "was_skipped": result.was_skipped,
                    "duration_ms": result.total_duration_ms,
                    "error_message": result.error_message,
                    "processor_count": len(result.processor_results)
                }
                for result in self.report.results
            ]
        }
        
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)


class StatisticsCollector(Finalizer):
    """统计信息收集器
    
    收集和汇总处理统计信息。
    """
    
    def __init__(self):
        """初始化统计信息收集器"""
        super().__init__("StatisticsCollector")
        self.stats = {
            "file_types": {},
            "serial_ids": {},
            "errors": [],
            "warnings": []
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
            
            return ProcessorResult.success(
                "统计信息收集完成",
                {"stats": self.stats}
            )
            
        except Exception as e:
            return ProcessorResult.error(f"统计信息收集失败: {str(e)}")


class CleanupFinalizer(Finalizer):
    """清理终结器
    
    执行各种清理操作。
    """
    
    def __init__(self, cleanup_actions: list[callable]):
        """初始化清理终结器
        
        Args:
            cleanup_actions: 清理操作列表
        """
        super().__init__("CleanupFinalizer")
        self.cleanup_actions = cleanup_actions
    
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
            executed_actions = []
            
            for action in self.cleanup_actions:
                try:
                    action()
                    executed_actions.append(action.__name__)
                except Exception as e:
                    # 记录清理操作失败，但继续执行其他操作
                    print(f"清理操作 {action.__name__} 失败: {e}")
            
            return ProcessorResult.success(
                f"执行了 {len(executed_actions)} 个清理操作",
                {"executed_actions": executed_actions}
            )
            
        except Exception as e:
            return ProcessorResult.error(f"清理操作失败: {str(e)}")
