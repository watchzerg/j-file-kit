"""JAV 领域工具函数单元测试

测试 jav_utils.py 中的所有函数，包括番号匹配、trim操作、文件名重构和目录生成。
测试文件结构与源文件一一对应。
"""

from pathlib import Path

import pytest

from j_file_kit.models.value_objects import SerialId
from j_file_kit.utils.jav_utils import (
    _match_serial_id,
    generate_jav_filename,
    generate_sorted_dir,
    trim_separators,
)


@pytest.mark.unit
class TestTrimSeparators:
    """测试 trim_separators 函数"""

    def test_trim_spaces(self) -> None:
        """测试去除空格"""
        assert trim_separators("  abc  ") == "abc"
        assert trim_separators("abc") == "abc"
        assert trim_separators("   ") == ""

    def test_trim_hyphens(self) -> None:
        """测试去除连字符"""
        assert trim_separators("---abc---") == "abc"
        assert trim_separators("-abc-") == "abc"
        assert trim_separators("abc-123") == "abc-123"  # 中间的不去除

    def test_trim_underscores(self) -> None:
        """测试去除下划线"""
        assert trim_separators("___abc___") == "abc"
        assert trim_separators("_abc_") == "abc"

    def test_trim_at_symbols(self) -> None:
        """测试去除@符号"""
        assert trim_separators("@@@abc@@@") == "abc"
        assert trim_separators("@abc@") == "abc"

    def test_trim_hash_symbols(self) -> None:
        """测试去除#符号"""
        assert trim_separators("###abc###") == "abc"
        assert trim_separators("#abc#") == "abc"

    def test_trim_mixed_separators(self) -> None:
        """测试去除混合分隔符"""
        assert trim_separators("  _-@#abc#@-_  ") == "abc"
        assert trim_separators("@ABC-001#") == "ABC-001"
        assert trim_separators("  _abc-123_  ") == "abc-123"

    def test_trim_preserves_dots(self) -> None:
        """测试保留点号（点号不应被trim）"""
        assert trim_separators("...ABC-001...") == "...ABC-001..."
        assert trim_separators(".abc.") == ".abc."

    def test_trim_empty_string(self) -> None:
        """测试空字符串"""
        assert trim_separators("") == ""

    def test_trim_only_separators(self) -> None:
        """测试只有分隔符的字符串"""
        assert trim_separators(" -_@#") == ""
        assert trim_separators("   ") == ""

    def test_trim_preserves_internal_separators(self) -> None:
        """测试保留中间的分隔符"""
        assert trim_separators("  abc-123-def  ") == "abc-123-def"
        assert trim_separators("_abc_123_") == "abc_123"


@pytest.mark.unit
class TestMatchSerialId:
    """测试 _match_serial_id 函数"""

    def test_match_standard_format_with_hyphen(self) -> None:
        """测试标准格式（带连字符）"""
        serial_id, match = _match_serial_id("ABC-123")
        assert serial_id is not None
        assert serial_id.prefix == "ABC"
        assert serial_id.number == "123"
        assert match is not None
        assert match.group(0) == "ABC-123"

    def test_match_standard_format_with_underscore(self) -> None:
        """测试标准格式（带下划线）"""
        serial_id, match = _match_serial_id("ABC_123")
        assert serial_id is not None
        assert serial_id.prefix == "ABC"
        assert serial_id.number == "123"

    def test_match_standard_format_no_separator(self) -> None:
        """测试标准格式（无分隔符）"""
        serial_id, match = _match_serial_id("ABC123")
        assert serial_id is not None
        assert serial_id.prefix == "ABC"
        assert serial_id.number == "123"

    def test_match_case_insensitive(self) -> None:
        """测试大小写不敏感"""
        serial_id, match = _match_serial_id("abc-123")
        assert serial_id is not None
        assert serial_id.prefix == "ABC"  # 转换为大写
        assert serial_id.number == "123"

        serial_id2, _ = _match_serial_id("AbC-123")
        assert serial_id2 is not None
        assert serial_id2.prefix == "ABC"

    def test_match_prefix_length_range(self) -> None:
        """测试前缀长度范围（2-5个字母）"""
        # 2个字母
        serial_id, _ = _match_serial_id("AB-123")
        assert serial_id is not None
        assert serial_id.prefix == "AB"

        # 5个字母
        serial_id, _ = _match_serial_id("ABCDE-123")
        assert serial_id is not None
        assert serial_id.prefix == "ABCDE"

        # 1个字母（不应匹配）
        serial_id, match = _match_serial_id("A-123")
        assert serial_id is None
        assert match is None

        # 6个字母（不应匹配）
        serial_id, match = _match_serial_id("ABCDEF-123")
        assert serial_id is None
        assert match is None

    def test_match_number_length_range(self) -> None:
        """测试数字长度范围（2-5个数字）"""
        # 2个数字
        serial_id, _ = _match_serial_id("ABC-12")
        assert serial_id is not None
        assert serial_id.number == "12"

        # 5个数字
        serial_id, _ = _match_serial_id("ABC-12345")
        assert serial_id is not None
        assert serial_id.number == "12345"

        # 1个数字（不应匹配）
        serial_id, match = _match_serial_id("ABC-1")
        assert serial_id is None
        assert match is None

        # 6个数字（不应匹配）
        serial_id, match = _match_serial_id("ABC-123456")
        assert serial_id is None
        assert match is None

    def test_match_boundary_conditions(self) -> None:
        """测试边界条件（前后不能紧挨字母/数字）"""
        # 前面有非字母字符（应匹配）
        serial_id, _ = _match_serial_id("_ABC-123")
        assert serial_id is not None

        # 后面有非数字字符（应匹配）
        serial_id, _ = _match_serial_id("ABC-123_")
        assert serial_id is not None

        # 在字符串开头（应匹配，因为前面没有字母）
        serial_id, _ = _match_serial_id("ABC-123")
        assert serial_id is not None

        # 在字符串末尾（应匹配，因为后面没有数字）
        serial_id, _ = _match_serial_id("ABC-123")
        assert serial_id is not None

        # 注意：正则表达式 (?<![a-zA-Z]) 和 (?![0-9]) 只检查匹配位置前后的字符
        # 如果整个匹配在字符串开头/末尾，边界条件会满足
        # 例如 "aABC-123" 会匹配整个字符串（因为 "aABC" 前面没有字母）
        # 例如 "ABC-1234" 会匹配整个字符串（因为 "1234" 后面没有数字）

    def test_match_in_filename(self) -> None:
        """测试在文件名中匹配"""
        serial_id, match = _match_serial_id("video_ABC-001_hd.mp4")
        assert serial_id is not None
        assert serial_id.prefix == "ABC"
        assert serial_id.number == "001"
        assert match is not None
        assert match.span() == (6, 13)  # "ABC-001" 的位置

    def test_match_first_occurrence(self) -> None:
        """测试匹配第一个出现的番号"""
        serial_id, match = _match_serial_id("ABC-001_XYZ-002")
        assert serial_id is not None
        assert serial_id.prefix == "ABC"
        assert serial_id.number == "001"
        assert match is not None
        assert match.group(0) == "ABC-001"

    def test_no_match(self) -> None:
        """测试无匹配情况"""
        serial_id, match = _match_serial_id("no_serial.mp4")
        assert serial_id is None
        assert match is None

        serial_id, match = _match_serial_id("")
        assert serial_id is None
        assert match is None

    def test_custom_pattern(self) -> None:
        """测试自定义正则模式"""
        custom_pattern = r"([A-Z]{3})(\d{3})"
        serial_id, match = _match_serial_id("ABC123", pattern=custom_pattern)
        assert serial_id is not None
        assert serial_id.prefix == "ABC"
        assert serial_id.number == "123"


@pytest.mark.unit
class TestGenerateJavFilename:
    """测试 generate_jav_filename 函数"""

    def test_serial_at_start_no_part3(self) -> None:
        """测试番号在开头，第3部分为空"""
        path = Path("ABC-001.mp4")
        new_path, serial_id = generate_jav_filename(path)
        assert new_path.name == "ABC-001.mp4"
        assert serial_id is not None
        assert serial_id.prefix == "ABC"
        assert serial_id.number == "001"

    def test_serial_at_start_with_part3(self) -> None:
        """测试番号在开头，第3部分不为空"""
        path = Path("ABC-001_video.mp4")
        new_path, serial_id = generate_jav_filename(path)
        assert new_path.name == "ABC-001 video.mp4"
        assert serial_id is not None

    def test_serial_at_start_with_part3_trimmed(self) -> None:
        """测试番号在开头，第3部分需要trim"""
        path = Path("ABC-001__video__.mp4")
        new_path, serial_id = generate_jav_filename(path)
        assert new_path.name == "ABC-001 video.mp4"
        assert serial_id is not None

    def test_serial_not_at_start_no_part3(self) -> None:
        """测试番号不在开头，第3部分为空"""
        path = Path("video_ABC-001.mp4")
        new_path, serial_id = generate_jav_filename(path)
        assert new_path.name == "ABC-001 video-serialId.mp4"
        assert serial_id is not None

    def test_serial_not_at_start_with_part3(self) -> None:
        """测试番号不在开头，第3部分不为空"""
        path = Path("video_ABC-001_hd.mp4")
        new_path, serial_id = generate_jav_filename(path)
        assert new_path.name == "ABC-001 video-serialId-hd.mp4"
        assert serial_id is not None

    def test_serial_not_at_start_with_part3_trimmed(self) -> None:
        """测试番号不在开头，第3部分需要trim"""
        path = Path("video_ABC-001__hd__.mp4")
        new_path, serial_id = generate_jav_filename(path)
        assert new_path.name == "ABC-001 video-serialId-hd.mp4"
        assert serial_id is not None

    def test_serial_not_at_start_part1_trimmed(self) -> None:
        """测试番号不在开头，第1部分需要trim"""
        path = Path("__video__ABC-001_hd.mp4")
        new_path, serial_id = generate_jav_filename(path)
        assert new_path.name == "ABC-001 video-serialId-hd.mp4"
        assert serial_id is not None

    def test_serial_with_underscore_separator(self) -> None:
        """测试下划线分隔的番号"""
        path = Path("ABC_001_video.mp4")
        new_path, serial_id = generate_jav_filename(path)
        assert new_path.name == "ABC-001 video.mp4"  # 标准化为连字符
        assert serial_id is not None
        assert serial_id.prefix == "ABC"
        assert serial_id.number == "001"

    def test_serial_without_separator(self) -> None:
        """测试无分隔符的番号"""
        path = Path("ABC001_video.mp4")
        new_path, serial_id = generate_jav_filename(path)
        assert new_path.name == "ABC-001 video.mp4"  # 标准化为连字符
        assert serial_id is not None

    def test_serial_case_insensitive(self) -> None:
        """测试大小写不敏感的番号匹配"""
        path = Path("abc-001_video.mp4")
        new_path, serial_id = generate_jav_filename(path)
        assert new_path.name == "ABC-001 video.mp4"  # 标准化为大写
        assert serial_id is not None
        assert serial_id.prefix == "ABC"

    def test_no_serial_id(self) -> None:
        """测试无番号的文件名"""
        path = Path("no_serial.mp4")
        new_path, serial_id = generate_jav_filename(path)
        assert new_path == path  # 保持原路径
        assert serial_id is None

    def test_no_extension(self) -> None:
        """测试无扩展名的文件名"""
        path = Path("ABC-001_video")
        new_path, serial_id = generate_jav_filename(path)
        assert new_path.name == "ABC-001 video"
        assert serial_id is not None

    def test_complex_separators(self) -> None:
        """测试复杂分隔符场景"""
        # 第1部分和第3部分都有多种分隔符
        path = Path("  _video_  ABC-001  _hd_  .mp4")
        new_path, serial_id = generate_jav_filename(path)
        assert new_path.name == "ABC-001 video-serialId-hd.mp4"
        assert serial_id is not None

    def test_at_and_hash_symbols(self) -> None:
        """测试@和#符号的处理"""
        path = Path("@video@ABC-001#hd#.mp4")
        new_path, serial_id = generate_jav_filename(path)
        assert new_path.name == "ABC-001 video-serialId-hd.mp4"
        assert serial_id is not None

    def test_preserves_parent_directory(self) -> None:
        """测试保留父目录"""
        path = Path("/some/path/ABC-001_video.mp4")
        new_path, serial_id = generate_jav_filename(path)
        assert new_path.parent == path.parent
        assert new_path.name == "ABC-001 video.mp4"
        assert serial_id is not None

    def test_multiple_dots_in_filename(self) -> None:
        """测试文件名中包含多个点号"""
        path = Path("ABC-001_video.1080p.mp4")
        new_path, serial_id = generate_jav_filename(path)
        # 应该只识别最后一个点号作为扩展名
        assert new_path.suffix == ".mp4"
        assert serial_id is not None

    def test_serial_at_start_empty_part3_after_trim(self) -> None:
        """测试番号在开头，第3部分trim后为空（但原始不为空）"""
        path = Path("ABC-001___.mp4")
        new_path, serial_id = generate_jav_filename(path)
        assert new_path.name == "ABC-001.mp4"
        assert serial_id is not None

    def test_serial_not_at_start_empty_part3_after_trim(self) -> None:
        """测试番号不在开头，第3部分trim后为空（但原始不为空）"""
        path = Path("video_ABC-001___.mp4")
        new_path, serial_id = generate_jav_filename(path)
        assert new_path.name == "ABC-001 video-serialId.mp4"
        assert serial_id is not None

    def test_serial_with_different_prefix_lengths(self) -> None:
        """测试不同长度的前缀"""
        # 2个字母
        path = Path("AB-001_video.mp4")
        new_path, serial_id = generate_jav_filename(path)
        assert new_path.name == "AB-001 video.mp4"
        assert serial_id is not None
        assert serial_id.prefix == "AB"

        # 5个字母
        path = Path("ABCDE-001_video.mp4")
        new_path, serial_id = generate_jav_filename(path)
        assert new_path.name == "ABCDE-001 video.mp4"
        assert serial_id is not None
        assert serial_id.prefix == "ABCDE"

    def test_serial_with_different_number_lengths(self) -> None:
        """测试不同长度的数字"""
        # 2个数字
        path = Path("ABC-12_video.mp4")
        new_path, serial_id = generate_jav_filename(path)
        assert new_path.name == "ABC-12 video.mp4"
        assert serial_id is not None
        assert serial_id.number == "12"

        # 5个数字
        path = Path("ABC-12345_video.mp4")
        new_path, serial_id = generate_jav_filename(path)
        assert new_path.name == "ABC-12345 video.mp4"
        assert serial_id is not None
        assert serial_id.number == "12345"


@pytest.mark.unit
class TestGenerateSortedDir:
    """测试 generate_sorted_dir 函数"""

    def test_prefix_length_2(self) -> None:
        """测试2个字符的前缀"""
        sorted_dir = Path("/sorted")
        serial_id = SerialId(prefix="AB", number="123")
        result = generate_sorted_dir(sorted_dir, serial_id)

        assert result == Path("/sorted/A/AB/AB")
        assert result.parent == Path("/sorted/A/AB")
        assert result.parent.parent == Path("/sorted/A")
        assert result.parent.parent.parent == sorted_dir

    def test_prefix_length_3(self) -> None:
        """测试3个字符的前缀"""
        sorted_dir = Path("/sorted")
        serial_id = SerialId(prefix="ABC", number="123")
        result = generate_sorted_dir(sorted_dir, serial_id)

        assert result == Path("/sorted/A/AB/ABC")

    def test_prefix_length_4(self) -> None:
        """测试4个字符的前缀"""
        sorted_dir = Path("/sorted")
        serial_id = SerialId(prefix="ABCD", number="123")
        result = generate_sorted_dir(sorted_dir, serial_id)

        assert result == Path("/sorted/A/AB/ABCD")

    def test_prefix_length_5(self) -> None:
        """测试5个字符的前缀"""
        sorted_dir = Path("/sorted")
        serial_id = SerialId(prefix="ABCDE", number="123")
        result = generate_sorted_dir(sorted_dir, serial_id)

        assert result == Path("/sorted/A/AB/ABCDE")

    def test_different_first_letters(self) -> None:
        """测试不同首字母"""
        sorted_dir = Path("/sorted")

        serial_id1 = SerialId(prefix="ABC", number="123")
        result1 = generate_sorted_dir(sorted_dir, serial_id1)
        assert result1 == Path("/sorted/A/AB/ABC")

        serial_id2 = SerialId(prefix="XYZ", number="456")
        result2 = generate_sorted_dir(sorted_dir, serial_id2)
        assert result2 == Path("/sorted/X/XY/XYZ")

        serial_id3 = SerialId(prefix="MNO", number="789")
        result3 = generate_sorted_dir(sorted_dir, serial_id3)
        assert result3 == Path("/sorted/M/MN/MNO")

    def test_relative_sorted_dir(self) -> None:
        """测试相对路径的整理目录"""
        sorted_dir = Path("sorted")
        serial_id = SerialId(prefix="ABC", number="123")
        result = generate_sorted_dir(sorted_dir, serial_id)

        assert result == Path("sorted/A/AB/ABC")

    def test_custom_sorted_dir(self) -> None:
        """测试自定义整理目录路径"""
        sorted_dir = Path("/custom/path/to/sorted")
        serial_id = SerialId(prefix="XYZ", number="456")
        result = generate_sorted_dir(sorted_dir, serial_id)

        assert result == Path("/custom/path/to/sorted/X/XY/XYZ")
        assert result.parent.parent.parent == sorted_dir

    def test_path_structure(self) -> None:
        """测试路径结构正确性"""
        sorted_dir = Path("/sorted")
        serial_id = SerialId(prefix="ABCD", number="123")
        result = generate_sorted_dir(sorted_dir, serial_id)

        # 验证路径层级结构
        assert result.name == "ABCD"
        assert result.parent.name == "AB"
        assert result.parent.parent.name == "A"
        assert result.parent.parent.parent == sorted_dir

    def test_number_not_used(self) -> None:
        """测试数字部分不影响目录生成"""
        sorted_dir = Path("/sorted")
        serial_id1 = SerialId(prefix="ABC", number="123")
        serial_id2 = SerialId(prefix="ABC", number="999")

        result1 = generate_sorted_dir(sorted_dir, serial_id1)
        result2 = generate_sorted_dir(sorted_dir, serial_id2)

        # 相同前缀应生成相同路径
        assert result1 == result2
        assert result1 == Path("/sorted/A/AB/ABC")
