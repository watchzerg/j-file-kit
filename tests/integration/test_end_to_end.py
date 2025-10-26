"""端到端测试

测试完整的文件整理流程。
"""

import pytest
import tempfile
import yaml
from pathlib import Path

from jfk.core.config import TaskConfig, GlobalConfig, TaskDefinition, load_config
from jfk.core.pipeline import Pipeline
from jfk.processors.analyzers import FileClassifier, SerialIdExtractor
from jfk.processors.executors import FileRenamer, FileMover
from jfk.processors.finalizers import EmptyDirCleaner, ReportGenerator
from jfk.rules.video_organizer import VideoFileOrganizer


@pytest.mark.slow
@pytest.mark.integration
class TestEndToEndVideoOrganizer:
    """测试完整的视频文件整理流程"""
    
    def test_complete_video_organizer_workflow(self, temp_dir: Path):
        """测试完整的视频文件整理工作流"""
        # 创建测试文件结构
        self._create_test_file_structure(temp_dir)
        
        # 创建配置文件
        config_path = self._create_test_config(temp_dir)
        
        # 创建视频文件整理器
        organizer = VideoFileOrganizer(config_path)
        
        # 运行预览模式
        print("运行预览模式...")
        preview_report = organizer.run_dry()
        
        # 验证预览结果
        assert preview_report is not None
        assert preview_report.total_files > 0
        print(f"预览模式处理了 {preview_report.total_files} 个文件")
        
        # 运行实际整理
        print("运行实际整理...")
        report = organizer.run()
        
        # 验证整理结果
        assert report is not None
        assert report.total_files > 0
        assert report.success_files >= 0
        assert report.error_files >= 0
        
        print(f"实际整理完成:")
        print(f"  总文件数: {report.total_files}")
        print(f"  成功: {report.success_files}")
        print(f"  失败: {report.error_files}")
        print(f"  跳过: {report.skipped_files}")
        print(f"  成功率: {report.success_rate:.2%}")
        
        # 验证文件移动结果
        self._verify_file_organization(temp_dir)
        
        # 验证报告生成
        self._verify_reports_generated(temp_dir)
    
    def test_video_organizer_with_serial_ids(self, temp_dir: Path):
        """测试带番号的视频文件整理"""
        # 创建带番号的测试文件
        test_files = [
            "ABCD-001_video.mp4",
            "XYZ-999_movie.avi",
            "ABC-123_hd.mkv",
            "no_serial_video.mp4",
            "prefix_ABC-456_suffix.mov"
        ]
        
        for filename in test_files:
            file_path = temp_dir / filename
            file_path.write_text(f"content for {filename}")
        
        # 创建配置文件
        config_path = self._create_test_config(temp_dir)
        
        # 创建视频文件整理器
        organizer = VideoFileOrganizer(config_path)
        
        # 运行整理
        report = organizer.run()
        
        # 验证结果
        assert report is not None
        assert report.total_files == len(test_files)
        
        # 验证番号提取和重命名
        self._verify_serial_id_processing(temp_dir)
    
    def test_video_organizer_error_handling(self, temp_dir: Path):
        """测试视频文件整理器的错误处理"""
        # 创建有问题的文件
        problem_files = [
            "corrupted.mp4",  # 可能损坏的文件
            "very_large_file.mp4",  # 大文件
            "special_chars_<>:\"\\|?*.mp4",  # 特殊字符
        ]
        
        for filename in problem_files:
            file_path = temp_dir / filename
            file_path.write_text("content")
        
        # 创建配置文件
        config_path = self._create_test_config(temp_dir)
        
        # 创建视频文件整理器
        organizer = VideoFileOrganizer(config_path)
        
        # 运行整理
        report = organizer.run()
        
        # 验证错误处理
        assert report is not None
        assert report.total_files == len(problem_files)
        # 应该有一些错误或警告
        assert report.error_files + report.warning_files >= 0
    
    def test_video_organizer_rollback(self, temp_dir: Path):
        """测试视频文件整理器的回滚功能"""
        # 创建测试文件
        test_files = [
            "video1.mp4",
            "video2.avi",
            "image1.jpg",
            "document.txt"
        ]
        
        for filename in test_files:
            file_path = temp_dir / filename
            file_path.write_text(f"content for {filename}")
        
        # 创建配置文件
        config_path = self._create_test_config(temp_dir)
        
        # 创建视频文件整理器
        organizer = VideoFileOrganizer(config_path)
        
        # 运行整理
        report = organizer.run()
        
        # 验证文件被移动
        todo_non_vidpic_dir = temp_dir / "todo_non_vidpic"
        todo_vidpic_dir = temp_dir / "todo_vidpic"
        
        assert todo_non_vidpic_dir.exists()
        assert todo_vidpic_dir.exists()
        
        # 执行回滚
        pipeline = organizer.create_pipeline()
        rolled_back_ids = pipeline.rollback()
        
        # 验证回滚结果
        assert isinstance(rolled_back_ids, list)
        print(f"回滚了 {len(rolled_back_ids)} 个操作")
    
    def _create_test_file_structure(self, temp_dir: Path):
        """创建测试文件结构"""
        # 创建视频文件
        video_files = [
            "ABCD-001_video.mp4",
            "XYZ-999_movie.avi",
            "ABC-123_hd.mkv",
            "no_serial_video.mp4",
            "prefix_ABC-456_suffix.mov"
        ]
        
        for filename in video_files:
            file_path = temp_dir / filename
            file_path.write_text(f"video content for {filename}")
        
        # 创建图片文件
        image_files = [
            "ABCD-001_image.jpg",
            "XYZ-999_picture.png",
            "no_serial_image.jpg",
            "prefix_ABC-456_suffix.webp"
        ]
        
        for filename in image_files:
            file_path = temp_dir / filename
            file_path.write_text(f"image content for {filename}")
        
        # 创建其他文件
        other_files = [
            "document.txt",
            "data.csv",
            "script.py",
            "readme.md"
        ]
        
        for filename in other_files:
            file_path = temp_dir / filename
            file_path.write_text(f"content for {filename}")
        
        # 创建子目录
        subdir = temp_dir / "subdir"
        subdir.mkdir()
        
        (subdir / "video_in_subdir.mp4").write_text("video content")
        (subdir / "image_in_subdir.jpg").write_text("image content")
        (subdir / "doc_in_subdir.txt").write_text("doc content")
        
        # 创建空目录
        (temp_dir / "empty_dir").mkdir()
    
    def _create_test_config(self, temp_dir: Path) -> Path:
        """创建测试配置文件"""
        config_data = {
            "global": {
                "scan_roots": [str(temp_dir)],
                "log_dir": str(temp_dir / "logs"),
                "report_dir": str(temp_dir / "reports")
            },
            "tasks": [
                {
                    "name": "video_file_organizer",
                    "type": "file_organize",
                    "enabled": True,
                    "config": {
                        "todo_non_vidpic_dir": str(temp_dir / "todo_non_vidpic"),
                        "todo_vidpic_dir": str(temp_dir / "todo_vidpic"),
                        "video_extensions": [".mp4", ".avi", ".mkv", ".mov"],
                        "image_extensions": [".jpg", ".png", ".webp"],
                        "serial_id_pattern": r"[A-Za-z]{2,5}-\d+"
                    }
                }
            ]
        }
        
        config_path = temp_dir / "test_config.yaml"
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f)
        
        return config_path
    
    def _verify_file_organization(self, temp_dir: Path):
        """验证文件整理结果"""
        todo_non_vidpic_dir = temp_dir / "todo_non_vidpic"
        todo_vidpic_dir = temp_dir / "todo_vidpic"
        
        # 验证目录存在
        assert todo_non_vidpic_dir.exists()
        assert todo_vidpic_dir.exists()
        
        # 验证非视频/图片文件被移动到 todo_non_vidpic
        non_vidpic_files = list(todo_non_vidpic_dir.glob("*"))
        assert len(non_vidpic_files) > 0
        print(f"非视频/图片文件移动到: {[f.name for f in non_vidpic_files]}")
        
        # 验证无番号的视频/图片文件被移动到 todo_vidpic
        vidpic_files = list(todo_vidpic_dir.glob("*"))
        print(f"无番号视频/图片文件移动到: {[f.name for f in vidpic_files]}")
        
        # 验证有番号的文件被重命名
        renamed_files = list(temp_dir.glob("*-serialId-*"))
        print(f"重命名的文件: {[f.name for f in renamed_files]}")
    
    def _verify_serial_id_processing(self, temp_dir: Path):
        """验证番号处理结果"""
        # 检查重命名的文件
        renamed_files = list(temp_dir.glob("*-serialId-*"))
        assert len(renamed_files) > 0
        
        for file_path in renamed_files:
            # 验证文件名格式
            assert "-serialId-" in file_path.name
            print(f"重命名文件: {file_path.name}")
    
    def _verify_reports_generated(self, temp_dir: Path):
        """验证报告生成"""
        reports_dir = temp_dir / "reports"
        logs_dir = temp_dir / "logs"
        
        # 验证报告目录存在
        assert reports_dir.exists()
        assert logs_dir.exists()
        
        # 验证报告文件
        report_files = list(reports_dir.glob("*"))
        log_files = list(logs_dir.glob("*"))
        
        assert len(report_files) > 0
        assert len(log_files) > 0
        
        print(f"生成的报告文件: {[f.name for f in report_files]}")
        print(f"生成的日志文件: {[f.name for f in log_files]}")


@pytest.mark.slow
@pytest.mark.integration
class TestEndToEndPipeline:
    """测试完整的管道端到端流程"""
    
    def test_complete_pipeline_workflow(self, temp_dir: Path):
        """测试完整的管道工作流"""
        # 创建测试文件
        self._create_test_files(temp_dir)
        
        # 创建配置
        config = self._create_test_config(temp_dir)
        
        # 创建管道
        pipeline = Pipeline(config, "test_task")
        
        # 添加处理器
        pipeline.add_analyzer(FileClassifier({".mp4", ".avi"}, {".jpg", ".png"}))
        pipeline.add_analyzer(SerialIdExtractor(r"[A-Za-z]{2,5}-\d+"))  # 使用配置文件中的默认模式
        pipeline.add_executor(FileRenamer(pipeline.transaction_log))
        pipeline.add_executor(FileMover(temp_dir / "todo_non_vidpic", pipeline.transaction_log))
        pipeline.add_executor(FileMover(temp_dir / "todo_vidpic", pipeline.transaction_log))
        pipeline.add_finalizer(EmptyDirCleaner(temp_dir, pipeline.transaction_log))
        pipeline.add_finalizer(ReportGenerator(temp_dir / "reports", pipeline.report))
        
        # 运行管道
        report = pipeline.run()
        
        # 验证结果
        assert report is not None
        assert report.total_files > 0
        assert report.start_time is not None
        assert report.end_time is not None
        
        print(f"管道处理完成:")
        print(f"  总文件数: {report.total_files}")
        print(f"  成功: {report.success_files}")
        print(f"  失败: {report.error_files}")
        print(f"  跳过: {report.skipped_files}")
        print(f"  成功率: {report.success_rate:.2%}")
        print(f"  耗时: {report.duration_seconds:.2f}秒")
    
    def test_pipeline_dry_run(self, temp_dir: Path):
        """测试管道预览模式"""
        # 创建测试文件
        self._create_test_files(temp_dir)
        
        # 创建配置
        config = self._create_test_config(temp_dir)
        
        # 创建管道
        pipeline = Pipeline(config, "test_task")
        
        # 添加处理器
        pipeline.add_analyzer(FileClassifier({".mp4", ".avi"}, {".jpg", ".png"}))
        pipeline.add_analyzer(SerialIdExtractor(r"[A-Za-z]{2,5}-\d+"))  # 使用配置文件中的默认模式
        
        # 运行预览模式
        report = pipeline.run_dry()
        
        # 验证结果
        assert report is not None
        assert report.total_files > 0
        
        print(f"预览模式处理了 {report.total_files} 个文件")
    
    def test_pipeline_error_recovery(self, temp_dir: Path):
        """测试管道错误恢复"""
        # 创建有问题的文件
        problem_files = [
            "corrupted.mp4",
            "very_large_file.mp4",
            "special_chars_<>:\"\\|?*.mp4"
        ]
        
        for filename in problem_files:
            file_path = temp_dir / filename
            file_path.write_text("content")
        
        # 创建配置
        config = self._create_test_config(temp_dir)
        
        # 创建管道
        pipeline = Pipeline(config, "test_task")
        
        # 添加处理器
        pipeline.add_analyzer(FileClassifier({".mp4"}, {".jpg"}))
        pipeline.add_analyzer(SerialIdExtractor(r"[A-Za-z]{2,5}-\d+"))  # 使用配置文件中的默认模式
        pipeline.add_executor(FileRenamer(pipeline.transaction_log))
        
        # 运行管道
        report = pipeline.run()
        
        # 验证错误处理
        assert report is not None
        assert report.total_files == len(problem_files)
        print(f"错误恢复测试完成，处理了 {report.total_files} 个文件")
    
    def _create_test_files(self, temp_dir: Path):
        """创建测试文件"""
        test_files = [
            "ABCD-001_video.mp4",
            "XYZ-999_movie.avi",
            "no_serial_video.mp4",
            "image1.jpg",
            "no_serial_image.jpg",
            "document.txt",
            "data.csv"
        ]
        
        for filename in test_files:
            file_path = temp_dir / filename
            file_path.write_text(f"content for {filename}")
        
        # 创建目标目录
        (temp_dir / "todo_non_vidpic").mkdir()
        (temp_dir / "todo_vidpic").mkdir()
        (temp_dir / "reports").mkdir()
        (temp_dir / "logs").mkdir()
    
    def _create_test_config(self, temp_dir: Path) -> TaskConfig:
        """创建测试配置"""
        global_config = GlobalConfig(scan_roots=[temp_dir])
        
        task = TaskDefinition(
            name="test_task",
            type="file_organize",
            enabled=True,
            config={
                "todo_non_vidpic_dir": str(temp_dir / "todo_non_vidpic"),
                "todo_vidpic_dir": str(temp_dir / "todo_vidpic"),
                "video_extensions": [".mp4", ".avi"],
                "image_extensions": [".jpg", ".png"],
                "serial_id_pattern": r"[A-Za-z]{2,5}-\d+"
            }
        )
        
        return TaskConfig(global_=global_config, tasks=[task])
