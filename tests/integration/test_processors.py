"""处理器集成测试

测试各种处理器的集成功能。
"""

import pytest
from pathlib import Path

from jfk.core.models import FileInfo, ProcessingContext, FileType
from jfk.processors.analyzers import FileClassifier, SerialIdExtractor, FileSizeAnalyzer
from jfk.processors.executors import FileRenamer, FileMover, FileDeleter
from jfk.processors.finalizers import EmptyDirCleaner, ReportGenerator
from jfk.utils.file_utils import extract_serial_id


@pytest.mark.integration
class TestAnalyzers:
    """测试分析器集成"""
    
    def test_file_classifier_integration(self, sample_file_structure: Path):
        """测试文件分类器集成"""
        classifier = FileClassifier({".mp4", ".avi"}, {".jpg", ".png"})
        
        # 测试视频文件
        video_file = sample_file_structure / "video1.mp4"
        file_info = FileInfo.from_path(video_file)
        ctx = ProcessingContext(file_info=file_info)
        
        result = classifier.process(ctx)
        
        assert result.status == "success"
        assert ctx.file_type == FileType.VIDEO
        assert not ctx.skip_remaining
        
        # 测试图片文件
        image_file = sample_file_structure / "image1.jpg"
        file_info = FileInfo.from_path(image_file)
        ctx = ProcessingContext(file_info=file_info)
        
        result = classifier.process(ctx)
        
        assert result.status == "success"
        assert ctx.file_type == FileType.IMAGE
        assert not ctx.skip_remaining
        
        # 测试其他文件
        other_file = sample_file_structure / "document.txt"
        file_info = FileInfo.from_path(other_file)
        ctx = ProcessingContext(file_info=other_file)
        
        result = classifier.process(ctx)
        
        assert result.status == "success"
        assert ctx.file_type == FileType.OTHER
        assert ctx.skip_remaining  # 其他文件应该设置短路标记
    
    def test_serial_id_extractor_integration(self, sample_file_structure: Path):
        """测试番号提取器集成"""
        extractor = SerialIdExtractor()
        
        # 测试有番号的视频文件
        video_file = sample_file_structure / "ABCD-001_video.mp4"
        file_info = FileInfo.from_path(video_file)
        ctx = ProcessingContext(file_info=file_info)
        ctx.file_type = FileType.VIDEO
        
        result = extractor.process(ctx)
        
        assert result.status == "success"
        assert ctx.serial_id == "ABCD-001"
        assert ctx.target_path is not None
        
        # 测试无番号的视频文件
        video_file = sample_file_structure / "no_serial_video.mp4"
        file_info = FileInfo.from_path(video_file)
        ctx = ProcessingContext(file_info=file_info)
        ctx.file_type = FileType.VIDEO
        
        result = extractor.process(ctx)
        
        assert result.status == "success"
        assert ctx.serial_id is None
        
        # 测试非视频文件（应该跳过）
        other_file = sample_file_structure / "document.txt"
        file_info = FileInfo.from_path(other_file)
        ctx = ProcessingContext(file_info=file_info)
        ctx.file_type = FileType.OTHER
        
        result = extractor.process(ctx)
        
        assert result.status == "skip"
    
    def test_file_size_analyzer_integration(self, sample_file_structure: Path):
        """测试文件大小分析器集成"""
        analyzer = FileSizeAnalyzer(min_size=100, max_size=10000)
        
        # 创建不同大小的文件
        small_file = sample_file_structure / "small.txt"
        small_file.write_text("x" * 50)  # 50 字节
        
        large_file = sample_file_structure / "large.txt"
        large_file.write_text("x" * 20000)  # 20000 字节
        
        normal_file = sample_file_structure / "normal.txt"
        normal_file.write_text("x" * 1000)  # 1000 字节
        
        # 测试小文件
        file_info = FileInfo.from_path(small_file)
        ctx = ProcessingContext(file_info=file_info)
        
        result = analyzer.process(ctx)
        
        assert result.status == "skip"
        assert ctx.skip_remaining
        
        # 测试大文件
        file_info = FileInfo.from_path(large_file)
        ctx = ProcessingContext(file_info=file_info)
        
        result = analyzer.process(ctx)
        
        assert result.status == "skip"
        assert ctx.skip_remaining
        
        # 测试正常文件
        file_info = FileInfo.from_path(normal_file)
        ctx = ProcessingContext(file_info=file_info)
        
        result = analyzer.process(ctx)
        
        assert result.status == "success"
        assert not ctx.skip_remaining
        assert ctx.custom_data["file_size"] == 1000


@pytest.mark.integration
class TestExecutors:
    """测试执行器集成"""
    
    def test_file_renamer_integration(self, sample_file_structure: Path):
        """测试文件重命名器集成"""
        renamer = FileRenamer()
        
        # 创建测试文件
        test_file = sample_file_structure / "old_name.mp4"
        test_file.write_text("test content")
        
        # 设置上下文
        file_info = FileInfo.from_path(test_file)
        ctx = ProcessingContext(file_info=file_info)
        ctx.serial_id = "ABC-001"
        ctx.target_path = sample_file_structure / "ABC-001-serialId-old_name.mp4"
        
        # 执行重命名
        result = renamer.process(ctx)
        
        assert result.status == "success"
        assert ctx.target_path.exists()
        assert not test_file.exists()
        
        # 验证文件内容
        assert ctx.target_path.read_text() == "test content"
    
    def test_file_mover_integration(self, sample_file_structure: Path):
        """测试文件移动器集成"""
        target_dir = sample_file_structure / "target"
        target_dir.mkdir()
        
        mover = FileMover(target_dir)
        
        # 创建测试文件
        test_file = sample_file_structure / "test.mp4"
        test_file.write_text("test content")
        
        # 设置上下文
        file_info = FileInfo.from_path(test_file)
        ctx = ProcessingContext(file_info=file_info)
        ctx.file_type = FileType.OTHER  # 其他文件需要移动
        
        # 执行移动
        result = mover.process(ctx)
        
        assert result.status == "success"
        assert (target_dir / "test.mp4").exists()
        assert not test_file.exists()
        
        # 验证文件内容
        assert (target_dir / "test.mp4").read_text() == "test content"
    
    def test_file_mover_skip_video(self, sample_file_structure: Path):
        """测试文件移动器跳过视频文件"""
        target_dir = sample_file_structure / "target"
        target_dir.mkdir()
        
        mover = FileMover(target_dir)
        
        # 创建测试文件
        test_file = sample_file_structure / "video.mp4"
        test_file.write_text("test content")
        
        # 设置上下文
        file_info = FileInfo.from_path(test_file)
        ctx = ProcessingContext(file_info=file_info)
        ctx.file_type = FileType.VIDEO  # 视频文件不需要移动
        
        # 执行移动
        result = mover.process(ctx)
        
        assert result.status == "skip"
        assert test_file.exists()  # 文件应该还在原位置
    
    def test_file_deleter_integration(self, sample_file_structure: Path):
        """测试文件删除器集成"""
        deleter = FileDeleter()
        
        # 创建测试文件
        test_file = sample_file_structure / "to_delete.txt"
        test_file.write_text("test content")
        
        # 设置上下文
        file_info = FileInfo.from_path(test_file)
        ctx = ProcessingContext(file_info=file_info)
        
        # 执行删除
        result = deleter.process(ctx)
        
        assert result.status == "success"
        assert not test_file.exists()
    
    def test_file_deleter_nonexistent_file(self, sample_file_structure: Path):
        """测试删除不存在的文件"""
        deleter = FileDeleter()
        
        # 设置上下文（文件不存在）
        file_info = FileInfo.from_path(sample_file_structure / "nonexistent.txt")
        ctx = ProcessingContext(file_info=file_info)
        
        # 执行删除
        result = deleter.process(ctx)
        
        assert result.status == "skip"


@pytest.mark.integration
class TestFinalizers:
    """测试终结器集成"""
    
    def test_empty_dir_cleaner_integration(self, sample_file_structure: Path):
        """测试空目录清理器集成"""
        cleaner = EmptyDirCleaner(sample_file_structure)
        
        # 创建空目录结构
        empty_dir1 = sample_file_structure / "empty1"
        empty_dir1.mkdir()
        
        empty_dir2 = sample_file_structure / "empty2"
        empty_dir2.mkdir()
        
        nested_empty = sample_file_structure / "nested" / "empty"
        nested_empty.mkdir(parents=True)
        
        # 执行清理
        result = cleaner.finalize()
        
        assert result.status == "success"
        assert not empty_dir1.exists()
        assert not empty_dir2.exists()
        assert not nested_empty.exists()
        assert not (sample_file_structure / "nested").exists()  # 父目录也应该被删除
    
    def test_empty_dir_cleaner_with_files(self, sample_file_structure: Path):
        """测试空目录清理器（有文件的情况）"""
        cleaner = EmptyDirCleaner(sample_file_structure)
        
        # 创建有文件的目录
        dir_with_file = sample_file_structure / "dir_with_file"
        dir_with_file.mkdir()
        (dir_with_file / "file.txt").write_text("content")
        
        # 创建空目录
        empty_dir = sample_file_structure / "empty"
        empty_dir.mkdir()
        
        # 执行清理
        result = cleaner.finalize()
        
        assert result.status == "success"
        assert not empty_dir.exists()  # 空目录应该被删除
        assert dir_with_file.exists()  # 有文件的目录应该保留
        assert (dir_with_file / "file.txt").exists()
    
    def test_report_generator_integration(self, sample_file_structure: Path):
        """测试报告生成器集成"""
        report_dir = sample_file_structure / "reports"
        report_dir.mkdir()
        
        # 创建模拟报告
        from jfk.core.models import TaskReport
        from datetime import datetime
        
        report = TaskReport(
            task_name="test_task",
            start_time=datetime.now(),
            end_time=datetime.now()
        )
        
        # 添加一些结果
        file_info = FileInfo.from_path(Path("/test/file.mp4"))
        ctx = ProcessingContext(file_info=file_info)
        
        from jfk.core.models import TaskResult, ProcessorResult
        task_result = TaskResult(
            file_info=file_info,
            context=ctx,
            processor_results=[ProcessorResult.success("成功")],
            total_duration_ms=100.0,
            success=True
        )
        
        report.add_result(task_result)
        
        # 创建报告生成器
        generator = ReportGenerator(report_dir, report)
        
        # 生成报告
        result = generator.finalize()
        
        assert result.status == "success"
        
        # 验证报告文件
        markdown_report = report_dir / "test_task_report.md"
        json_report = report_dir / "test_task_report.json"
        
        assert markdown_report.exists()
        assert json_report.exists()
        
        # 验证报告内容
        markdown_content = markdown_report.read_text()
        assert "test_task" in markdown_content
        assert "总文件数" in markdown_content
        
        json_content = json_report.read_text()
        assert "test_task" in json_content
        assert "statistics" in json_content


@pytest.mark.integration
class TestProcessorChain:
    """测试处理器链集成"""
    
    def test_processor_chain_integration(self, sample_file_structure: Path):
        """测试处理器链集成"""
        from jfk.core.processor import ProcessorChain
        
        chain = ProcessorChain()
        
        # 添加分析器
        classifier = FileClassifier({".mp4"}, {".jpg"})
        extractor = SerialIdExtractor()
        
        chain.add_analyzer(classifier)
        chain.add_analyzer(extractor)
        
        # 添加执行器
        target_dir = sample_file_structure / "target"
        target_dir.mkdir()
        
        mover = FileMover(target_dir)
        chain.add_executor(mover)
        
        # 添加终结器
        cleaner = EmptyDirCleaner(sample_file_structure)
        chain.add_finalizer(cleaner)
        
        # 测试文件处理
        test_file = sample_file_structure / "test.mp4"
        test_file.write_text("test content")
        
        file_info = FileInfo.from_path(test_file)
        ctx = ProcessingContext(file_info=file_info)
        
        # 处理文件
        results = chain.process_file(ctx)
        
        assert len(results) > 0
        assert all(result.status in ["success", "skip"] for result in results)
        
        # 测试终结器
        finalizer_results = chain.finalize_all()
        
        assert len(finalizer_results) > 0
        assert all(result.status in ["success", "skip"] for result in finalizer_results)
    
    def test_processor_chain_skip_remaining(self, sample_file_structure: Path):
        """测试处理器链短路机制"""
        from jfk.core.processor import ProcessorChain
        
        chain = ProcessorChain()
        
        # 添加分析器
        classifier = FileClassifier({".mp4"}, {".jpg"})
        chain.add_analyzer(classifier)
        
        # 添加执行器
        target_dir = sample_file_structure / "target"
        target_dir.mkdir()
        
        mover = FileMover(target_dir)
        chain.add_executor(mover)
        
        # 测试其他文件（应该被跳过）
        test_file = sample_file_structure / "test.txt"
        test_file.write_text("test content")
        
        file_info = FileInfo.from_path(test_file)
        ctx = ProcessingContext(file_info=file_info)
        
        # 处理文件
        results = chain.process_file(ctx)
        
        # 应该只有分析器执行，执行器被跳过
        assert len(results) == 1  # 只有分析器
        assert results[0].status == "success"
        assert ctx.skip_remaining
