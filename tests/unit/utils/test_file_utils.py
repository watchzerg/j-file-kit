"""文件工具函数单元测试

测试 extract_serial_id, resolve_unique_path 等工具函数。
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from j_file_kit.domain.models import FileType
from j_file_kit.utils.file_utils import (
    get_file_type,
    resolve_unique_path,
)


@pytest.mark.unit
class TestResolveUniquePath:
    """测试路径冲突处理函数"""

    def test_resolve_unique_path_no_conflict(self, tmp_path):
        """测试无冲突情况"""
        target_path = tmp_path / "test.mp4"
        result = resolve_unique_path(target_path)
        assert result == target_path

    def test_resolve_unique_path_with_conflict(self, tmp_path):
        """测试有冲突情况"""
        # 创建冲突文件
        conflict_file = tmp_path / "test.mp4"
        conflict_file.write_text("test")

        target_path = tmp_path / "test.mp4"

        # Mock random.choices 返回固定的随机字符串
        with patch(
            "j_file_kit.utils.file_utils.random.choices",
            return_value=["a", "b", "c", "d"],
        ):
            result = resolve_unique_path(target_path)
            expected = tmp_path / "test-abcd.mp4"
            assert result == expected

    def test_resolve_unique_path_multiple_conflicts(self, tmp_path):
        """测试多次冲突情况"""
        # 创建目标文件，触发冲突
        target_path = tmp_path / "test.mp4"
        target_path.write_text("test")

        # 创建多个冲突文件，使用新格式（-{4个随机字符}）
        conflict_suffixes = ["abcd", "efgh", "ijkl", "mnop", "qrst"]
        for suffix in conflict_suffixes:
            conflict_file = tmp_path / f"test-{suffix}.mp4"
            conflict_file.write_text("test")

        # Mock random.choices 模拟多次冲突，最后返回一个不冲突的值
        with patch(
            "j_file_kit.utils.file_utils.random.choices",
            side_effect=[
                ["a", "b", "c", "d"],  # 冲突：test-abcd.mp4 已存在
                ["e", "f", "g", "h"],  # 冲突：test-efgh.mp4 已存在
                ["i", "j", "k", "l"],  # 冲突：test-ijkl.mp4 已存在
                ["m", "n", "o", "p"],  # 冲突：test-mnop.mp4 已存在
                ["q", "r", "s", "t"],  # 冲突：test-qrst.mp4 已存在
                ["u", "v", "w", "x"],  # 不冲突：test-uvwx.mp4 不存在
            ],
        ):
            result = resolve_unique_path(target_path)
            expected = tmp_path / "test-uvwx.mp4"
            assert result == expected

    def test_resolve_unique_path_max_attempts(self, tmp_path):
        """测试最大重试次数"""
        # 创建目标文件，触发冲突
        target_path = tmp_path / "test.mp4"
        target_path.write_text("test")

        # 创建冲突文件
        conflict_file = tmp_path / "test-abcd.mp4"
        conflict_file.write_text("test")

        # Mock random.choices 始终返回相同的值（导致冲突），模拟100次尝试都失败
        with patch(
            "j_file_kit.utils.file_utils.random.choices",
            side_effect=[["a", "b", "c", "d"]] * 100,
        ):
            # 应该抛出异常，因为100次尝试都失败
            with pytest.raises(RuntimeError, match="无法为.*生成唯一路径"):
                resolve_unique_path(target_path)


@pytest.mark.unit
class TestGetFileType:
    """测试文件类型判断函数"""

    def test_get_file_type_video(self):
        """测试视频文件"""
        path = Path("test.mp4")
        video_exts = {".mp4", ".avi", ".mkv"}
        image_exts = {".jpg", ".png"}
        archive_exts = {".zip", ".rar", ".7z"}

        result = get_file_type(path, video_exts, image_exts, archive_exts)
        assert result == FileType.VIDEO

    def test_get_file_type_image(self):
        """测试图片文件"""
        path = Path("test.jpg")
        video_exts = {".mp4", ".avi", ".mkv"}
        image_exts = {".jpg", ".png"}
        archive_exts = {".zip", ".rar", ".7z"}

        result = get_file_type(path, video_exts, image_exts, archive_exts)
        assert result == FileType.IMAGE

    def test_get_file_type_misc(self):
        """测试Misc文件"""
        path = Path("test.txt")
        video_exts = {".mp4", ".avi", ".mkv"}
        image_exts = {".jpg", ".png"}
        archive_exts = {".zip", ".rar", ".7z"}

        result = get_file_type(path, video_exts, image_exts, archive_exts)
        assert result == FileType.MISC

    def test_get_file_type_case_insensitive(self):
        """测试大小写不敏感"""
        path = Path("test.MP4")
        video_exts = {".mp4", ".avi", ".mkv"}
        image_exts = {".jpg", ".png"}
        archive_exts = {".zip", ".rar", ".7z"}

        result = get_file_type(path, video_exts, image_exts, archive_exts)
        assert result == FileType.VIDEO
