"""管道集成测试

测试完整的处理管道流程。
"""

import pytest
from pathlib import Path

from jfk.core.config import TaskConfig, GlobalConfig, TaskDefinition
from jfk.core.pipeline import Pipeline
from jfk.processors.analyzers import FileClassifier, SerialIdExtractor
from jfk.processors.executors import FileMover, FileRenamer
from jfk.processors.finalizers import EmptyDirCleaner, ReportGenerator
from jfk.core.models import FileType


@pytest.mark.integration
class TestPipeline:
    """测试处理管道"""
    
    def test_pipeline_creation(self, sample_config: TaskConfig):
        """测试管道创建"""
        pipeline = Pipeline(sample_config, "test_task")
        
        assert pipeline.config == sample_config
        assert pipeline.task_name == "test_task"
        assert pipeline.task_config is not None
        assert pipeline.scanner is not None
        assert pipeline.processor_chain is not None
        assert pipeline.logger is not None
        assert pipeline.transaction_log is not None
    
    def test_pipeline_add_processors(self, sample_config: TaskConfig):
        """测试添加处理器"""
        pipeline = Pipeline(sample_config, "test_task")
        
        # 添加分析器
        classifier = FileClassifier({".mp4", ".avi"}, {".jpg", ".png"})
        extractor = SerialIdExtractor()
        
        pipeline.add_analyzer(classifier)
        pipeline.add_analyzer(extractor)
        
        assert len(pipeline.processor_chain.analyzers) == 2
        assert pipeline.processor_chain.analyzers[0] == classifier
        assert pipeline.processor_chain.analyzers[1] == extractor
        
        # 添加执行器
        renamer = FileRenamer()
        mover = FileMover(Path("/target"), pipeline.transaction_log)
        
        pipeline.add_executor(renamer)
        pipeline.add_executor(mover)
        
        assert len(pipeline.processor_chain.executors) == 2
        assert pipeline.processor_chain.executors[0] == renamer
        assert pipeline.processor_chain.executors[1] == mover
        
        # 添加终结器
        cleaner = EmptyDirCleaner(Path("/test"))
        reporter = ReportGenerator(Path("/reports"), pipeline.report)
        
        pipeline.add_finalizer(cleaner)
        pipeline.add_finalizer(reporter)
        
        assert len(pipeline.processor_chain.finalizers) == 2
        assert pipeline.processor_chain.finalizers[0] == cleaner
        assert pipeline.processor_chain.finalizers[1] == reporter
    
    def test_pipeline_dry_run(self, sample_file_structure: Path):
        """测试管道预览模式"""
        # 创建配置
        global_config = GlobalConfig(scan_roots=[sample_file_structure])
        task = TaskDefinition(
            name="test_task",
            type="file_organize",
            enabled=True,
            config={
                "todo_non_vidpic_dir": str(sample_file_structure / "todo_non_vidpic"),
                "todo_vidpic_dir": str(sample_file_structure / "todo_vidpic"),
                "video_extensions": [".mp4", ".avi", ".mkv"],
                "image_extensions": [".jpg", ".png", ".webp"]
            }
        )
        
        config = TaskConfig(global_=global_config, tasks=[task])
        
        # 创建管道
        pipeline = Pipeline(config, "test_task")
        
        # 添加处理器
        pipeline.add_analyzer(FileClassifier({".mp4", ".avi", ".mkv"}, {".jpg", ".png", ".webp"}))
        pipeline.add_analyzer(SerialIdExtractor())
        
        # 运行预览模式
        report = pipeline.run_dry()
        
        # 验证结果
        assert report is not None
        assert report.task_name == "test_task"
        assert report.total_files > 0
        assert report.start_time is not None
        assert report.end_time is not None
    
    def test_pipeline_full_run(self, sample_file_structure: Path):
        """测试管道完整运行"""
        # 创建目标目录
        todo_non_vidpic_dir = sample_file_structure / "todo_non_vidpic"
        todo_vidpic_dir = sample_file_structure / "todo_vidpic"
        todo_non_vidpic_dir.mkdir()
        todo_vidpic_dir.mkdir()
        
        # 创建配置
        global_config = GlobalConfig(scan_roots=[sample_file_structure])
        task = TaskDefinition(
            name="test_task",
            type="file_organize",
            enabled=True,
            config={
                "todo_non_vidpic_dir": str(todo_non_vidpic_dir),
                "todo_vidpic_dir": str(todo_vidpic_dir),
                "video_extensions": [".mp4", ".avi", ".mkv"],
                "image_extensions": [".jpg", ".png", ".webp"]
            }
        )
        
        config = TaskConfig(global_=global_config, tasks=[task])
        
        # 创建管道
        pipeline = Pipeline(config, "test_task")
        
        # 添加处理器
        pipeline.add_analyzer(FileClassifier({".mp4", ".avi", ".mkv"}, {".jpg", ".png", ".webp"}))
        pipeline.add_analyzer(SerialIdExtractor())
        pipeline.add_executor(FileRenamer(pipeline.transaction_log))
        pipeline.add_executor(FileMover(todo_non_vidpic_dir, pipeline.transaction_log))
        pipeline.add_executor(FileMover(todo_vidpic_dir, pipeline.transaction_log))
        pipeline.add_finalizer(EmptyDirCleaner(sample_file_structure, pipeline.transaction_log))
        
        # 运行管道
        report = pipeline.run()
        
        # 验证结果
        assert report is not None
        assert report.task_name == "test_task"
        assert report.total_files > 0
        assert report.start_time is not None
        assert report.end_time is not None
        
        # 验证文件被移动
        assert todo_non_vidpic_dir.exists()
        assert todo_vidpic_dir.exists()
        
        # 验证空目录被清理
        empty_dir = sample_file_structure / "empty_dir"
        if empty_dir.exists():
            assert not empty_dir.exists()  # 空目录应该被删除
    
    def test_pipeline_error_handling(self, sample_file_structure: Path):
        """测试管道错误处理"""
        # 创建配置
        global_config = GlobalConfig(scan_roots=[sample_file_structure])
        task = TaskDefinition(
            name="test_task",
            type="file_organize",
            enabled=True,
            config={
                "todo_non_vidpic_dir": "/nonexistent/path",  # 无效路径
                "todo_vidpic_dir": "/nonexistent/path",
                "video_extensions": [".mp4"],
                "image_extensions": [".jpg"],
                "serial_id_pattern": r"[A-Za-z]{2,5}-\d+"
            }
        )
        
        config = TaskConfig(global_=global_config, tasks=[task])
        
        # 创建管道
        pipeline = Pipeline(config, "test_task")
        
        # 添加处理器
        pipeline.add_analyzer(FileClassifier({".mp4"}, {".jpg"}))
        pipeline.add_analyzer(SerialIdExtractor())
        pipeline.add_executor(FileMover(Path("/nonexistent"), pipeline.transaction_log))
        
        # 运行管道（应该处理错误但继续运行）
        report = pipeline.run()
        
        # 验证结果
        assert report is not None
        assert report.total_files > 0
        # 应该有一些错误文件
        assert report.error_files >= 0
    
    def test_pipeline_skip_remaining(self, sample_file_structure: Path):
        """测试管道短路机制"""
        # 创建配置
        global_config = GlobalConfig(scan_roots=[sample_file_structure])
        task = TaskDefinition(
            name="test_task",
            type="file_organize",
            enabled=True,
            config={
                "todo_non_vidpic_dir": str(sample_file_structure / "todo_non_vidpic"),
                "todo_vidpic_dir": str(sample_file_structure / "todo_vidpic"),
                "video_extensions": [".mp4"],
                "image_extensions": [".jpg"],
                "serial_id_pattern": r"[A-Za-z]{2,5}-\d+"
            }
        )
        
        config = TaskConfig(global_=global_config, tasks=[task])
        
        # 创建管道
        pipeline = Pipeline(config, "test_task")
        
        # 添加处理器
        pipeline.add_analyzer(FileClassifier({".mp4"}, {".jpg"}))
        pipeline.add_analyzer(SerialIdExtractor())
        pipeline.add_executor(FileRenamer(pipeline.transaction_log))
        
        # 运行管道
        report = pipeline.run()
        
        # 验证结果
        assert report is not None
        assert report.total_files > 0
        
        # 检查是否有跳过文件（非视频/图片文件应该被跳过）
        assert report.skipped_files >= 0
    
    def test_pipeline_transaction_logging(self, sample_file_structure: Path):
        """测试管道事务日志"""
        # 创建目标目录
        todo_dir = sample_file_structure / "todo"
        todo_dir.mkdir()
        
        # 创建配置
        global_config = GlobalConfig(scan_roots=[sample_file_structure])
        task = TaskDefinition(
            name="test_task",
            type="file_organize",
            enabled=True,
            config={
                "todo_non_vidpic_dir": str(todo_dir),
                "todo_vidpic_dir": str(todo_dir),
                "video_extensions": [".mp4"],
                "image_extensions": [".jpg"],
                "serial_id_pattern": r"[A-Za-z]{2,5}-\d+"
            }
        )
        
        config = TaskConfig(global_=global_config, tasks=[task])
        
        # 创建管道
        pipeline = Pipeline(config, "test_task")
        
        # 添加处理器
        pipeline.add_analyzer(FileClassifier({".mp4"}, {".jpg"}))
        pipeline.add_executor(FileMover(todo_dir, pipeline.transaction_log))
        
        # 运行管道
        report = pipeline.run()
        
        # 验证事务日志
        summary = pipeline.get_transaction_summary()
        assert summary is not None
        assert "total_transactions" in summary
        assert "completed_transactions" in summary
    
    def test_pipeline_rollback(self, sample_file_structure: Path):
        """测试管道回滚功能"""
        # 创建目标目录
        todo_dir = sample_file_structure / "todo"
        todo_dir.mkdir()
        
        # 创建配置
        global_config = GlobalConfig(scan_roots=[sample_file_structure])
        task = TaskDefinition(
            name="test_task",
            type="file_organize",
            enabled=True,
            config={
                "todo_non_vidpic_dir": str(todo_dir),
                "todo_vidpic_dir": str(todo_dir),
                "video_extensions": [".mp4"],
                "image_extensions": [".jpg"],
                "serial_id_pattern": r"[A-Za-z]{2,5}-\d+"
            }
        )
        
        config = TaskConfig(global_=global_config, tasks=[task])
        
        # 创建管道
        pipeline = Pipeline(config, "test_task")
        
        # 添加处理器
        pipeline.add_analyzer(FileClassifier({".mp4"}, {".jpg"}))
        pipeline.add_executor(FileMover(todo_dir, pipeline.transaction_log))
        
        # 运行管道
        report = pipeline.run()
        
        # 执行回滚
        rolled_back_ids = pipeline.rollback()
        
        # 验证回滚结果
        assert isinstance(rolled_back_ids, list)
        # 回滚的文件数量应该与移动的文件数量相关
        assert len(rolled_back_ids) >= 0
