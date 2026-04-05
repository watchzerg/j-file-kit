"""JAV 文件名工具单元测试

覆盖 generate_jav_filename、generate_sorted_dir。
"""

from pathlib import Path

import pytest

from j_file_kit.app.file_task.application.jav_filename_util import (
    MAX_FILENAME_BYTES,
    _match_serial_id,
    _truncate_to_bytes,
    generate_jav_filename,
    generate_sorted_dir,
    strip_jav_filename_noise,
)
from j_file_kit.app.file_task.domain.models import SerialId

pytestmark = pytest.mark.unit

# 显式传入 strip 时测站标去噪（示例使用 BBS-2048，与默认 YAML 清单中该项一致）
_TEST_STRIP_BBS_2048: tuple[str, ...] = ("BBS-2048",)


class TestGenerateJavFilename:
    """generate_jav_filename 文件名重构"""

    def test_serial_at_start_with_part3(self) -> None:
        new_name, serial_id = generate_jav_filename("ABC-100_video.mp4")
        assert new_name == "ABC-100 video.mp4"
        assert serial_id is not None
        assert serial_id.prefix == "ABC"
        assert serial_id.number == "100"

    def test_serial_at_start_part3_empty(self) -> None:
        new_name, serial_id = generate_jav_filename("ABC-100.mp4")
        assert new_name == "ABC-100.mp4"
        assert serial_id is not None

    def test_serial_not_at_start_part3_empty(self) -> None:
        new_name, serial_id = generate_jav_filename("prefix_ABC-100.mp4")
        assert new_name == "ABC-100 prefix-serialId.mp4"
        assert serial_id is not None

    def test_serial_not_at_start_with_part3(self) -> None:
        new_name, serial_id = generate_jav_filename("video_ABC-100_hd.mp4")
        assert new_name == "ABC-100 video-serialId-hd.mp4"
        assert serial_id is not None

    def test_no_serial_returns_original(self) -> None:
        new_name, serial_id = generate_jav_filename("no_serial_here.mp4")
        assert new_name == "no_serial_here.mp4"
        assert serial_id is None

    def test_trim_separators(self) -> None:
        new_name, _ = generate_jav_filename("  -  ABC-100  -  suffix  .mp4")
        assert "ABC-100" in new_name
        assert new_name.startswith("ABC-100")

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

    def test_strip_site_noise_avoids_false_serial(self) -> None:
        """站标子串误识别为番号：去噪后无有效番号则返回原名（不去噪）。"""
        raw = "foo_bbs-2048.com_bar.mp4"
        new_name, serial_id = generate_jav_filename(
            raw,
            strip_substrings=_TEST_STRIP_BBS_2048,
        )
        assert serial_id is None
        assert new_name == raw

    def test_strip_site_noise_then_match_keeps_output_clean(self) -> None:
        """去噪后匹配真实番号，输出不含站标子串。"""
        new_name, serial_id = generate_jav_filename(
            "site_bbs-2048.com_ABC-123.mp4",
            strip_substrings=_TEST_STRIP_BBS_2048,
        )
        assert serial_id is not None
        assert serial_id.prefix == "ABC"
        assert "bbs-2048" not in new_name.lower()
        assert new_name == "ABC-123 site_.com-serialId.mp4"

    def test_strip_disabled_restores_legacy_false_positive(self) -> None:
        """strip_substrings 为空时不去噪，bbs-2048 仍可能被识别为 BBS 番号（与未配置该字段一致）。"""
        new_name, serial_id = generate_jav_filename(
            "foo_bbs-2048.com.mp4",
            strip_substrings=(),
        )
        assert serial_id is not None
        assert serial_id.prefix == "BBS"
        assert "BBS-2048" in new_name


class TestStripJavFilenameNoise:
    """strip_jav_filename_noise"""

    def test_case_insensitive(self) -> None:
        assert strip_jav_filename_noise("XXXbBs-2048YYY", ("BBS-2048",)) == "XXXYYY"


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
            "(Unc Leak) SDNT-108 寝取らせ願望のある旦那に従い出演させられた本物シロウト人妻"
            " case6 小学校教師・藤川なお（仮名）27歳 輪姦中出し了承 東京都武蔵野市在住"
            " 主人のためにネトラレます.mp4"
        )
        new_name, serial_id = generate_jav_filename(filename)

        assert serial_id is not None
        assert serial_id.prefix == "SDNT"
        assert serial_id.number == "108"
        # 字节精确等于上限（part3 截断后刚好用满 255 字节预算）
        assert len(new_name.encode()) == MAX_FILENAME_BYTES
        # part1 "(Unc Leak)" 完整保留
        assert new_name == (
            "SDNT-108 (Unc Leak)-serialId-寝取らせ願望のある旦那に従い出演させられた本物シロウト人妻"
            " case6 小学校教師・藤川なお（仮名）27歳 輪姦中出し了承 東京都武蔵野市在住 主人のためにネトラレ.mp4"
        )

    def test_serial_at_start_long_part3_truncated(self) -> None:
        """番号在开头，part3 过长时只截断 part3，字节精确用满上限。

        fixed = "ABC-100 .mp4" = 12 字节，剩余 243 字节给 part3。
        100 个"あ"= 300 字节 → 截断为 81 个"あ"= 243 字节，总计 255 字节。
        """
        long_part3 = "あ" * 100
        filename = f"ABC-100 {long_part3}.mp4"
        new_name, serial_id = generate_jav_filename(filename)

        assert serial_id is not None
        assert serial_id.prefix == "ABC"
        assert serial_id.number == "100"
        assert len(new_name.encode()) == MAX_FILENAME_BYTES
        assert new_name == f"ABC-100 {'あ' * 81}.mp4"

    def test_serial_not_at_start_no_part3_long_part1_truncated(self) -> None:
        """番号不在开头且无 part3，part1 过长时截断 part1，占位符和扩展名完整保留。

        fixed = "ABC-100 -serialId.mp4" = 21 字节，剩余 234 字节给 part1。
        90 个"あ"= 270 字节 → 截断为 78 个"あ"= 234 字节，总计 255 字节。
        """
        long_part1 = "あ" * 90
        filename = f"{long_part1}_ABC-100.mp4"
        new_name, serial_id = generate_jav_filename(filename)

        assert serial_id is not None
        assert serial_id.prefix == "ABC"
        assert serial_id.number == "100"
        assert len(new_name.encode()) == MAX_FILENAME_BYTES
        assert new_name == f"ABC-100 {'あ' * 78}-serialId.mp4"

    def test_serial_not_at_start_both_parts_long_part3_truncated_first(self) -> None:
        """番号不在开头，part1 较短可完整保留，只截断 part3。

        fixed = "ABC-100 -serialId-.mp4" = 22 字节，剩余 233 字节。
        part1 "prefix" = 6 字节，part3 预算 = 227 字节。
        90 个"い"= 270 字节 → 截断为 75 个"い"= 225 字节（227 字节内最多完整字符）。
        总计 22 + 6 + 225 = 253 字节（最后 2 字节因多字节边界无法利用）。
        """
        part1 = "prefix"
        long_part3 = "い" * 90
        filename = f"{part1}_ABC-100_{long_part3}.mp4"
        new_name, serial_id = generate_jav_filename(filename)

        assert serial_id is not None
        assert serial_id.prefix == "ABC"
        assert serial_id.number == "100"
        assert len(new_name.encode()) == 253  # 255 - 2（多字节边界损耗）
        assert new_name == f"ABC-100 prefix-serialId-{'い' * 75}.mp4"

    def test_serial_not_at_start_part1_exceeds_budget_drops_part3(self) -> None:
        """番号不在开头，part1 本身超出预算，丢弃 part3 并截断 part1。

        fixed（含 part3）= "ABC-100 -serialId-.mp4" = 22 字节，剩余 233 字节。
        part1 "う"×90 = 270 字节 > 233 → 触发 else 分支。
        改用 fixed2 = "ABC-100 -serialId.mp4" = 21 字节，剩余 234 字节给 part1。
        截断为 78 个"う"= 234 字节，总计 255 字节；part3 "suffix" 被完全丢弃。
        """
        long_part1 = "う" * 90
        part3 = "suffix"
        filename = f"{long_part1}_ABC-100_{part3}.mp4"
        new_name, serial_id = generate_jav_filename(filename)

        assert serial_id is not None
        assert serial_id.prefix == "ABC"
        assert serial_id.number == "100"
        assert len(new_name.encode()) == MAX_FILENAME_BYTES
        assert new_name == f"ABC-100 {'う' * 78}-serialId.mp4"
        # "suffix" 已被丢弃，不应出现在文件名中
        assert "suffix" not in new_name

    def test_within_limit_no_truncation(self) -> None:
        """文件名未超限时，输出与不加截断逻辑时完全一致"""
        new_name, serial_id = generate_jav_filename("(prefix) ABC-100 suffix.mp4")
        assert serial_id is not None
        assert serial_id.prefix == "ABC"
        assert serial_id.number == "100"
        assert new_name == "ABC-100 (prefix)-serialId-suffix.mp4"
        assert len(new_name.encode()) <= MAX_FILENAME_BYTES

    def test_within_limit_serial_at_start(self) -> None:
        """番号在开头且未超限时，原样保留 part3，不做截断"""
        new_name, serial_id = generate_jav_filename("SDNT-108 some description.mp4")
        assert serial_id is not None
        assert serial_id.prefix == "SDNT"
        assert serial_id.number == "108"
        assert new_name == "SDNT-108 some description.mp4"
        assert len(new_name.encode()) <= MAX_FILENAME_BYTES


class TestMatchSerialIdFixedGrammar:
    """固定番号 grammar：前缀 2–6 字母、数字 3–5 字符、有效位 1–4"""

    def test_typical_three_letter_three_digit(self) -> None:
        sid, _, _ = _match_serial_id("ABC-123")
        assert sid is not None
        assert sid.prefix == "ABC"
        assert sid.number == "123"

    def test_two_letter_prefix(self) -> None:
        sid, _, _ = _match_serial_id("AB-123")
        assert sid is not None
        assert sid.prefix == "AB"

    def test_six_letter_prefix(self) -> None:
        sid, _, _ = _match_serial_id("ABCDEF-123")
        assert sid is not None
        assert sid.prefix == "ABCDEF"

    def test_rejects_two_digit_run(self) -> None:
        assert _match_serial_id("ABC-12")[0] is None

    def test_rejects_six_digit_run(self) -> None:
        assert _match_serial_id("ABC-123456")[0] is None

    def test_rejects_five_effective_digits(self) -> None:
        assert _match_serial_id("AB-12345")[0] is None

    def test_accepts_01234_five_chars_four_effective(self) -> None:
        sid, _, _ = _match_serial_id("AB-01234.mp4")
        assert sid is not None
        assert sid.number == "1234"

    def test_case_insensitive(self) -> None:
        assert _match_serial_id("abc-123")[0] is not None
        assert _match_serial_id("Abc-123")[0] is not None

    def test_no_separator(self) -> None:
        assert _match_serial_id("ABC123")[0] is not None

    def test_underscore_separator(self) -> None:
        assert _match_serial_id("ABC_123")[0] is not None

    def test_single_letter_prefix_rejected(self) -> None:
        assert _match_serial_id("A-123")[0] is None

    def test_four_digit_effective_after_abc(self) -> None:
        sid, _, _ = _match_serial_id("ABC-1234")
        assert sid is not None
        assert sid.number == "1234"

    def test_leading_zeros_five_char_run(self) -> None:
        sid, _, _ = _match_serial_id("BAZX-00399.mp4")
        assert sid is not None
        assert sid.prefix == "BAZX"
        assert sid.number == "399"

    def test_generate_jav_filename_uses_default_pattern(self) -> None:
        new_name, sid = generate_jav_filename("ABCD-123_video.mp4")
        assert sid is not None
        assert sid.prefix == "ABCD"
        assert new_name == "ABCD-123 video.mp4"

        new_name2, sid2 = generate_jav_filename("ABC-123_video.mp4")
        assert sid2 is not None
        assert sid2.prefix == "ABC"
        assert new_name2 == "ABC-123 video.mp4"


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
