"""JAV 文件名工具单元测试

覆盖 generate_jav_filename、generate_sorted_dir。
"""

from pathlib import Path

import pytest

from j_file_kit.app.file_task.application.jav_filename_util import (
    MAX_FILENAME_BYTES,
    _truncate_to_bytes,
    build_serial_pattern,
    generate_jav_filename,
    generate_sorted_dir,
)
from j_file_kit.app.file_task.domain.models import SerialId

pytestmark = pytest.mark.unit


class TestGenerateJavFilename:
    """generate_jav_filename 文件名重构"""

    def test_serial_at_start_with_part3(self) -> None:
        new_name, serial_id = generate_jav_filename("ABC-001_video.mp4")
        assert new_name == "ABC-001 video.mp4"
        assert serial_id is not None
        assert serial_id.prefix == "ABC"
        assert serial_id.number == "001"

    def test_serial_at_start_part3_empty(self) -> None:
        new_name, serial_id = generate_jav_filename("ABC-001.mp4")
        assert new_name == "ABC-001.mp4"
        assert serial_id is not None

    def test_serial_not_at_start_part3_empty(self) -> None:
        new_name, serial_id = generate_jav_filename("prefix_ABC-001.mp4")
        assert new_name == "ABC-001 prefix-serialId.mp4"
        assert serial_id is not None

    def test_serial_not_at_start_with_part3(self) -> None:
        new_name, serial_id = generate_jav_filename("video_ABC-001_hd.mp4")
        assert new_name == "ABC-001 video-serialId-hd.mp4"
        assert serial_id is not None

    def test_no_serial_returns_original(self) -> None:
        new_name, serial_id = generate_jav_filename("no_serial_here.mp4")
        assert new_name == "no_serial_here.mp4"
        assert serial_id is None

    def test_trim_separators(self) -> None:
        new_name, _ = generate_jav_filename("  -  ABC-001  -  suffix  .mp4")
        assert "ABC-001" in new_name
        assert new_name.startswith("ABC-001")

    def test_underscore_separator(self) -> None:
        new_name, serial_id = generate_jav_filename("ABC_123.mp4")
        assert serial_id is not None
        assert serial_id.prefix == "ABC"
        assert serial_id.number == "123"
        assert new_name == "ABC-123.mp4"

    def test_lowercase_serial_normalized(self) -> None:
        new_name, serial_id = generate_jav_filename("abc-123.mp4")
        assert serial_id is not None
        assert serial_id.prefix == "ABC"
        assert new_name == "ABC-123.mp4"


class TestTruncateToBytes:
    """_truncate_to_bytes 内部辅助函数"""

    def test_short_text_unchanged(self) -> None:
        assert _truncate_to_bytes("hello", 10) == "hello"

    def test_exact_limit_unchanged(self) -> None:
        # "abc" 恰好 3 字节，等于上限时原样返回
        text = "abc"
        assert _truncate_to_bytes(text, 3) == text

    def test_ascii_truncation(self) -> None:
        result = _truncate_to_bytes("abcdef", 3)
        assert result == "abc"

    def test_multibyte_cut_at_exact_boundary(self) -> None:
        # "ab中" = 5 字节；上限恰好 5 时完整保留
        # "ab中文" encode: \x61\x62 \xe4\xb8\xad \xe6\x96\x87
        result = _truncate_to_bytes("ab中文", 5)
        assert result == "ab中"
        assert len(result.encode()) == 5

    def test_multibyte_cut_in_middle_drops_incomplete_char(self) -> None:
        # 上限 4 字节：截断后 b'\x61\x62\xe4\xb8' 末尾的 \xe4\xb8 是不完整的 "中"，
        # errors="ignore" 丢弃，结果为 "ab"
        result = _truncate_to_bytes("ab中文", 4)
        assert result == "ab"
        assert len(result.encode()) == 2

    def test_multibyte_cut_one_byte_before_boundary(self) -> None:
        # 上限 4 同理：\xe4 单独是无效 UTF-8 首字节，被丢弃
        result = _truncate_to_bytes("ab中", 4)
        assert result == "ab"

    def test_zero_limit_returns_empty(self) -> None:
        assert _truncate_to_bytes("abc", 0) == ""

    def test_negative_limit_returns_empty(self) -> None:
        assert _truncate_to_bytes("abc", -1) == ""


class TestGenerateJavFilenameByteLimit:
    """generate_jav_filename 超 255 字节时的截断行为"""

    def test_real_world_long_filename_truncated(self) -> None:
        """复现实际 bug：番号不在开头，part3 过长导致生成文件名超限。

        原始 252 字节的文件名，经过重构后生成 261 字节，超过 255 字节限制。
        修复后：保留 (Unc Leak)（part1 完整），从 part3 末尾截断，精确输出 255 字节。
        """
        filename = (
            "(Unc Leak) SDNT-008 寝取らせ願望のある旦那に従い出演させられた本物シロウト人妻"
            " case6 小学校教師・藤川なお（仮名）27歳 輪姦中出し了承 東京都武蔵野市在住"
            " 主人のためにネトラレます.mp4"
        )
        new_name, serial_id = generate_jav_filename(filename)

        assert serial_id is not None
        assert serial_id.prefix == "SDNT"
        assert serial_id.number == "008"
        # 字节精确等于上限（part3 截断后刚好用满 255 字节预算）
        assert len(new_name.encode()) == MAX_FILENAME_BYTES
        # part1 "(Unc Leak)" 完整保留
        assert new_name == (
            "SDNT-008 (Unc Leak)-serialId-寝取らせ願望のある旦那に従い出演させられた本物シロウト人妻"
            " case6 小学校教師・藤川なお（仮名）27歳 輪姦中出し了承 東京都武蔵野市在住 主人のためにネトラレ.mp4"
        )

    def test_serial_at_start_long_part3_truncated(self) -> None:
        """番号在开头，part3 过长时只截断 part3，字节精确用满上限。

        fixed = "ABC-001 .mp4" = 12 字节，剩余 243 字节给 part3。
        100 个"あ"= 300 字节 → 截断为 81 个"あ"= 243 字节，总计 255 字节。
        """
        long_part3 = "あ" * 100
        filename = f"ABC-001 {long_part3}.mp4"
        new_name, serial_id = generate_jav_filename(filename)

        assert serial_id is not None
        assert serial_id.prefix == "ABC"
        assert serial_id.number == "001"
        assert len(new_name.encode()) == MAX_FILENAME_BYTES
        assert new_name == f"ABC-001 {'あ' * 81}.mp4"

    def test_serial_not_at_start_no_part3_long_part1_truncated(self) -> None:
        """番号不在开头且无 part3，part1 过长时截断 part1，占位符和扩展名完整保留。

        fixed = "ABC-001 -serialId.mp4" = 21 字节，剩余 234 字节给 part1。
        90 个"あ"= 270 字节 → 截断为 78 个"あ"= 234 字节，总计 255 字节。
        """
        long_part1 = "あ" * 90
        filename = f"{long_part1}_ABC-001.mp4"
        new_name, serial_id = generate_jav_filename(filename)

        assert serial_id is not None
        assert serial_id.prefix == "ABC"
        assert serial_id.number == "001"
        assert len(new_name.encode()) == MAX_FILENAME_BYTES
        assert new_name == f"ABC-001 {'あ' * 78}-serialId.mp4"

    def test_serial_not_at_start_both_parts_long_part3_truncated_first(self) -> None:
        """番号不在开头，part1 较短可完整保留，只截断 part3。

        fixed = "ABC-001 -serialId-.mp4" = 22 字节，剩余 233 字节。
        part1 "prefix" = 6 字节，part3 预算 = 227 字节。
        90 个"い"= 270 字节 → 截断为 75 个"い"= 225 字节（227 字节内最多完整字符）。
        总计 22 + 6 + 225 = 253 字节（最后 2 字节因多字节边界无法利用）。
        """
        part1 = "prefix"
        long_part3 = "い" * 90
        filename = f"{part1}_ABC-001_{long_part3}.mp4"
        new_name, serial_id = generate_jav_filename(filename)

        assert serial_id is not None
        assert serial_id.prefix == "ABC"
        assert serial_id.number == "001"
        assert len(new_name.encode()) == 253  # 255 - 2（多字节边界损耗）
        assert new_name == f"ABC-001 prefix-serialId-{'い' * 75}.mp4"

    def test_serial_not_at_start_part1_exceeds_budget_drops_part3(self) -> None:
        """番号不在开头，part1 本身超出预算，丢弃 part3 并截断 part1。

        fixed（含 part3）= "ABC-001 -serialId-.mp4" = 22 字节，剩余 233 字节。
        part1 "う"×90 = 270 字节 > 233 → 触发 else 分支。
        改用 fixed2 = "ABC-001 -serialId.mp4" = 21 字节，剩余 234 字节给 part1。
        截断为 78 个"う"= 234 字节，总计 255 字节；part3 "suffix" 被完全丢弃。
        """
        long_part1 = "う" * 90
        part3 = "suffix"
        filename = f"{long_part1}_ABC-001_{part3}.mp4"
        new_name, serial_id = generate_jav_filename(filename)

        assert serial_id is not None
        assert serial_id.prefix == "ABC"
        assert serial_id.number == "001"
        assert len(new_name.encode()) == MAX_FILENAME_BYTES
        assert new_name == f"ABC-001 {'う' * 78}-serialId.mp4"
        # "suffix" 已被丢弃，不应出现在文件名中
        assert "suffix" not in new_name

    def test_within_limit_no_truncation(self) -> None:
        """文件名未超限时，输出与不加截断逻辑时完全一致"""
        new_name, serial_id = generate_jav_filename("(prefix) ABC-001 suffix.mp4")
        assert serial_id is not None
        assert serial_id.prefix == "ABC"
        assert serial_id.number == "001"
        assert new_name == "ABC-001 (prefix)-serialId-suffix.mp4"
        assert len(new_name.encode()) <= MAX_FILENAME_BYTES

    def test_within_limit_serial_at_start(self) -> None:
        """番号在开头且未超限时，原样保留 part3，不做截断"""
        new_name, serial_id = generate_jav_filename("SDNT-008 some description.mp4")
        assert serial_id is not None
        assert serial_id.prefix == "SDNT"
        assert serial_id.number == "008"
        assert new_name == "SDNT-008 some description.mp4"
        assert len(new_name.encode()) <= MAX_FILENAME_BYTES


class TestBuildSerialPattern:
    """build_serial_pattern 可配置番号正则构建"""

    def test_single_combination_matches_exact(self) -> None:
        """给定单一组合 (3,3)，恰好 3字母+3数字命中"""
        p = build_serial_pattern([(3, 3)])
        assert p.search("ABC-123") is not None

    def test_single_combination_rejects_shorter_letters(self) -> None:
        """2字母+3数字在只含 (3,3) 的组合中不命中"""
        p = build_serial_pattern([(3, 3)])
        assert p.search("AB-123") is None

    def test_single_combination_rejects_longer_letters(self) -> None:
        """4字母+3数字在只含 (3,3) 的组合中不命中"""
        p = build_serial_pattern([(3, 3)])
        assert p.search("ABCD-123") is None

    def test_single_combination_rejects_wrong_digit_count(self) -> None:
        """3字母+4数字在只含 (3,3) 的组合中不命中"""
        p = build_serial_pattern([(3, 3)])
        assert p.search("ABC-1234") is None

    def test_multiple_combinations_match_all(self) -> None:
        """[(3,3),(4,3)] 中两种组合均命中"""
        p = build_serial_pattern([(3, 3), (4, 3)])
        assert p.search("ABC-123") is not None
        assert p.search("ABCD-123") is not None

    def test_multiple_combinations_rejects_unlisted(self) -> None:
        """[(3,3),(4,3)] 中未列出的 5字母+3数字不命中"""
        p = build_serial_pattern([(3, 3), (4, 3)])
        assert p.search("ABCDE-123") is None

    def test_case_insensitive(self) -> None:
        """大小写不敏感：小写字母也能命中"""
        p = build_serial_pattern([(3, 3)])
        assert p.search("abc-123") is not None
        assert p.search("Abc-123") is not None

    def test_no_separator(self) -> None:
        """无分隔符也能命中"""
        p = build_serial_pattern([(3, 3)])
        assert p.search("ABC123") is not None

    def test_underscore_separator(self) -> None:
        """下划线分隔符能命中"""
        p = build_serial_pattern([(3, 3)])
        assert p.search("ABC_123") is not None

    def test_boundary_letter_before_not_match(self) -> None:
        """字母紧前时不命中（前置负向后视边界）"""
        p = build_serial_pattern([(3, 3)])
        # "XABC-123" 中 "ABC" 前面紧接字母 "X"，不应命中
        assert p.search("XABC-123") is None

    def test_boundary_digit_after_not_match(self) -> None:
        """数字紧后时不命中（后置负向前视边界）"""
        p = build_serial_pattern([(3, 3)])
        # "ABC-1234" 的 "123" 后面紧接数字 "4"，不应命中
        assert p.search("ABC-1234") is None

    def test_empty_combinations_raises(self) -> None:
        """空组合列表抛 ValueError"""
        with pytest.raises(ValueError, match="不能为空"):
            build_serial_pattern([])

    def test_non_positive_value_raises(self) -> None:
        """含零或负数的组合抛 ValueError"""
        with pytest.raises(ValueError, match="正整数"):
            build_serial_pattern([(0, 3)])
        with pytest.raises(ValueError, match="正整数"):
            build_serial_pattern([(3, -1)])

    def test_generate_jav_filename_with_custom_pattern(self) -> None:
        """generate_jav_filename 使用自定义 pattern 只识别指定组合"""
        p = build_serial_pattern([(4, 3)])
        # 4字母+3数字的文件名能识别
        new_name, sid = generate_jav_filename("ABCD-001_video.mp4", pattern=p)
        assert sid is not None
        assert sid.prefix == "ABCD"
        assert new_name == "ABCD-001 video.mp4"

        # 3字母+3数字的文件名不能识别，返回原名
        new_name2, sid2 = generate_jav_filename("ABC-001_video.mp4", pattern=p)
        assert sid2 is None
        assert new_name2 == "ABC-001_video.mp4"


class TestGenerateSortedDir:
    """generate_sorted_dir 子目录路径生成"""

    def test_four_letter_prefix(self) -> None:
        sid = SerialId(prefix="ABCD", number="123")
        result = generate_sorted_dir(sid)
        assert result == Path("A/AB/ABCD")

    def test_three_letter_prefix(self) -> None:
        sid = SerialId(prefix="XYZ", number="456")
        result = generate_sorted_dir(sid)
        assert result == Path("X/XY/XYZ")

    def test_two_letter_prefix(self) -> None:
        sid = SerialId(prefix="AB", number="789")
        result = generate_sorted_dir(sid)
        assert result == Path("A/AB/AB")

    def test_five_letter_prefix(self) -> None:
        sid = SerialId(prefix="ABCDE", number="00001")
        result = generate_sorted_dir(sid)
        assert result == Path("A/AB/ABCDE")
