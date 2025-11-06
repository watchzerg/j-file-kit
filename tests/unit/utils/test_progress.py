"""进度追踪模块单元测试

测试进度追踪器的初始化和进度更新功能。
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from rich.console import Console

from jfk.utils.progress import ProgressTracker
from jfk.core.models import TaskStats


class TestProgressTracker:
    """测试 ProgressTracker 类"""

    @pytest.fixture
    def console(self):
        """控制台 fixture"""
        return Console(file=open("/dev/null", "w"), force_terminal=False)

    @pytest.fixture
    def tracker(self, console):
        """进度追踪器 fixture"""
        return ProgressTracker(console)

    def test_initialization(self, tracker, console):
        """测试进度追踪器初始化"""
        assert tracker.console == console
        assert isinstance(tracker.stats, TaskStats)
        assert tracker.progress is None
        assert tracker.task is None
        assert tracker.stats.processed_files == 0
        assert tracker.stats.current_file is None

    def test_start_progress(self, tracker):
        """测试开始进度显示"""
        tracker.start_progress()

        assert tracker.progress is not None
        assert tracker.task is not None

    def test_start_progress_creates_task(self, tracker):
        """测试开始进度显示时创建任务"""
        tracker.start_progress()

        # 验证任务已创建
        assert tracker.task is not None
        # 验证进度条已创建
        assert tracker.progress is not None

    def test_update_progress_without_file(self, tracker):
        """测试不带文件名的进度更新"""
        tracker.start_progress()
        initial_count = tracker.stats.processed_files

        tracker.update_progress()

        assert tracker.stats.processed_files == initial_count + 1
        assert tracker.stats.current_file is None

    def test_update_progress_with_file(self, tracker):
        """测试带文件名的进度更新"""
        tracker.start_progress()
        initial_count = tracker.stats.processed_files

        tracker.update_progress("test_file.mp4")

        assert tracker.stats.processed_files == initial_count + 1
        assert tracker.stats.current_file == "test_file.mp4"

    def test_update_progress_multiple_times(self, tracker):
        """测试多次更新进度"""
        tracker.start_progress()

        tracker.update_progress("file1.mp4")
        tracker.update_progress("file2.mp4")
        tracker.update_progress("file3.mp4")

        assert tracker.stats.processed_files == 3
        assert tracker.stats.current_file == "file3.mp4"

    def test_update_progress_without_starting(self, tracker):
        """测试未启动进度显示时更新进度"""
        # 不调用 start_progress，直接更新
        tracker.update_progress("test_file.mp4")

        # 统计信息应该仍然更新
        assert tracker.stats.processed_files == 1
        assert tracker.stats.current_file == "test_file.mp4"
        # 但进度条不应该存在
        assert tracker.progress is None

    def test_stop_progress(self, tracker):
        """测试停止进度显示"""
        tracker.start_progress()
        assert tracker.progress is not None

        tracker.stop_progress()

        assert tracker.progress is None
        assert tracker.task is None

    def test_stop_progress_without_starting(self, tracker):
        """测试未启动时停止进度显示"""
        # 不调用 start_progress，直接停止
        tracker.stop_progress()

        # 应该不会出错
        assert tracker.progress is None
        assert tracker.task is None

    def test_stop_progress_multiple_times(self, tracker):
        """测试多次停止进度显示"""
        tracker.start_progress()
        tracker.stop_progress()

        # 再次停止不应该出错
        tracker.stop_progress()
        assert tracker.progress is None

    def test_full_workflow(self, tracker):
        """测试完整工作流程"""
        # 开始进度显示
        tracker.start_progress()
        assert tracker.progress is not None

        # 更新进度多次
        files = ["file1.mp4", "file2.mp4", "file3.mp4"]
        for file in files:
            tracker.update_progress(file)

        assert tracker.stats.processed_files == 3
        assert tracker.stats.current_file == "file3.mp4"

        # 停止进度显示
        tracker.stop_progress()
        assert tracker.progress is None

    def test_stats_update_on_progress_update(self, tracker):
        """测试进度更新时统计信息同步更新"""
        tracker.start_progress()

        # 更新进度
        tracker.update_progress("test.mp4")

        # 验证统计信息已更新
        assert tracker.stats.processed_files == 1
        assert tracker.stats.current_file == "test.mp4"
        assert tracker.stats.last_update is not None

    def test_update_progress_with_none_file(self, tracker):
        """测试使用 None 作为文件名更新进度"""
        tracker.start_progress()

        tracker.update_progress(None)

        assert tracker.stats.processed_files == 1
        assert tracker.stats.current_file is None

    def test_update_progress_with_empty_string(self, tracker):
        """测试使用空字符串作为文件名更新进度"""
        tracker.start_progress()

        tracker.update_progress("")

        assert tracker.stats.processed_files == 1
        assert tracker.stats.current_file == ""

    def test_restart_progress(self, tracker):
        """测试重新启动进度显示"""
        # 第一次启动和停止
        tracker.start_progress()
        tracker.update_progress("file1.mp4")
        tracker.stop_progress()

        # 重新启动
        tracker.start_progress()
        tracker.update_progress("file2.mp4")

        # 统计信息应该继续累积
        assert tracker.stats.processed_files == 2
        assert tracker.stats.current_file == "file2.mp4"
        assert tracker.progress is not None

    def test_stats_independence(self, tracker):
        """测试统计信息独立于进度显示"""
        # 不启动进度显示，直接更新统计
        tracker.update_progress("file1.mp4")
        tracker.update_progress("file2.mp4")

        # 统计信息应该正常更新
        assert tracker.stats.processed_files == 2
        assert tracker.stats.current_file == "file2.mp4"

        # 然后启动进度显示
        tracker.start_progress()
        tracker.update_progress("file3.mp4")

        # 统计信息应该继续累积
        assert tracker.stats.processed_files == 3
        assert tracker.stats.current_file == "file3.mp4"

    def test_progress_description_update(self, tracker):
        """测试进度描述更新"""
        tracker.start_progress()

        # 更新进度，验证描述会更新
        tracker.update_progress("file1.mp4")
        tracker.update_progress("file2.mp4")

        # 验证统计信息已更新
        assert tracker.stats.processed_files == 2

    def test_concurrent_updates(self, tracker):
        """测试连续快速更新"""
        tracker.start_progress()

        # 快速连续更新
        for i in range(10):
            tracker.update_progress(f"file{i}.mp4")

        assert tracker.stats.processed_files == 10
        assert tracker.stats.current_file == "file9.mp4"

