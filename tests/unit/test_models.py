"""数据模型单元测试

测试 Pydantic 模型的验证和序列化。
"""

import pytest
from datetime import datetime
from pathlib import Path

from jfk.core.models import (
    FileInfo, ProcessingContext, ProcessorResult, TaskResult, TaskReport,
    ProcessorStatus, FileType, TaskStats
)


class TestFileInfo:
    """测试 FileInfo 模型"""
    
    def test_file_info_creation(self):
        """测试 FileInfo 创建"""
        path = Path("/test/file.mp4")
        file_info = FileInfo(
            path=path,
            name="file",
            suffix=".mp4"
        )
        
        assert file_info.path == path
        assert file_info.name == "file"
        assert file_info.suffix == ".mp4"
    
    def test_file_info_from_path(self):
        """测试从路径创建 FileInfo"""
        path = Path("/test/video_file.mp4")
        file_info = FileInfo.from_path(path)
        
        assert file_info.path == path
        assert file_info.name == "video_file"
        assert file_info.suffix == ".mp4"
    
    def test_file_info_validation(self):
        """测试 FileInfo 验证"""
        # 测试必需字段
        with pytest.raises(ValueError):
            FileInfo(path=Path("/test"), name="", suffix=".mp4")
        
        # 测试路径类型
        with pytest.raises(ValueError):
            FileInfo(path="/test/file.mp4", name="file", suffix=".mp4")


class TestProcessingContext:
    """测试 ProcessingContext 模型"""
    
    def test_processing_context_creation(self):
        """测试 ProcessingContext 创建"""
        file_info = FileInfo.from_path(Path("/test/file.mp4"))
        ctx = ProcessingContext(file_info=file_info)
        
        assert ctx.file_info == file_info
        assert ctx.file_type is None
        assert ctx.serial_id is None
        assert ctx.target_path is None
        assert ctx.skip_remaining is False
        assert ctx.custom_data == {}
    
    def test_processing_context_with_data(self):
        """测试带数据的 ProcessingContext"""
        file_info = FileInfo.from_path(Path("/test/file.mp4"))
        ctx = ProcessingContext(
            file_info=file_info,
            file_type=FileType.VIDEO,
            serial_id="ABC-001",
            target_path=Path("/target/file.mp4"),
            skip_remaining=True,
            custom_data={"key": "value"}
        )
        
        assert ctx.file_type == FileType.VIDEO
        assert ctx.serial_id == "ABC-001"
        assert ctx.target_path == Path("/target/file.mp4")
        assert ctx.skip_remaining is True
        assert ctx.custom_data == {"key": "value"}


class TestProcessorResult:
    """测试 ProcessorResult 模型"""
    
    def test_processor_result_creation(self):
        """测试 ProcessorResult 创建"""
        result = ProcessorResult(
            status=ProcessorStatus.SUCCESS,
            message="处理成功",
            duration_ms=100.5,
            data={"key": "value"}
        )
        
        assert result.status == ProcessorStatus.SUCCESS
        assert result.message == "处理成功"
        assert result.duration_ms == 100.5
        assert result.data == {"key": "value"}
    
    def test_processor_result_factory_methods(self):
        """测试 ProcessorResult 工厂方法"""
        # 测试成功结果
        result = ProcessorResult.success("操作成功", {"id": 123})
        assert result.status == ProcessorStatus.SUCCESS
        assert result.message == "操作成功"
        assert result.data == {"id": 123}
        
        # 测试错误结果
        result = ProcessorResult.error("操作失败", {"error": "test"})
        assert result.status == ProcessorStatus.ERROR
        assert result.message == "操作失败"
        assert result.data == {"error": "test"}
        
        # 测试跳过结果
        result = ProcessorResult.skip("跳过处理")
        assert result.status == ProcessorStatus.SKIP
        assert result.message == "跳过处理"
        
        # 测试警告结果
        result = ProcessorResult.warning("警告信息", {"warning": "test"})
        assert result.status == ProcessorStatus.WARNING
        assert result.message == "警告信息"
        assert result.data == {"warning": "test"}


class TestTaskResult:
    """测试 TaskResult 模型"""
    
    def test_task_result_creation(self):
        """测试 TaskResult 创建"""
        file_info = FileInfo.from_path(Path("/test/file.mp4"))
        ctx = ProcessingContext(file_info=file_info)
        
        result = TaskResult(
            file_info=file_info,
            context=ctx,
            processor_results=[],
            total_duration_ms=100.0,
            success=True,
            error_message=None
        )
        
        assert result.file_info == file_info
        assert result.context == ctx
        assert result.processor_results == []
        assert result.total_duration_ms == 100.0
        assert result.success is True
        assert result.error_message is None
    
    def test_task_result_properties(self):
        """测试 TaskResult 属性"""
        file_info = FileInfo.from_path(Path("/test/file.mp4"))
        ctx = ProcessingContext(file_info=file_info)
        
        # 测试成功结果
        success_result = ProcessorResult.success("成功")
        error_result = ProcessorResult.error("错误")
        warning_result = ProcessorResult.warning("警告")
        skip_result = ProcessorResult.skip("跳过")
        
        # 测试有错误的情况
        result = TaskResult(
            file_info=file_info,
            context=ctx,
            processor_results=[error_result],
            total_duration_ms=100.0,
            success=False,
            error_message="处理失败"
        )
        
        assert result.has_errors is True
        assert result.has_warnings is False
        assert result.was_skipped is False
        
        # 测试有警告的情况
        result = TaskResult(
            file_info=file_info,
            context=ctx,
            processor_results=[warning_result],
            total_duration_ms=100.0,
            success=True,
            error_message=None
        )
        
        assert result.has_errors is False
        assert result.has_warnings is True
        assert result.was_skipped is False
        
        # 测试跳过的情况
        result = TaskResult(
            file_info=file_info,
            context=ctx,
            processor_results=[skip_result],
            total_duration_ms=100.0,
            success=True,
            error_message=None
        )
        
        assert result.has_errors is False
        assert result.has_warnings is False
        assert result.was_skipped is True


class TestTaskReport:
    """测试 TaskReport 模型"""
    
    def test_task_report_creation(self):
        """测试 TaskReport 创建"""
        start_time = datetime.now()
        report = TaskReport(
            task_name="test_task",
            start_time=start_time,
            end_time=start_time
        )
        
        assert report.task_name == "test_task"
        assert report.start_time == start_time
        assert report.end_time == start_time
        assert report.total_files == 0
        assert report.success_files == 0
        assert report.error_files == 0
    
    def test_task_report_properties(self):
        """测试 TaskReport 属性"""
        start_time = datetime.now()
        end_time = datetime.now()
        
        report = TaskReport(
            task_name="test_task",
            start_time=start_time,
            end_time=end_time,
            total_files=100,
            success_files=80,
            error_files=20
        )
        
        assert report.success_rate == 0.8
        assert report.error_rate == 0.2
        assert report.duration_seconds > 0
    
    def test_task_report_add_result(self):
        """测试 TaskReport 添加结果"""
        start_time = datetime.now()
        report = TaskReport(
            task_name="test_task",
            start_time=start_time,
            end_time=start_time
        )
        
        # 创建测试结果
        file_info = FileInfo.from_path(Path("/test/file.mp4"))
        ctx = ProcessingContext(file_info=file_info)
        
        success_result = TaskResult(
            file_info=file_info,
            context=ctx,
            processor_results=[ProcessorResult.success("成功")],
            total_duration_ms=100.0,
            success=True,
            error_message=None
        )
        
        # 添加结果
        report.add_result(success_result)
        
        assert report.total_files == 1
        assert report.success_files == 1
        assert report.error_files == 0
        assert report.skipped_files == 0
        assert report.warning_files == 0


class TestTaskStats:
    """测试 TaskStats 模型"""
    
    def test_task_stats_creation(self):
        """测试 TaskStats 创建"""
        stats = TaskStats()
        
        assert stats.processed_files == 0
        assert stats.current_file is None
        assert stats.start_time is not None
        assert stats.last_update is not None
    
    def test_task_stats_update(self):
        """测试 TaskStats 更新"""
        stats = TaskStats()
        
        # 更新统计信息
        stats.update("test_file.mp4")
        
        assert stats.processed_files == 1
        assert stats.current_file == "test_file.mp4"
        assert stats.elapsed_seconds >= 0
    
    def test_task_stats_elapsed_seconds(self):
        """测试 TaskStats 耗时计算"""
        stats = TaskStats()
        
        # 等待一小段时间
        import time
        time.sleep(0.1)
        
        assert stats.elapsed_seconds >= 0.1


class TestEnums:
    """测试枚举类型"""
    
    def test_processor_status_enum(self):
        """测试 ProcessorStatus 枚举"""
        assert ProcessorStatus.SUCCESS == "success"
        assert ProcessorStatus.ERROR == "error"
        assert ProcessorStatus.SKIP == "skip"
        assert ProcessorStatus.WARNING == "warning"
    
    def test_file_type_enum(self):
        """测试 FileType 枚举"""
        assert FileType.VIDEO == "video"
        assert FileType.IMAGE == "image"
        assert FileType.OTHER == "other"
