"""文件工具函数单元测试

测试 extract_serial_id, resolve_unique_path 等工具函数。
"""

import pytest
from pathlib import Path
from unittest.mock import patch

from jfk.utils.file_utils import (
    resolve_unique_path,
    find_empty_dirs,
    is_video_or_image,
    get_file_type_from_path
)
from jfk.core.models import FileType



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
