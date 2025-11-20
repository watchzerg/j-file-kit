"""文件工具函数单元测试

测试 extract_serial_id, generate_alternative_path 等工具函数。
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from j_file_kit.models.enums import FileType
from j_file_kit.models.value_objects import SerialId
from j_file_kit.utils.file_utils import (
    generate_alternative_path,
    generate_sorted_dir,
    get_file_type,
)


@pytest.mark.unit
class TestGenerateAlternativePath:
    """测试路径生成函数"""

    def test_generate_alternative_path_basic(self):
        """测试基本路径生成"""
        target_path = Path("test.mp4")

        # Mock random.choices 返回固定的随机字符串
        with patch(
            "j_file_kit.utils.file_utils.random.choices",
            return_value=["a", "b", "c", "d"],
        ):
            result = generate_alternative_path(target_path)
            expected = Path("test-jfk-abcd.mp4")
            assert result == expected

    def test_generate_alternative_path_with_existing_suffix(self):
        """测试已带后缀的路径（应提取原始路径）"""
        target_path = Path("test-jfk-a3b2.mp4")

        # Mock random.choices 返回固定的随机字符串
        with patch(
            "j_file_kit.utils.file_utils.random.choices",
            return_value=["x", "y", "z", "1"],
        ):
            result = generate_alternative_path(target_path)
            # 应该基于原始路径 test.mp4 生成，而不是 test-jfk-a3b2.mp4
            expected = Path("test-jfk-xyz1.mp4")
            assert result == expected

    def test_generate_alternative_path_extract_original(self):
        """测试路径提取逻辑"""
        # 测试能正确从 test-jfk-xxxx.mp4 提取出 test.mp4
        target_path = Path("test-jfk-a3b2.mp4")

        with patch(
            "j_file_kit.utils.file_utils.random.choices",
            return_value=["x", "y", "z", "1"],
        ):
            result = generate_alternative_path(target_path)
            # 验证生成的是 test-jfk-xyz1.mp4，而不是 test-jfk-a3b2-jfk-xyz1.mp4
            assert result == Path("test-jfk-xyz1.mp4")
            # 确保不会产生越来越长的路径
            assert "-jfk-" not in result.stem.replace("-jfk-xyz1", "")

    def test_generate_alternative_path_no_suffix(self):
        """测试不带后缀的路径（正常生成）"""
        target_path = Path("test.mp4")

        with patch(
            "j_file_kit.utils.file_utils.random.choices",
            return_value=["1", "2", "3", "4"],
        ):
            result = generate_alternative_path(target_path)
            assert result == Path("test-jfk-1234.mp4")

    def test_generate_alternative_path_with_path(self):
        """测试带完整路径的情况"""
        target_path = Path("/some/dir/test.mp4")

        with patch(
            "j_file_kit.utils.file_utils.random.choices",
            return_value=["a", "b", "c", "d"],
        ):
            result = generate_alternative_path(target_path)
            assert result == Path("/some/dir/test-jfk-abcd.mp4")
            assert result.parent == target_path.parent


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


@pytest.mark.unit
class TestGenerateSortedDir:
    """测试整理目录生成函数"""

    def test_generate_sorted_dir_4_letter_prefix(self):
        """测试4字母前缀的情况"""
        sorted_dir = Path("/sorted")
        serial_id = SerialId(prefix="ABCD", number="123")
        result = generate_sorted_dir(sorted_dir, serial_id)
        expected = Path("/sorted/A/AB/ABCD")
        assert result == expected

    def test_generate_sorted_dir_3_letter_prefix(self):
        """测试3字母前缀的情况"""
        sorted_dir = Path("/sorted")
        serial_id = SerialId(prefix="XYZ", number="456")
        result = generate_sorted_dir(sorted_dir, serial_id)
        expected = Path("/sorted/X/XY/XYZ")
        assert result == expected

    def test_generate_sorted_dir_2_letter_prefix(self):
        """测试2字母前缀的情况"""
        sorted_dir = Path("/sorted")
        serial_id = SerialId(prefix="AB", number="789")
        result = generate_sorted_dir(sorted_dir, serial_id)
        expected = Path("/sorted/A/AB/AB")
        assert result == expected

    def test_generate_sorted_dir_5_letter_prefix(self):
        """测试5字母前缀的情况"""
        sorted_dir = Path("/sorted")
        serial_id = SerialId(prefix="ABCDE", number="123")
        result = generate_sorted_dir(sorted_dir, serial_id)
        expected = Path("/sorted/A/AB/ABCDE")
        assert result == expected
