"""Pytest 配置和共享 fixtures

提供测试中使用的共享 fixtures 和配置。
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Generator

from jfk.core.models import FileInfo, ProcessingContext, ProcessorResult, TaskResult
from jfk.core.config import TaskConfig, GlobalConfig, TaskDefinition


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """临时目录 fixture"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def sample_file_info() -> FileInfo:
    """示例文件信息 fixture"""
    return FileInfo(
        path=Path("/test/sample.mp4"),
        name="sample",
        suffix=".mp4"
    )


@pytest.fixture
def sample_processing_context(sample_file_info: FileInfo) -> ProcessingContext:
    """示例处理上下文 fixture"""
    return ProcessingContext(file_info=sample_file_info)


@pytest.fixture
def sample_processor_result() -> ProcessorResult:
    """示例处理器结果 fixture"""
    return ProcessorResult(
        status="success",
        message="处理成功",
        duration_ms=100.0,
        data={"key": "value"}
    )


@pytest.fixture
def sample_task_result(sample_file_info: FileInfo, sample_processing_context: ProcessingContext) -> TaskResult:
    """示例任务结果 fixture"""
    return TaskResult(
        file_info=sample_file_info,
        context=sample_processing_context,
        processor_results=[],
        total_duration_ms=100.0,
        success=True,
        error_message=None
    )


@pytest.fixture
def sample_config() -> TaskConfig:
    """示例配置 fixture"""
    global_config = GlobalConfig(scan_roots=[Path("/test/scan")])
    
    task = TaskDefinition(
        name="test_task",
        type="file_organize",
        enabled=True,
        config={
            "todo_non_vidpic_dir": "/todo/non-vidpic",
            "todo_vidpic_dir": "/todo/vidpic",
            "video_extensions": [".mp4", ".avi"],
            "image_extensions": [".jpg", ".png"],
            "serial_id_pattern": r"[A-Za-z]{2,5}-\d+"
        }
    )
    
    return TaskConfig(
        global_=global_config,
        tasks=[task]
    )


@pytest.fixture
def sample_file_structure(temp_dir: Path) -> Path:
    """示例文件结构 fixture"""
    # 创建示例文件结构
    (temp_dir / "video1.mp4").write_text("video content")
    (temp_dir / "video2.avi").write_text("video content")
    (temp_dir / "image1.jpg").write_text("image content")
    (temp_dir / "image2.png").write_text("image content")
    (temp_dir / "document.txt").write_text("text content")
    
    # 创建子目录
    subdir = temp_dir / "subdir"
    subdir.mkdir()
    (subdir / "video3.mkv").write_text("video content")
    (subdir / "image3.webp").write_text("image content")
    
    # 创建空目录
    (temp_dir / "empty_dir").mkdir()
    
    return temp_dir


@pytest.fixture
def sample_video_files(temp_dir: Path) -> list[Path]:
    """示例视频文件 fixture"""
    video_files = [
        "ABCD-001_video.mp4",
        "XYZ-999_movie.avi",
        "ABC-123_hd.mkv",
        "no_serial_video.mp4",
        "prefix_ABC-456_suffix.mov"
    ]
    
    created_files = []
    for filename in video_files:
        file_path = temp_dir / filename
        file_path.write_text("video content")
        created_files.append(file_path)
    
    return created_files


@pytest.fixture
def sample_image_files(temp_dir: Path) -> list[Path]:
    """示例图片文件 fixture"""
    image_files = [
        "ABCD-001_image.jpg",
        "XYZ-999_picture.png",
        "ABC-123_photo.webp",
        "no_serial_image.jpg",
        "prefix_ABC-456_suffix.png"
    ]
    
    created_files = []
    for filename in image_files:
        file_path = temp_dir / filename
        file_path.write_text("image content")
        created_files.append(file_path)
    
    return created_files


@pytest.fixture
def sample_other_files(temp_dir: Path) -> list[Path]:
    """示例其他文件 fixture"""
    other_files = [
        "document.txt",
        "data.csv",
        "script.py",
        "readme.md",
        "config.json"
    ]
    
    created_files = []
    for filename in other_files:
        file_path = temp_dir / filename
        file_path.write_text("file content")
        created_files.append(file_path)
    
    return created_files


@pytest.fixture
def mock_transaction_log():
    """模拟事务日志 fixture"""
    class MockTransactionLog:
        def __init__(self):
            self.transactions = []
        
        def log_rename(self, source_path, target_path, data=None):
            transaction_id = f"rename_{len(self.transactions)}"
            self.transactions.append({
                "id": transaction_id,
                "operation": "rename",
                "source_path": str(source_path),
                "target_path": str(target_path),
                "data": data or {}
            })
            return transaction_id
        
        def log_move(self, source_path, target_path, data=None):
            transaction_id = f"move_{len(self.transactions)}"
            self.transactions.append({
                "id": transaction_id,
                "operation": "move",
                "source_path": str(source_path),
                "target_path": str(target_path),
                "data": data or {}
            })
            return transaction_id
        
        def log_delete(self, path, data=None):
            transaction_id = f"delete_{len(self.transactions)}"
            self.transactions.append({
                "id": transaction_id,
                "operation": "delete",
                "source_path": str(path),
                "data": data or {}
            })
            return transaction_id
        
        def mark_completed(self, transaction_id):
            for transaction in self.transactions:
                if transaction["id"] == transaction_id:
                    transaction["completed"] = True
                    break
        
        def get_summary(self):
            return {
                "total_transactions": len(self.transactions),
                "completed_transactions": len([t for t in self.transactions if t.get("completed", False)]),
                "rolled_back_transactions": 0,
                "pending_transactions": len([t for t in self.transactions if not t.get("completed", False)])
            }
    
    return MockTransactionLog()


@pytest.fixture
def mock_logger():
    """模拟日志记录器 fixture"""
    class MockLogger:
        def __init__(self):
            self.logs = []
        
        def info(self, message, data=None):
            self.logs.append({"level": "INFO", "message": message, "data": data})
        
        def warning(self, message, data=None):
            self.logs.append({"level": "WARNING", "message": message, "data": data})
        
        def error(self, message, data=None):
            self.logs.append({"level": "ERROR", "message": message, "data": data})
        
        def debug(self, message, data=None):
            self.logs.append({"level": "DEBUG", "message": message, "data": data})
        
        def log_file_result(self, result):
            self.logs.append({"level": "FILE_RESULT", "result": result})
        
        def log_task_start(self, scan_root, total_files):
            self.logs.append({"level": "TASK_START", "scan_root": str(scan_root), "total_files": total_files})
        
        def log_task_end(self, report):
            self.logs.append({"level": "TASK_END", "report": report})
    
    return MockLogger()


# 测试标记
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.slow = pytest.mark.slow
