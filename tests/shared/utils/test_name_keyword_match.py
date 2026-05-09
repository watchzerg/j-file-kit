"""``shared.utils.name_keyword_match`` 单元测试。"""

import pytest

from j_file_kit.shared.utils.name_keyword_match import (
    name_contains_keyword,
    name_matches_any_keyword,
    normalize_keyword_tokens,
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
