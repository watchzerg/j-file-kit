"""文件任务工具函数单元测试

测试 file_task/file_ops.py 中的工具函数，覆盖候选文件名生成。
"""

from pathlib import Path

import pytest

from j_file_kit.app.file_task.application.file_ops import generate_alternative_filename


@pytest.mark.unit
class TestGenerateAlternativeFilename:
    """测试 generate_alternative_filename 函数"""

    def test_normal_filename(self) -> None:
        """测试普通文件名生成"""
        path = Path("test.mp4")
        result = generate_alternative_filename(path)

        assert result.parent == path.parent
        assert result.suffix == path.suffix
        assert result.stem.startswith("test-jfk-")
        assert len(result.stem) == len("test-jfk-") + 4  # 4个随机字符

    def test_filename_with_jfk_suffix(self) -> None:
        """测试已带 -jfk-xxxx 后缀的文件名（应基于原始文件名生成）"""
        path = Path("test-jfk-a3b2.mp4")
        result = generate_alternative_filename(path)

        assert result.parent == path.parent
        assert result.suffix == path.suffix
        # 应该基于原始文件名 test.mp4 生成，而不是 test-jfk-a3b2.mp4
        assert result.stem.startswith("test-jfk-")
        assert result.stem != "test-jfk-a3b2"  # 应该是新的随机后缀

    def test_multiple_jfk_suffix_calls(self) -> None:
        """测试多次调用应始终基于原始文件名"""
        path = Path("test.mp4")
        result1 = generate_alternative_filename(path)
        result2 = generate_alternative_filename(result1)
        result3 = generate_alternative_filename(result2)

        # 所有结果都应基于原始文件名 test.mp4
        assert result1.stem.startswith("test-jfk-")
        assert result2.stem.startswith("test-jfk-")
        assert result3.stem.startswith("test-jfk-")
        # 每次生成的随机后缀应该不同（概率极高）
        assert result1.stem != result2.stem
        assert result2.stem != result3.stem

    def test_hidden_file(self) -> None:
        """测试隐藏文件（空 stem）"""
        path = Path(".hidden")
        result = generate_alternative_filename(path)

        assert result.parent == path.parent
        assert result.suffix == ""
        # 空 stem 时使用完整文件名作为基础
        assert result.name.startswith(".hidden-jfk-")
        assert len(result.name) == len(".hidden-jfk-") + 4

    def test_hidden_file_with_jfk_suffix(self) -> None:
        """测试已带 -jfk-xxxx 后缀的隐藏文件"""
        path = Path(".hidden-jfk-a3b2")
        result = generate_alternative_filename(path)

        assert result.parent == path.parent
        assert result.suffix == ""
        # 应该基于原始文件名 .hidden 生成
        assert result.name.startswith(".hidden-jfk-")
        assert result.name != ".hidden-jfk-a3b2"

    def test_file_with_only_extension(self) -> None:
        """测试只有扩展名的文件（如 .mp4）"""
        path = Path(".mp4")
        result = generate_alternative_filename(path)

        assert result.parent == path.parent
        # 对于 .mp4 这样的文件，Path.suffix 返回空字符串
        # 但函数会使用完整文件名 .mp4 作为基础
        assert result.name.startswith(".mp4-jfk-")
        assert len(result.name) == len(".mp4-jfk-") + 4

    def test_preserves_parent_directory(self) -> None:
        """测试保留父目录"""
        path = Path("/some/path/to/test.mp4")
        result = generate_alternative_filename(path)

        assert result.parent == path.parent
        assert result.parent == Path("/some/path/to")

    def test_relative_path(self) -> None:
        """测试相对路径"""
        path = Path("subdir/test.mp4")
        result = generate_alternative_filename(path)

        assert result.parent == path.parent
        assert result.parent == Path("subdir")

    def test_filename_format(self) -> None:
        """测试生成的文件名格式"""
        path = Path("test.mp4")
        result = generate_alternative_filename(path)

        # 验证格式：{原始stem}-jfk-{4个随机字符}{suffix}
        parts = result.stem.split("-jfk-")
        assert len(parts) == 2
        assert parts[0] == "test"
        assert len(parts[1]) == 4
        # 随机字符应为小写字母或数字
        assert all(c in "abcdefghijklmnopqrstuvwxyz0123456789" for c in parts[1])

    def test_complex_filename(self) -> None:
        """测试复杂文件名"""
        path = Path("my-video-file-2024.mp4")
        result = generate_alternative_filename(path)

        assert result.parent == path.parent
        assert result.suffix == path.suffix
        assert result.stem.startswith("my-video-file-2024-jfk-")

    def test_complex_filename_with_jfk_suffix(self) -> None:
        """测试复杂文件名已带 -jfk-xxxx 后缀"""
        path = Path("my-video-file-2024-jfk-xyz1.mp4")
        result = generate_alternative_filename(path)

        assert result.parent == path.parent
        assert result.suffix == path.suffix
        # 应该基于原始文件名 my-video-file-2024.mp4 生成
        assert result.stem.startswith("my-video-file-2024-jfk-")
        assert result.stem != "my-video-file-2024-jfk-xyz1"

    def test_unicode_filename(self) -> None:
        """测试包含 Unicode 字符的文件名"""
        path = Path("测试文件.mp4")
        result = generate_alternative_filename(path)

        assert result.parent == path.parent
        assert result.suffix == path.suffix
        assert result.stem.startswith("测试文件-jfk-")
