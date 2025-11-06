"""正则表达式模式单元测试

测试番号提取相关的正则表达式功能，包括：
- extract_serial_id 函数的各种模式匹配
- 支持多种番号格式：连字符分隔、下划线分隔、无分隔符

番号规则（基于正则表达式：`(?<![a-zA-Z])([a-zA-Z]{2,5})[-_]?(\\d{2,5})(?![0-9])`）：
- 字母部分：2-5个英文字母（大小写都可以）
- 分隔符：可选，支持 `-`、`_` 或无分隔符
- 数字部分：2-5个数字
- 边界条件：
  - 前面不能紧挨着字母（使用负向后查找 `(?<![a-zA-Z])`）
  - 后面不能紧挨着数字（使用负向前查找 `(?![0-9])`）
- 输出格式：统一标准化为 `字母-数字` 格式（大写字母）

示例：
- `ABC-123.mp4` → `ABC-123`
- `ABC_123.mp4` → `ABC-123`
- `ABC123.mp4` → `ABC-123`
- `video_ABC-001_hd.mp4` → `ABC-001`
- `XABC-123.mp4` → `XABC-123`（XABC-123是有效的4字母+3数字番号）
"""

import pytest

from j_file_kit.utils.regex_patterns import DEFAULT_SERIAL_PATTERN, extract_serial_id


class TestSerialIdExtraction:
    """测试番号提取功能

    测试各种番号格式的提取，包括：
    - 连字符分隔：ABC-123
    - 下划线分隔：ABC_123
    - 无分隔符：ABC123
    - 边界情况和错误匹配
    """

    @pytest.mark.parametrize(
        "filename,expected",
        [
            # === 基本格式测试 - 应该匹配 ===
            ("ABC-123.mp4", "ABC-123"),  # 连字符分隔
            ("ABC_123.mp4", "ABC-123"),  # 下划线分隔
            ("ABC123.mp4", "ABC-123"),  # 无分隔符
            ("abc-001.mp4", "ABC-001"),  # 小写字母
            ("prefix_XYZ-999_suffix.mp4", "XYZ-999"),  # 复杂文件名
            ("video_ABC-001_hd.mp4", "ABC-001"),  # 中间位置
            ("ABC-001_video.mp4", "ABC-001"),  # 开头位置
            ("ABC-001.mp4", "ABC-001"),  # 只有番号
            # === 长度边界测试 - 应该匹配 ===
            ("AB-12.mp4", "AB-12"),  # 最短：2字母+2数字
            ("ABCDE-12345.mp4", "ABCDE-12345"),  # 最长：5字母+5数字
            ("AB_12.mp4", "AB-12"),  # 最短：2字母+2数字，下划线
            ("AB123.mp4", "AB-123"),  # 最短：2字母+2数字，无分隔符
            ("ABC1234.mp4", "ABC-1234"),  # 3字母+4数字，无分隔符
            # === 大小写测试 - 应该匹配 ===
            ("abcd-123.mp4", "ABCD-123"),  # 全小写
            ("AbCd-123.mp4", "ABCD-123"),  # 混合大小写
            ("abcd123.mp4", "ABCD-123"),  # 无分隔符，混合大小写
            # === 多个匹配 - 应该匹配第一个 ===
            ("ABC-123_DEF-456.mp4", "ABC-123"),  # 多个番号，取第一个
            # === 特殊字符测试 - 应该匹配 ===
            ("ABC-123[HD].mp4", "ABC-123"),  # 方括号
            ("ABC-123(1080p).mp4", "ABC-123"),  # 圆括号
            ("ABC-123_uncensored.mp4", "ABC-123"),  # 下划线后缀
            ("ABC123[HD].mp4", "ABC-123"),  # 无分隔符+特殊字符
            # === 边界条件测试 - 应该匹配 ===
            ("ABC-123ABC.mp4", "ABC-123"),  # 后面是字母（允许）
            ("ABC123-456.mp4", "ABC-123"),  # 前面是数字（允许）
            ("XABC-123.mp4", "XABC-123"),  # XABC-123是有效的4字母+3数字番号
            ("ABC-1234.mp4", "ABC-1234"),  # ABC-1234是有效的3字母+4数字番号
            # === 不应该匹配的情况 ===
            ("", None),  # 空字符串
            ("ABC.mp4", None),  # 缺少数字部分
            ("123.mp4", None),  # 缺少字母部分
            ("no-serial-here.mp4", None),  # 无番号
            ("123-ABC.mp4", None),  # 数字在前
            ("ABCDEF-123456.mp4", None),  # 字母超长（6个）
            ("ABC-123456.mp4", None),  # 数字超长（6个）
            ("ABC123456.mp4", None),  # 无分隔符但数字超长（6个）
            ("A-12.mp4", None),  # 字母太少（1个）
            ("ABC-1.mp4", None),  # 数字太少（1个）
            ("ABCDEF-123.mp4", None),  # 字母超长（6个）
            ("ABC-123456789.mp4", None),  # 数字超长（9个）
        ],
    )
    def test_extract_serial_id_default_pattern(self, filename, expected):
        """测试默认番号提取模式

        使用配置文件中的默认模式：`(?<![a-zA-Z])([a-zA-Z]{2,5})[-_]?(\\d{2,5})(?![0-9])`

        测试用例包括：
        - 基本格式：ABC-123, ABC_123, ABC123
        - 长度边界：最短/最长长度验证
        - 错误匹配：超长字母/数字，边界条件
        - 大小写处理：统一转换为大写
        - 特殊字符：方括号、圆括号等
        - 多个匹配：取第一个匹配的番号
        """
        result = extract_serial_id(filename, DEFAULT_SERIAL_PATTERN)
        assert result == expected


class TestAdvancedEdgeCases:
    """测试高级边界情况

    测试复杂的文件名场景和边界条件：
    - 复杂文件名中的番号提取
    - 分隔符变化处理
    - 长度边界验证
    - 上下文边界检查
    - 大小写敏感性
    """

    def test_complex_filename_scenarios(self):
        """测试复杂文件名场景"""
        pattern = DEFAULT_SERIAL_PATTERN

        # 复杂文件名测试
        test_cases = [
            # === 应该匹配的情况 ===
            ("[2023]ABC-123[1080p][HD].mp4", "ABC-123"),
            ("(Uncensored)ABC-123(Leaked).mp4", "ABC-123"),
            ("ABC-123_v2_Final.mp4", "ABC-123"),
            ("ABC-123-Repack.mp4", "ABC-123"),
            ("ABC-123_Extended_Cut.mp4", "ABC-123"),
            ("ABC123[1080p][HD].mp4", "ABC-123"),  # 无分隔符
            ("ABC123_v2_Final.mp4", "ABC-123"),  # 无分隔符
            # === 不应该匹配的情况 ===
            ("ABCDEF-123456.mp4", None),  # 字母和数字都超长
            ("ABC-123456789.mp4", None),  # 数字超长
            ("ABCDEFGH-123.mp4", None),  # 字母超长
            ("ABC-123456.mp4", None),  # 后面紧挨着数字
            ("ABC123456.mp4", None),  # 无分隔符但数字超长
        ]

        for filename, expected in test_cases:
            result = extract_serial_id(filename, pattern)
            assert result == expected, (
                f"Failed for filename: {filename}, expected: {expected}, got: {result}"
            )

    def test_separator_variations(self):
        """测试分隔符变化"""
        pattern = DEFAULT_SERIAL_PATTERN

        # 测试不同的分隔符
        separator_tests = [
            ("ABC-123.mp4", "ABC-123"),  # 连字符
            ("ABC_123.mp4", "ABC-123"),  # 下划线
            ("ABC123.mp4", "ABC-123"),  # 无分隔符
            ("ABC-123_456.mp4", "ABC-123"),  # 混合分隔符，取第一个
            ("ABC_123-456.mp4", "ABC-123"),  # 混合分隔符，取第一个
        ]

        for filename, expected in separator_tests:
            result = extract_serial_id(filename, pattern)
            assert result == expected, f"Failed for separator test: {filename}"

    def test_length_boundary_validation(self):
        """测试长度边界验证"""
        pattern = DEFAULT_SERIAL_PATTERN

        # 测试字母长度边界
        letter_length_tests = [
            # === 不应该匹配的情况 ===
            ("A-12.mp4", None),  # 1个字母（太少）
            ("ABCDEF-12.mp4", None),  # 6个字母（太多）
            ("A12.mp4", None),  # 1个字母（太少），无分隔符
            ("ABCDEF12.mp4", None),  # 6个字母（太多），无分隔符
            # === 应该匹配的情况 ===
            ("AB-12.mp4", "AB-12"),  # 2个字母（最小）
            ("ABC-12.mp4", "ABC-12"),  # 3个字母
            ("ABCD-12.mp4", "ABCD-12"),  # 4个字母
            ("ABCDE-12.mp4", "ABCDE-12"),  # 5个字母（最大）
            ("AB12.mp4", "AB-12"),  # 2个字母（最小），无分隔符
            ("ABC12.mp4", "ABC-12"),  # 3个字母，无分隔符
            ("ABCD12.mp4", "ABCD-12"),  # 4个字母，无分隔符
            ("ABCDE12.mp4", "ABCDE-12"),  # 5个字母（最大），无分隔符
        ]

        for filename, expected in letter_length_tests:
            result = extract_serial_id(filename, pattern)
            assert result == expected, f"Failed for letter length test: {filename}"

        # 测试数字长度边界
        digit_length_tests = [
            # === 不应该匹配的情况 ===
            ("ABC-1.mp4", None),  # 1个数字（太少）
            ("ABC-123456.mp4", None),  # 6个数字（太多）
            ("ABC1.mp4", None),  # 1个数字（太少），无分隔符
            ("ABC123456.mp4", None),  # 6个数字（太多），无分隔符
            # === 应该匹配的情况 ===
            ("ABC-12.mp4", "ABC-12"),  # 2个数字（最小）
            ("ABC-123.mp4", "ABC-123"),  # 3个数字
            ("ABC-1234.mp4", "ABC-1234"),  # 4个数字
            ("ABC-12345.mp4", "ABC-12345"),  # 5个数字（最大）
            ("ABC12.mp4", "ABC-12"),  # 2个数字（最小），无分隔符
            ("ABC123.mp4", "ABC-123"),  # 3个数字，无分隔符
            ("ABC1234.mp4", "ABC-1234"),  # 4个数字，无分隔符
            ("ABC12345.mp4", "ABC-12345"),  # 5个数字（最大），无分隔符
        ]

        for filename, expected in digit_length_tests:
            result = extract_serial_id(filename, pattern)
            assert result == expected, f"Failed for digit length test: {filename}"

    def test_context_boundary_validation(self):
        """测试上下文边界验证"""
        pattern = DEFAULT_SERIAL_PATTERN

        # 测试前后边界
        boundary_tests = [
            # === 应该匹配的情况 ===
            ("ABC-123.mp4", "ABC-123"),  # 正常情况
            ("1ABC-123.mp4", "ABC-123"),  # 前面是数字
            ("_ABC-123.mp4", "ABC-123"),  # 前面是下划线
            ("-ABC-123.mp4", "ABC-123"),  # 前面是连字符
            (" ABC-123.mp4", "ABC-123"),  # 前面是空格
            ("XABC-123.mp4", "XABC-123"),  # XABC-123是有效的番号（4字母+3数字）
            ("ABC-123X.mp4", "ABC-123"),  # 后面是字母（允许）
            ("ABC-1234.mp4", "ABC-1234"),  # ABC-1234是有效的番号（3字母+4数字）
            ("ABC-123_.mp4", "ABC-123"),  # 后面是下划线
            ("ABC-123-.mp4", "ABC-123"),  # 后面是连字符
            ("ABC-123 .mp4", "ABC-123"),  # 后面是空格
            # === 不应该匹配的情况 ===
            (
                "ZABCDE-123.mp4",
                None,
            ),  # 前面紧挨着字母Z（ZABCDE-123不是有效番号，
            # 因为ZABCDE是6个字母+3数字，字母超长）
        ]

        for filename, expected in boundary_tests:
            result = extract_serial_id(filename, pattern)
            assert result == expected, f"Failed for boundary test: {filename}"


class TestEdgeCasesAndSpecialScenarios:
    """测试边界情况和特殊场景

    测试一些特殊的边界情况和可能被忽略的场景：
    - 文件扩展名变化
    - 特殊字符组合
    - 边界条件的精确验证
    - 性能相关的大文件名测试
    """

    def test_file_extension_variations(self):
        """测试不同文件扩展名"""
        pattern = DEFAULT_SERIAL_PATTERN

        extension_tests = [
            # === 应该匹配的情况 ===
            ("ABC-123.mp4", "ABC-123"),  # 视频文件
            ("ABC-123.avi", "ABC-123"),  # 视频文件
            ("ABC-123.mkv", "ABC-123"),  # 视频文件
            ("ABC-123.jpg", "ABC-123"),  # 图片文件
            ("ABC-123.png", "ABC-123"),  # 图片文件
            ("ABC-123.txt", "ABC-123"),  # 文本文件
            ("ABC-123.zip", "ABC-123"),  # 压缩文件
            ("ABC-123", "ABC-123"),  # 无扩展名
            # === 不应该匹配的情况 ===
            ("ABC.mp4", None),  # 缺少数字
            ("123.mp4", None),  # 缺少字母
        ]

        for filename, expected in extension_tests:
            result = extract_serial_id(filename, pattern)
            assert result == expected, f"Failed for extension test: {filename}"

    def test_special_characters_and_unicode(self):
        """测试特殊字符和Unicode字符"""
        pattern = DEFAULT_SERIAL_PATTERN

        special_char_tests = [
            # === 应该匹配的情况 ===
            ("ABC-123[1080p].mp4", "ABC-123"),  # 方括号
            ("ABC-123(HD).mp4", "ABC-123"),  # 圆括号
            ("ABC-123_uncensored.mp4", "ABC-123"),  # 下划线
            ("ABC-123-Repack.mp4", "ABC-123"),  # 连字符
            ("ABC-123.2023.mp4", "ABC-123"),  # 点号
            ("ABC-123@special.mp4", "ABC-123"),  # @符号
            ("ABC-123#tag.mp4", "ABC-123"),  # #符号
            # === 不应该匹配的情况 ===
            ("ABC-123456.mp4", None),  # 数字超长
            ("ABCDEF-123.mp4", None),  # 字母超长
        ]

        for filename, expected in special_char_tests:
            result = extract_serial_id(filename, pattern)
            assert result == expected, f"Failed for special char test: {filename}"

    def test_performance_with_long_filenames(self):
        """测试长文件名的性能"""
        pattern = DEFAULT_SERIAL_PATTERN

        # 生成很长的文件名
        long_prefix = "very_long_prefix_" * 50
        long_suffix = "_very_long_suffix" * 50

        long_filename_tests = [
            # === 应该匹配的情况 ===
            (f"{long_prefix}ABC-123{long_suffix}.mp4", "ABC-123"),
            (f"{long_prefix}XYZ-999{long_suffix}.mp4", "XYZ-999"),
            # === 不应该匹配的情况 ===
            (f"{long_prefix}no_serial_here{long_suffix}.mp4", None),
        ]

        for filename, expected in long_filename_tests:
            result = extract_serial_id(filename, pattern)
            assert result == expected, "Failed for long filename test"

    def test_multiple_serial_ids_in_filename(self):
        """测试文件名中包含多个番号的情况"""
        pattern = DEFAULT_SERIAL_PATTERN

        multiple_serial_tests = [
            # === 应该匹配第一个番号 ===
            ("ABC-123_DEF-456.mp4", "ABC-123"),  # 两个番号，取第一个
            ("XYZ-999_ABC-123_GHI-789.mp4", "XYZ-999"),  # 三个番号，取第一个
            ("ABC-123-456_DEF-789.mp4", "ABC-123"),  # 混合分隔符，取第一个
        ]

        for filename, expected in multiple_serial_tests:
            result = extract_serial_id(filename, pattern)
            assert result == expected, f"Failed for multiple serial test: {filename}"

    def test_case_insensitive_matching(self):
        """测试大小写不敏感的匹配"""
        pattern = DEFAULT_SERIAL_PATTERN

        case_tests = [
            # === 应该匹配的情况 ===
            ("abc-123.mp4", "ABC-123"),  # 全小写
            ("ABC-123.mp4", "ABC-123"),  # 全大写
            ("AbC-123.mp4", "ABC-123"),  # 混合大小写
            ("aBc-123.mp4", "ABC-123"),  # 混合大小写
            ("AbCdE-12345.mp4", "ABCDE-12345"),  # 长混合大小写
            ("abc123.mp4", "ABC-123"),  # 无分隔符，小写
            ("ABC123.mp4", "ABC-123"),  # 无分隔符，大写
            ("AbC123.mp4", "ABC-123"),  # 无分隔符，混合大小写
        ]

        for filename, expected in case_tests:
            result = extract_serial_id(filename, pattern)
            assert result == expected, f"Failed for case test: {filename}"
            assert result.isupper(), f"Result should be uppercase: {result}"
