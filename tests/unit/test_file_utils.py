"""文件工具函数单元测试

测试 extract_serial_id, resolve_unique_path 等工具函数。
"""

import pytest
from pathlib import Path
from unittest.mock import patch

from jfk.utils.file_utils import (
    extract_serial_id,
    resolve_unique_path,
    generate_new_filename,
    find_empty_dirs,
    is_video_or_image,
    get_file_type_from_path
)
from jfk.core.models import FileType


class TestExtractSerialId:
    """测试番号提取函数"""
    
    @pytest.mark.parametrize("filename,expected", [
        # 基本测试用例
        ("ABCD-123.mp4", "ABCD-123"),
        ("abc-001.mp4", "ABC-001"),
        ("prefix_XYZ-999_suffix.mp4", "XYZ-999"),
        
        # 边界测试用例
        ("AB-1.mp4", "AB-1"),                 # 最短2字母
        ("ABCDE-12345.mp4", "ABCDE-12345"),   # 最长5字母
        ("ABCDEF-123.mp4", None),             # 超长无效
        ("no-serial-here.mp4", None),         # 无番号
        
        # 大小写测试
        ("abcd-123.mp4", "ABCD-123"),
        ("AbCd-123.mp4", "ABCD-123"),
        
        # 位置测试
        ("video_ABC-001_hd.mp4", "ABC-001"),
        ("ABC-001_video.mp4", "ABC-001"),
        ("ABC-001.mp4", "ABC-001"),
        
        # 边界情况
        ("", None),
        ("ABC.mp4", None),                    # 缺少数字
        ("123-ABC.mp4", None),                 # 数字在前
        ("ABC-123-456.mp4", "ABC-123"),       # 多个数字，取第一个
    ])
    def test_extract_serial_id(self, filename, expected):
        """测试番号提取"""
        result = extract_serial_id(filename)
        assert result == expected
    
    def test_extract_serial_id_custom_pattern(self):
        """测试自定义正则表达式"""
        # 测试不同的番号格式
        result = extract_serial_id("ABC123.mp4", r"[A-Za-z]{3}\d{3}")
        assert result == "ABC123"
        
        result = extract_serial_id("ABC-123.mp4", r"[A-Za-z]{3}\d{3}")
        assert result is None


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
        
        with patch('jfk.utils.file_utils.random.randint', return_value=1234):
            result = resolve_unique_path(target_path)
            expected = tmp_path / "test-Dup1234.mp4"
            assert result == expected
    
    def test_resolve_unique_path_multiple_conflicts(self, tmp_path):
        """测试多次冲突情况"""
        # 创建多个冲突文件
        for i in range(5):
            conflict_file = tmp_path / f"test-Dup{i:04d}.mp4"
            conflict_file.write_text("test")
        
        target_path = tmp_path / "test.mp4"
        
        # Mock 随机数生成，模拟冲突重试
        with patch('jfk.utils.file_utils.random.randint', side_effect=[1000, 1001, 1002, 1003, 1004, 1005]):
            result = resolve_unique_path(target_path)
            expected = tmp_path / "test-Dup1005.mp4"
            assert result == expected
    
    def test_resolve_unique_path_max_attempts(self, tmp_path):
        """测试最大重试次数"""
        # 创建大量冲突文件
        for i in range(200):
            conflict_file = tmp_path / f"test-Dup{i:04d}.mp4"
            conflict_file.write_text("test")
        
        target_path = tmp_path / "test.mp4"
        
        # 应该抛出异常
        with pytest.raises(RuntimeError, match="无法为.*生成唯一路径"):
            resolve_unique_path(target_path)


class TestGenerateNewFilename:
    """测试新文件名生成函数"""
    
    def test_generate_new_filename_already_at_start(self, tmp_path):
        """测试番号已在开头的情况"""
        original_path = tmp_path / "ABC-001_video.mp4"
        new_path = generate_new_filename(original_path, "ABC-001")
        assert new_path == original_path
    
    def test_generate_new_filename_move_to_start(self, tmp_path):
        """测试番号移动到开头的情况"""
        original_path = tmp_path / "video_ABC-001_hd.mp4"
        new_path = generate_new_filename(original_path, "ABC-001")
        expected = tmp_path / "ABC-001-serialId-hd.mp4"
        assert new_path == expected
    
    def test_generate_new_filename_no_serial_id(self, tmp_path):
        """测试无番号的情况"""
        original_path = tmp_path / "video.mp4"
        new_path = generate_new_filename(original_path, "ABC-001")
        assert new_path == original_path
    
    def test_generate_new_filename_custom_pattern(self, tmp_path):
        """测试自定义正则表达式"""
        original_path = tmp_path / "video_ABC123_hd.mp4"
        new_path = generate_new_filename(original_path, "ABC123", r"[A-Za-z]{3}\d{3}")
        expected = tmp_path / "ABC123-serialId-hd.mp4"
        assert new_path == expected


class TestIsVideoOrImage:
    """测试文件类型判断函数"""
    
    def test_is_video_or_image_video(self):
        """测试视频文件"""
        path = Path("test.mp4")
        video_exts = {".mp4", ".avi", ".mkv"}
        image_exts = {".jpg", ".png"}
        
        result = is_video_or_image(path, video_exts, image_exts)
        assert result == "video"
    
    def test_is_video_or_image_image(self):
        """测试图片文件"""
        path = Path("test.jpg")
        video_exts = {".mp4", ".avi", ".mkv"}
        image_exts = {".jpg", ".png"}
        
        result = is_video_or_image(path, video_exts, image_exts)
        assert result == "image"
    
    def test_is_video_or_image_other(self):
        """测试其他文件"""
        path = Path("test.txt")
        video_exts = {".mp4", ".avi", ".mkv"}
        image_exts = {".jpg", ".png"}
        
        result = is_video_or_image(path, video_exts, image_exts)
        assert result == "other"
    
    def test_is_video_or_image_case_insensitive(self):
        """测试大小写不敏感"""
        path = Path("test.MP4")
        video_exts = {".mp4", ".avi", ".mkv"}
        image_exts = {".jpg", ".png"}
        
        result = is_video_or_image(path, video_exts, image_exts)
        assert result == "video"


class TestGetFileTypeFromPath:
    """测试文件类型枚举获取函数"""
    
    def test_get_file_type_from_path_video(self):
        """测试视频文件类型"""
        path = Path("test.mp4")
        video_exts = {".mp4", ".avi", ".mkv"}
        image_exts = {".jpg", ".png"}
        
        result = get_file_type_from_path(path, video_exts, image_exts)
        assert result == FileType.VIDEO
    
    def test_get_file_type_from_path_image(self):
        """测试图片文件类型"""
        path = Path("test.jpg")
        video_exts = {".mp4", ".avi", ".mkv"}
        image_exts = {".jpg", ".png"}
        
        result = get_file_type_from_path(path, video_exts, image_exts)
        assert result == FileType.IMAGE
    
    def test_get_file_type_from_path_other(self):
        """测试其他文件类型"""
        path = Path("test.txt")
        video_exts = {".mp4", ".avi", ".mkv"}
        image_exts = {".jpg", ".png"}
        
        result = get_file_type_from_path(path, video_exts, image_exts)
        assert result == FileType.OTHER


class TestFindEmptyDirs:
    """测试空目录查找函数"""
    
    def test_find_empty_dirs_no_empty_dirs(self, tmp_path):
        """测试无空目录的情况"""
        # 创建有文件的目录
        (tmp_path / "file.txt").write_text("test")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "file.txt").write_text("test")
        
        result = find_empty_dirs(tmp_path)
        assert result == []
    
    def test_find_empty_dirs_with_empty_dirs(self, tmp_path):
        """测试有空目录的情况"""
        # 创建空目录结构
        (tmp_path / "empty1").mkdir()
        (tmp_path / "empty2").mkdir()
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "empty3").mkdir()
        
        result = find_empty_dirs(tmp_path)
        # 应该找到所有空目录
        assert len(result) == 3
        assert all(d.name.startswith("empty") for d in result)
    
    def test_find_empty_dirs_nested_structure(self, tmp_path):
        """测试嵌套目录结构"""
        # 创建嵌套目录结构
        (tmp_path / "level1").mkdir()
        (tmp_path / "level1" / "level2").mkdir()
        (tmp_path / "level1" / "level2" / "level3").mkdir()
        
        result = find_empty_dirs(tmp_path)
        # 应该找到所有空目录
        assert len(result) == 3
    
    def test_find_empty_dirs_mixed_structure(self, tmp_path):
        """测试混合目录结构"""
        # 创建混合结构：有些空，有些有文件
        (tmp_path / "empty1").mkdir()
        (tmp_path / "empty2").mkdir()
        (tmp_path / "with_file").mkdir()
        (tmp_path / "with_file" / "file.txt").write_text("test")
        (tmp_path / "empty3").mkdir()
        
        result = find_empty_dirs(tmp_path)
        # 应该只找到空目录
        assert len(result) == 3
        assert all(d.name.startswith("empty") for d in result)
