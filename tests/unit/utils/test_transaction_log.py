"""事务日志模块单元测试

测试事务日志的创建、写入和序列化。
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from j_file_kit.utils.transaction_log import (
    OperationType,
    TransactionEntry,
    TransactionLog,
)


@pytest.mark.unit
class TestOperationType:
    """测试 OperationType 常量类"""

    def test_operation_type_constants(self):
        """测试操作类型常量值"""
        assert OperationType.RENAME == "rename"
        assert OperationType.MOVE == "move"
        assert OperationType.DELETE == "delete"
        assert OperationType.CREATE_DIR == "create_dir"
        assert OperationType.DELETE_DIR == "delete_dir"


@pytest.mark.unit
class TestTransactionEntry:
    """测试 TransactionEntry 类"""

    def test_entry_initialization(self):
        """测试事务条目初始化"""
        source_path = Path("/test/source.txt")
        target_path = Path("/test/target.txt")
        data = {"key": "value"}

        entry = TransactionEntry(
            operation=OperationType.RENAME,
            source_path=source_path,
            target_path=target_path,
            data=data,
        )

        assert entry.operation == OperationType.RENAME
        assert entry.source_path == source_path
        assert entry.target_path == target_path
        assert entry.data == data
        assert entry.id is not None
        assert isinstance(entry.timestamp, datetime)

    def test_entry_initialization_without_target_path(self):
        """测试不带目标路径的事务条目初始化"""
        source_path = Path("/test/file.txt")

        entry = TransactionEntry(
            operation=OperationType.DELETE,
            source_path=source_path,
        )

        assert entry.operation == OperationType.DELETE
        assert entry.source_path == source_path
        assert entry.target_path is None
        assert entry.data == {}

    def test_entry_initialization_without_data(self):
        """测试不带附加数据的事务条目初始化"""
        source_path = Path("/test/file.txt")

        entry = TransactionEntry(
            operation=OperationType.DELETE,
            source_path=source_path,
        )

        assert entry.data == {}

    def test_entry_to_dict(self):
        """测试事务条目转换为字典"""
        source_path = Path("/test/source.txt")
        target_path = Path("/test/target.txt")
        data = {"serial_id": "123"}

        entry = TransactionEntry(
            operation=OperationType.MOVE,
            source_path=source_path,
            target_path=target_path,
            data=data,
        )

        result = entry.to_dict()

        assert result["operation"] == OperationType.MOVE
        assert result["source_path"] == str(source_path)
        assert result["target_path"] == str(target_path)
        assert result["data"] == data
        assert result["id"] == entry.id
        assert result["timestamp"] == entry.timestamp.isoformat()

    def test_entry_to_dict_without_target_path(self):
        """测试不带目标路径的条目转换为字典"""
        source_path = Path("/test/file.txt")

        entry = TransactionEntry(
            operation=OperationType.DELETE,
            source_path=source_path,
        )

        result = entry.to_dict()

        assert result["target_path"] is None

    def test_entry_from_dict(self):
        """测试从字典创建事务条目"""
        source_path = Path("/test/source.txt")
        target_path = Path("/test/target.txt")
        data = {"key": "value"}
        entry_id = "test-id-123"
        timestamp = datetime.now()

        dict_data = {
            "id": entry_id,
            "timestamp": timestamp.isoformat(),
            "operation": OperationType.RENAME,
            "source_path": str(source_path),
            "target_path": str(target_path),
            "data": data,
        }

        entry = TransactionEntry.from_dict(dict_data)

        assert entry.id == entry_id
        assert entry.timestamp == timestamp
        assert entry.operation == OperationType.RENAME
        assert entry.source_path == source_path
        assert entry.target_path == target_path
        assert entry.data == data

    def test_entry_from_dict_without_target_path(self):
        """测试从字典创建不带目标路径的事务条目"""
        source_path = Path("/test/file.txt")
        entry_id = "test-id-456"
        timestamp = datetime.now()

        dict_data: dict[str, Any] = {
            "id": entry_id,
            "timestamp": timestamp.isoformat(),
            "operation": OperationType.DELETE,
            "source_path": str(source_path),
            "target_path": None,
            "data": {},
        }

        entry = TransactionEntry.from_dict(dict_data)

        assert entry.target_path is None

    def test_entry_round_trip(self):
        """测试事务条目的序列化和反序列化往返"""
        source_path = Path("/test/source.txt")
        target_path = Path("/test/target.txt")
        data = {"test": "data"}

        original_entry = TransactionEntry(
            operation=OperationType.MOVE,
            source_path=source_path,
            target_path=target_path,
            data=data,
        )

        # 序列化
        dict_data = original_entry.to_dict()

        # 反序列化
        restored_entry = TransactionEntry.from_dict(dict_data)

        assert restored_entry.id == original_entry.id
        assert restored_entry.timestamp == original_entry.timestamp
        assert restored_entry.operation == original_entry.operation
        assert restored_entry.source_path == original_entry.source_path
        assert restored_entry.target_path == original_entry.target_path
        assert restored_entry.data == original_entry.data


@pytest.mark.unit
class TestTransactionLog:
    """测试 TransactionLog 类"""

    def test_log_initialization(self, tmp_path):
        """测试事务日志初始化"""
        log = TransactionLog(tmp_path, "test_task")

        assert log.log_dir == tmp_path
        assert log.task_name == "test_task"
        assert log.task_id is not None
        assert len(log.task_id) == 8
        assert log.log_file.name.startswith("transaction_test_task_")
        assert log.log_file.suffix == ".jsonl"
        # 文件在首次写入时创建，初始化时目录存在即可
        assert log.log_dir.exists()

    def test_log_creates_directory(self, tmp_path):
        """测试事务日志自动创建目录"""
        log_dir = tmp_path / "nested" / "logs"
        TransactionLog(log_dir, "test_task")

        assert log_dir.exists()
        assert log_dir.is_dir()

    def test_create_rename_entry(self, tmp_path):
        """测试创建重命名事务条目"""
        log = TransactionLog(tmp_path, "test_task")
        source_path = Path("/test/source.txt")
        target_path = Path("/test/target.txt")
        data = {"serial_id": "123"}

        entry = log.create_rename_entry(source_path, target_path, data)

        assert entry.operation == OperationType.RENAME
        assert entry.source_path == source_path
        assert entry.target_path == target_path
        assert entry.data == data

    def test_create_move_entry(self, tmp_path):
        """测试创建移动事务条目"""
        log = TransactionLog(tmp_path, "test_task")
        source_path = Path("/test/source.txt")
        target_path = Path("/test/target.txt")
        data = {"file_type": "video"}

        entry = log.create_move_entry(source_path, target_path, data)

        assert entry.operation == OperationType.MOVE
        assert entry.source_path == source_path
        assert entry.target_path == target_path
        assert entry.data == data

    def test_create_delete_entry(self, tmp_path):
        """测试创建删除事务条目"""
        log = TransactionLog(tmp_path, "test_task")
        path = Path("/test/file.txt")
        data = {"reason": "duplicate"}

        entry = log.create_delete_entry(path, data)

        assert entry.operation == OperationType.DELETE
        assert entry.source_path == path
        assert entry.target_path is None
        assert entry.data == data

    def test_create_dir_entry(self, tmp_path):
        """测试创建目录事务条目"""
        log = TransactionLog(tmp_path, "test_task")
        path = Path("/test/new_dir")
        data = {"purpose": "storage"}

        entry = log.create_dir_entry(path, data)

        assert entry.operation == OperationType.CREATE_DIR
        assert entry.source_path == path
        assert entry.target_path is None
        assert entry.data == data

    def test_create_delete_dir_entry(self, tmp_path):
        """测试创建删除目录事务条目"""
        log = TransactionLog(tmp_path, "test_task")
        path = Path("/test/old_dir")
        data = {"purpose": "cleanup"}

        entry = log.create_delete_dir_entry(path, data)

        assert entry.operation == OperationType.DELETE_DIR
        assert entry.source_path == path
        assert entry.target_path is None
        assert entry.data == data

    def test_create_entry_without_data(self, tmp_path):
        """测试创建不带附加数据的事务条目"""
        log = TransactionLog(tmp_path, "test_task")
        source_path = Path("/test/source.txt")
        target_path = Path("/test/target.txt")

        entry = log.create_rename_entry(source_path, target_path)

        assert entry.data == {}

    def test_write_entry(self, tmp_path):
        """测试写入事务条目到日志文件"""
        log = TransactionLog(tmp_path, "test_task")
        source_path = Path("/test/source.txt")
        target_path = Path("/test/target.txt")

        entry = log.create_rename_entry(source_path, target_path)
        log.write_entry(entry)

        # 读取日志文件
        lines = log.log_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1

        entry_data = json.loads(lines[0])
        assert entry_data["operation"] == OperationType.RENAME
        assert entry_data["source_path"] == str(source_path)
        assert entry_data["target_path"] == str(target_path)
        assert entry_data["id"] == entry.id

    def test_write_multiple_entries(self, tmp_path):
        """测试写入多个事务条目"""
        log = TransactionLog(tmp_path, "test_task")

        # 写入多个条目
        entry1 = log.create_rename_entry(
            Path("/test/file1.txt"), Path("/test/file1_new.txt")
        )
        log.write_entry(entry1)

        entry2 = log.create_move_entry(
            Path("/test/file2.txt"), Path("/test/moved/file2.txt")
        )
        log.write_entry(entry2)

        entry3 = log.create_delete_entry(Path("/test/file3.txt"))
        log.write_entry(entry3)

        # 读取日志文件
        lines = log.log_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 3

        # 验证每个条目
        entry1_data = json.loads(lines[0])
        assert entry1_data["operation"] == OperationType.RENAME
        assert entry1_data["id"] == entry1.id

        entry2_data = json.loads(lines[1])
        assert entry2_data["operation"] == OperationType.MOVE
        assert entry2_data["id"] == entry2.id

        entry3_data = json.loads(lines[2])
        assert entry3_data["operation"] == OperationType.DELETE
        assert entry3_data["id"] == entry3.id

    def test_write_entry_with_data(self, tmp_path):
        """测试写入带附加数据的事务条目"""
        log = TransactionLog(tmp_path, "test_task")
        source_path = Path("/test/source.txt")
        target_path = Path("/test/target.txt")
        data = {"serial_id": "ABC-123", "file_type": "video"}

        entry = log.create_move_entry(source_path, target_path, data)
        log.write_entry(entry)

        # 读取日志文件
        lines = log.log_file.read_text(encoding="utf-8").strip().split("\n")
        entry_data = json.loads(lines[0])

        assert entry_data["data"] == data
        assert entry_data["data"]["serial_id"] == "ABC-123"
        assert entry_data["data"]["file_type"] == "video"

    def test_write_entry_unicode(self, tmp_path):
        """测试写入包含 Unicode 字符的事务条目"""
        log = TransactionLog(tmp_path, "test_task")
        source_path = Path("/test/测试文件.txt")
        target_path = Path("/test/目标文件.txt")
        data = {"备注": "测试数据"}

        entry = log.create_rename_entry(source_path, target_path, data)
        log.write_entry(entry)

        # 读取日志文件
        lines = log.log_file.read_text(encoding="utf-8").strip().split("\n")
        entry_data = json.loads(lines[0])

        assert entry_data["source_path"] == str(source_path)
        assert entry_data["target_path"] == str(target_path)
        assert entry_data["data"]["备注"] == "测试数据"

    def test_different_task_names(self, tmp_path):
        """测试不同任务名称创建不同的日志文件"""
        log1 = TransactionLog(tmp_path, "task1")
        log2 = TransactionLog(tmp_path, "task2")

        assert log1.task_name == "task1"
        assert log2.task_name == "task2"
        assert log1.log_file != log2.log_file
        assert log1.log_file.name.startswith("transaction_task1_")
        assert log2.log_file.name.startswith("transaction_task2_")

    def test_same_task_name_different_ids(self, tmp_path):
        """测试相同任务名称但不同实例创建不同的日志文件"""
        log1 = TransactionLog(tmp_path, "test_task")
        log2 = TransactionLog(tmp_path, "test_task")

        # 由于 task_id 是随机生成的，文件应该不同
        assert log1.task_id != log2.task_id
        assert log1.log_file != log2.log_file
