"""``shared.utils.name_keyword_match`` 单元测试。"""

import pytest

from j_file_kit.shared.utils.name_keyword_match import (
    expand_keyword_to_variants,
    expand_keywords_camelcase,
    name_contains_keyword,
    name_matches_any_keyword,
    normalize_keyword_tokens,
    split_camelcase_tokens,
)

pytestmark = pytest.mark.unit


def test_name_contains_keyword_empty_keyword_never_matches() -> None:
    assert name_contains_keyword("anything", "") is False


def test_name_matches_any_keyword_empty_keywords_never_matches() -> None:
    assert name_matches_any_keyword("anything", ()) is False


def test_name_matches_any_keyword_uses_normalize_keyword_tokens() -> None:
    tokens = normalize_keyword_tokens(("AMZN",))
    assert name_matches_any_keyword("prefix_amzn_suffix", tokens) is True


def test_name_contains_keyword_nfk_casefold_equivalence() -> None:
    assert name_contains_keyword("ａｍｚｎ_clip", "AMZN") is True


def test_name_matches_any_keyword_skips_empty_tokens_in_tuple() -> None:
    assert name_matches_any_keyword("_ello", ("", "ello")) is True


def test_bounded_dot_and_hyphen_boundaries() -> None:
    assert name_contains_keyword("foo.ABC-123.bar", "ABC-123") is True


def test_bounded_rejects_letter_glued_left() -> None:
    assert name_contains_keyword("prefixabc-123", "ABC-123") is False


def test_bounded_rejects_prefix_of_longer_digit_run() -> None:
    assert name_contains_keyword("ABC-1234", "ABC-123") is False


def test_bounded_chinese_junk_requires_separator_when_glued_cjk() -> None:
    kw = "扫码下载1024安卓APP"
    assert name_contains_keyword(f"前缀{kw}后缀", kw) is False
    assert name_contains_keyword(f"前缀_{kw}_后缀", kw) is True


def test_bounded_unicode_punctuation_boundary_class_p() -> None:
    assert name_contains_keyword("trail（FC2-PPV）", "FC2-PPV") is True


# --- split_camelcase_tokens ---


def test_split_camelcase_standard() -> None:
    assert split_camelcase_tokens("LethalHardcoreVR", frozenset({"VR"})) == [
        "Lethal",
        "Hardcore",
        "VR",
    ]


def test_split_camelcase_no_split_protects_prefix_acronym() -> None:
    # VR 在词首，后接小写字母：标准算法会拆成 V+Redging，黑名单保护后应为 VR+edging
    assert split_camelcase_tokens("VRedging", frozenset({"VR"})) == ["VR", "edging"]


def test_split_camelcase_no_split_mid_word() -> None:
    assert split_camelcase_tokens("CzechVRFetish", frozenset({"VR"})) == [
        "Czech",
        "VR",
        "Fetish",
    ]


def test_split_camelcase_all_uppercase_not_split() -> None:
    # SLR 全大写，无 CamelCase 边界，不拆分
    assert split_camelcase_tokens("SLR", frozenset({"VR"})) == ["SLR"]


def test_split_camelcase_all_uppercase_amzn() -> None:
    assert split_camelcase_tokens("AMZN", frozenset({"VR"})) == ["AMZN"]


def test_split_camelcase_empty_no_split() -> None:
    # VR 末尾全大写且无后续小写字母，CamelCase 正则不会拆开 V 与 R
    # 因此 no_split 为空时结果与含 VR 时相同
    assert split_camelcase_tokens("LethalHardcoreVR", frozenset()) == [
        "Lethal",
        "Hardcore",
        "VR",
    ]


# --- expand_keyword_to_variants ---


def test_expand_keyword_camelcase_multi_tokens() -> None:
    variants = expand_keyword_to_variants("LethalHardcoreVR", frozenset({"VR"}))
    assert "lethalhardcorevr" in variants
    assert "lethal.hardcore.vr" in variants
    assert "lethal_hardcore_vr" in variants
    assert "lethal-hardcore-vr" in variants
    assert "lethal hardcore vr" in variants


def test_expand_keyword_has_separator_no_expansion() -> None:
    # 已含分隔符，不做 CamelCase 展开
    assert expand_keyword_to_variants("JAV-VR", frozenset({"VR"})) == ("jav-vr",)
    assert expand_keyword_to_variants("FC2-PPV", frozenset({"VR"})) == ("fc2-ppv",)


def test_expand_keyword_single_token_no_expansion() -> None:
    # 全大写，1 个词根，不产生额外变体
    result = expand_keyword_to_variants("SLR", frozenset({"VR"}))
    assert result == ("slr",)


def test_expand_keyword_vredging_with_no_split() -> None:
    variants = expand_keyword_to_variants("VRedging", frozenset({"VR"}))
    assert "vredging" in variants  # 归一化原始
    assert "vr.edging" in variants
    assert "vr_edging" in variants


def test_expand_keyword_dedup_variants() -> None:
    # 若原始归一化与某变体相同，应去重
    result = expand_keyword_to_variants("Abc", frozenset())
    assert len(result) == len(set(result))


# --- expand_keywords_camelcase ---


def test_expand_keywords_camelcase_flattened() -> None:
    result = expand_keywords_camelcase(
        ("LethalHardcoreVR", "SLR"),
        frozenset({"VR"}),
    )
    assert "lethal.hardcore.vr" in result
    assert "lethal_hardcore_vr" in result
    assert "slr" in result


def test_expand_keywords_camelcase_skips_empty() -> None:
    result = expand_keywords_camelcase(("", "SLR"), frozenset({"VR"}))
    assert "" not in result
    assert "slr" in result


def test_expand_keywords_camelcase_matches_dot_variant() -> None:
    # 展开后的元组应能命中以 . 分隔的变体文件名
    kw_ex = expand_keywords_camelcase(("LethalHardcoreVR",), frozenset({"VR"}))
    assert name_matches_any_keyword("Lethal.Hardcore.VR_clip", kw_ex) is True
    assert name_matches_any_keyword("Lethal_Hardcore_VR_clip", kw_ex) is True
    assert name_matches_any_keyword("Lethal-Hardcore-VR.clip", kw_ex) is True
    assert name_matches_any_keyword("LethalHardcoreVR.clip", kw_ex) is True


def test_expand_keywords_camelcase_no_false_positive_glued() -> None:
    # 无边界的紧贴不命中
    kw_ex = expand_keywords_camelcase(("LethalHardcoreVR",), frozenset({"VR"}))
    assert name_matches_any_keyword("XLethalHardcoreVRY", kw_ex) is False
