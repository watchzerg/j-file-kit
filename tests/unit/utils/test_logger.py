"""结构化日志模块单元测试

测试日志文件的创建、写入和格式。
"""

import json
from datetime import datetime
from pathlib import Path

import pytest

from j_file_kit.domain.models import (
    FileInfo,
    FileResult,
    FileType,
    ProcessingContext,
    ProcessorResult,
    TaskReport,
)
from j_file_kit.infrastructure.logging.logger import StructuredLogger


@pytest.mark.unit
class TestStructuredLogger:
    """测试 StructuredLogger 类"""

    def test_logger_initialization(self, tmp_path):
        """测试日志记录器初始化"""
        logger = StructuredLogger(tmp_path, "test_task")

        assert logger.log_dir == tmp_path
        assert logger.task_name == "test_task"
        assert logger.task_id is not None
        assert len(logger.task_id) == 8
        assert logger.log_file.exists()
        assert logger.log_file.name.startswith("test_task_")
        assert logger.log_file.suffix == ".jsonl"

    def test_info_log(self, tmp_path):
        """测试信息日志记录"""
        logger = StructuredLogger(tmp_path, "test_task")
        logger.info("测试消息", {"key": "value"})

        # 读取日志文件
        lines = logger.log_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1

        entry = json.loads(lines[0])
        assert entry["level"] == "INFO"
        assert entry["message"] == "测试消息"
        assert entry["task_name"] == "test_task"
        assert entry["task_id"] == logger.task_id
        assert entry["data"] == {"key": "value"}
        assert "timestamp" in entry

    def test_warning_log(self, tmp_path):
        """测试警告日志记录"""
        logger = StructuredLogger(tmp_path, "test_task")
        logger.warning("警告消息")

        entry = json.loads(logger.log_file.read_text(encoding="utf-8").strip())
        assert entry["level"] == "WARNING"
        assert entry["message"] == "警告消息"
        assert entry["data"] == {}

    def test_error_log(self, tmp_path):
        """测试错误日志记录"""
        logger = StructuredLogger(tmp_path, "test_task")
        logger.error("错误消息", {"error_code": 500})

        entry = json.loads(logger.log_file.read_text(encoding="utf-8").strip())
        assert entry["level"] == "ERROR"
        assert entry["message"] == "错误消息"
        assert entry["data"] == {"error_code": 500}

    def test_debug_log(self, tmp_path):
        """测试调试日志记录"""
        logger = StructuredLogger(tmp_path, "test_task")
        logger.debug("调试消息")

        entry = json.loads(logger.log_file.read_text(encoding="utf-8").strip())
        assert entry["level"] == "DEBUG"
        assert entry["message"] == "调试消息"

    def test_log_file_result(self, tmp_path):
        """测试文件处理结果日志"""
        logger = StructuredLogger(tmp_path, "test_task")

        file_info = FileInfo.from_path(Path("/test/video.mp4"))
        from j_file_kit.domain.models import SerialId

        context = ProcessingContext(
            file_info=file_info,
            file_type=FileType.VIDEO,
            serial_id=SerialId(prefix="ABC", number="123"),
            renamed_filename=None,
            target_path=None,
            skip_remaining=False,
            action=None,
            should_delete=False,
            file_size=None,
            file_result_id=None,
        )
        result = FileResult(
            file_info=file_info,
            context=context,
            processor_results=[
                ProcessorResult.success("处理成功"),
                ProcessorResult.warning("有警告"),
            ],
            total_duration_ms=123.45,
            success=True,
            error_message=None,
        )

        logger.log_file_result(result)

        entry = json.loads(logger.log_file.read_text(encoding="utf-8").strip())
        assert entry["level"] == "FILE_RESULT"
        assert entry["message"] == "处理文件: video.mp4"
        assert entry["data"]["file_path"] == "/test/video.mp4"
        assert entry["data"]["file_type"] == "video"
        assert entry["data"]["serial_id"] == "ABC-123"
        assert entry["data"]["success"] is True
        assert entry["data"]["has_errors"] is False
        assert entry["data"]["has_warnings"] is True
        assert entry["data"]["was_skipped"] is False
        assert entry["data"]["duration_ms"] == 123.45
        assert entry["data"]["processor_count"] == 2

    def test_log_file_result_with_error(self, tmp_path):
        """测试带错误消息的文件结果日志"""
        logger = StructuredLogger(tmp_path, "test_task")

        file_info = FileInfo.from_path(Path("/test/file.mp4"))
        context = ProcessingContext(
            file_info=file_info,
            file_type=None,
            serial_id=None,
            renamed_filename=None,
            target_path=None,
            skip_remaining=False,
            action=None,
            should_delete=False,
            file_size=None,
            file_result_id=None,
        )
        result = FileResult(
            file_info=file_info,
            context=context,
            success=False,
            error_message="处理失败",
            total_duration_ms=0.0,
        )

        logger.log_file_result(result)

        entry = json.loads(logger.log_file.read_text(encoding="utf-8").strip())
        assert entry["data"]["error_message"] == "处理失败"
        assert entry["data"]["success"] is False

    def test_log_file_result_with_skip(self, tmp_path):
        """测试跳过状态的文件结果日志"""
        logger = StructuredLogger(tmp_path, "test_task")

        file_info = FileInfo.from_path(Path("/test/file.mp4"))
        context = ProcessingContext(
            file_info=file_info,
            file_type=None,
            serial_id=None,
            renamed_filename=None,
            target_path=None,
            skip_remaining=False,
            action=None,
            should_delete=False,
            file_size=None,
            file_result_id=None,
        )
        result = FileResult(
            file_info=file_info,
            context=context,
            processor_results=[ProcessorResult.skip("文件已存在")],
            success=True,
            total_duration_ms=0.0,
            error_message=None,
        )

        logger.log_file_result(result)

        entry = json.loads(logger.log_file.read_text(encoding="utf-8").strip())
        assert entry["data"]["was_skipped"] is True

    def test_log_task_start(self, tmp_path):
        """测试任务开始日志"""
        logger = StructuredLogger(tmp_path, "test_task")
        logger.log_task_start("/path/to/scan")

        entry = json.loads(logger.log_file.read_text(encoding="utf-8").strip())
        assert entry["level"] == "TASK_START"
        assert entry["message"] == "开始任务: test_task"
        assert entry["data"]["scan_root"] == "/path/to/scan"

    def test_log_task_end(self, tmp_path):
        """测试任务结束日志"""
        logger = StructuredLogger(tmp_path, "test_task")

        # 创建任务报告
        report = TaskReport(
            task_name="test_task",
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_files=100,
            success_files=90,
            error_files=5,
            skipped_files=3,
            warning_files=2,
            total_duration_ms=123450.0,
        )

        logger.log_task_end(report)

        entry = json.loads(logger.log_file.read_text(encoding="utf-8").strip())
        assert entry["level"] == "TASK_END"
        assert entry["message"] == "任务完成: test_task"
        assert entry["data"]["total_files"] == 100
        assert entry["data"]["success_files"] == 90
        assert entry["data"]["error_files"] == 5
        assert entry["data"]["skipped_files"] == 3
        assert entry["data"]["warning_files"] == 2
        assert entry["data"]["success_rate"] == 0.9
        assert entry["data"]["duration_seconds"] == 123.45

    def test_multiple_log_entries(self, tmp_path):
        """测试多条日志记录"""
        logger = StructuredLogger(tmp_path, "test_task")

        logger.info("消息1")
        logger.warning("消息2")
        logger.error("消息3")

        lines = logger.log_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 3

        entries = [json.loads(line) for line in lines]
        assert entries[0]["level"] == "INFO"
        assert entries[0]["message"] == "消息1"
        assert entries[1]["level"] == "WARNING"
        assert entries[1]["message"] == "消息2"
        assert entries[2]["level"] == "ERROR"
        assert entries[2]["message"] == "消息3"

        # 验证所有条目都有相同的 task_id
        assert all(entry["task_id"] == logger.task_id for entry in entries)

    def test_unicode_handling(self, tmp_path):
        """测试 Unicode 字符处理"""
        logger = StructuredLogger(tmp_path, "测试任务")
        logger.info("中文消息", {"中文键": "中文值", "emoji": "🎬"})

        entry = json.loads(logger.log_file.read_text(encoding="utf-8").strip())
        assert entry["message"] == "中文消息"
        assert entry["data"]["中文键"] == "中文值"
        assert entry["data"]["emoji"] == "🎬"

    def test_empty_data(self, tmp_path):
        """测试空数据"""
        logger = StructuredLogger(tmp_path, "test_task")
        logger.info("消息", None)

        entry = json.loads(logger.log_file.read_text(encoding="utf-8").strip())
        assert entry["data"] == {}

    def test_empty_dict_data(self, tmp_path):
        """测试空字典数据"""
        logger = StructuredLogger(tmp_path, "test_task")
        logger.info("消息", {})

        entry = json.loads(logger.log_file.read_text(encoding="utf-8").strip())
        assert entry["data"] == {}

    def test_log_directory_creation(self, tmp_path):
        """测试日志目录自动创建"""
        log_dir = tmp_path / "nested" / "logs"
        logger = StructuredLogger(log_dir, "test_task")

        assert log_dir.exists()
        assert logger.log_file.exists()

    def test_timestamp_format(self, tmp_path):
        """测试时间戳格式"""
        logger = StructuredLogger(tmp_path, "test_task")
        logger.info("测试")

        entry = json.loads(logger.log_file.read_text(encoding="utf-8").strip())
        timestamp = entry["timestamp"]

        # 验证 ISO 格式
        parsed_time = datetime.fromisoformat(timestamp)
        assert isinstance(parsed_time, datetime)

    def test_task_id_consistency(self, tmp_path):
        """测试同一 logger 实例的 task_id 一致性"""
        logger = StructuredLogger(tmp_path, "test_task")
        task_id = logger.task_id

        logger.info("消息1")
        logger.warning("消息2")

        lines = logger.log_file.read_text(encoding="utf-8").strip().split("\n")
        entries = [json.loads(line) for line in lines]

        # 所有日志条目应该有相同的 task_id
        assert all(entry["task_id"] == task_id for entry in entries)

    def test_different_loggers_different_task_ids(self, tmp_path):
        """测试不同 logger 实例有不同的 task_id"""
        logger1 = StructuredLogger(tmp_path, "task1")
        logger2 = StructuredLogger(tmp_path, "task2")

        assert logger1.task_id != logger2.task_id

    def test_log_file_result_with_none_values(self, tmp_path):
        """测试文件结果日志处理 None 值"""
        logger = StructuredLogger(tmp_path, "test_task")

        file_info = FileInfo.from_path(Path("/test/file.mp4"))
        context = ProcessingContext(
            file_info=file_info,
            file_type=None,
            serial_id=None,
            renamed_filename=None,
            target_path=None,
            skip_remaining=False,
            action=None,
            should_delete=False,
            file_size=None,
            file_result_id=None,
        )
        result = FileResult(
            file_info=file_info,
            context=context,
            success=True,
            total_duration_ms=0.0,
            error_message=None,
        )

        logger.log_file_result(result)

        entry = json.loads(logger.log_file.read_text(encoding="utf-8").strip())
        assert entry["data"]["file_type"] is None
        assert entry["data"]["serial_id"] is None
        assert "error_message" not in entry["data"]

    def test_json_lines_format(self, tmp_path):
        """测试 JSON Lines 格式（每行一个 JSON 对象）"""
        logger = StructuredLogger(tmp_path, "test_task")

        logger.info("消息1")
        logger.info("消息2")
        logger.info("消息3")

        content = logger.log_file.read_text(encoding="utf-8")
        lines = [line for line in content.strip().split("\n") if line]

        assert len(lines) == 3

        # 每行都应该是有效的 JSON
        for line in lines:
            entry = json.loads(line)
            assert isinstance(entry, dict)
            assert "level" in entry
            assert "message" in entry

    def test_special_characters_in_message(self, tmp_path):
        """测试消息中的特殊字符"""
        logger = StructuredLogger(tmp_path, "test_task")
        logger.info('消息包含\n换行符\t制表符"引号')

        entry = json.loads(logger.log_file.read_text(encoding="utf-8").strip())
        assert "\n" in entry["message"]
        assert "\t" in entry["message"]
        assert '"' in entry["message"]

    def test_special_characters_in_data(self, tmp_path):
        """测试数据中的特殊字符"""
        logger = StructuredLogger(tmp_path, "test_task")
        logger.info("测试", {"path": "/path/with\nnewline", "json": '{"key": "value"}'})

        entry = json.loads(logger.log_file.read_text(encoding="utf-8").strip())
        assert "\n" in entry["data"]["path"]
        assert entry["data"]["json"] == '{"key": "value"}'
