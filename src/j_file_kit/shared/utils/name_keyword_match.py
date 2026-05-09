"""名称与关键字的 token 边界匹配。

先对目录 basename、文件名 stem、配置关键字做 **NFKC + casefold**，再在规范化串上判定：
关键字某一出现之 **左邻**（串首除外）与 **右邻**（串尾除外）须为「分隔符」。

分隔符：① **显式字符集**（含 ``.``、常见文件名分段符）；② **Unicode 类别兜底**
``unicodedata.category(ch)[0]`` 为 ``Z``（空白类）或 ``P``（标点类）。
不对 grapheme cluster 做拆分（按 Unicode 标量字符迭代边界）。

**不设 ``S*``（符号）整类为边界**：避免误切 token；若个别符号需当边界，加入显式集。

CJK 等 ``Lo`` 与相邻汉字粘连且无标点/空白时，**不构成边界**，可能不再命中（相对纯子串匹配的语义变化）。
"""

import unicodedata
from pathlib import Path

from j_file_kit.shared.utils.file_utils import sanitize_surrogate_str

# 显式分隔符：补充 NFKC 后仍为 ``S*``/``M*`` 等、但产品上希望切断 token 的少量字符可在此列出。
_EXPLICIT_TOKEN_BOUNDARY_CHARS: frozenset[str] = frozenset(
    " \t\n\r\f\v._-=+[](){}/\\|,;:'\"~!?@#%&*`<>《》「」【】〔〕〈〉"
)

_UNICODE_BOUNDARY_CATEGORIES: frozenset[str] = frozenset(("Z", "P"))


def normalize_for_match(text: str) -> str:
    """NFKC + casefold：用于名称与关键字匹配的统一形态。"""
    return unicodedata.normalize("NFKC", text.casefold())


def normalize_keyword_tokens(tokens: tuple[str, ...]) -> tuple[str, ...]:
    """预归一化配置中的关键字，避免热路径重复 NFKC。"""
    return tuple(normalize_for_match(t) for t in tokens if t != "")


def _is_token_boundary_char(ch: str) -> bool:
    """单字符是否为 token 分隔符（规范化后的 haystack / needle 侧邻接判断）。"""
    if ch in _EXPLICIT_TOKEN_BOUNDARY_CHARS:
        return True
    return unicodedata.category(ch)[0] in _UNICODE_BOUNDARY_CATEGORIES


def _haystack_contains_bounded_needle(hay: str, needle: str) -> bool:
    """``hay`` 中是否存在 ``needle`` 的一次出现，且该出现左右满足 token 边界。"""
    if not needle:
        return False
    start_search = 0
    hay_len = len(hay)
    needle_len = len(needle)
    while True:
        pos = hay.find(needle, start_search)
        if pos < 0:
            return False
        left_ok = pos == 0 or _is_token_boundary_char(hay[pos - 1])
        end_pos = pos + needle_len
        right_ok = end_pos >= hay_len or _is_token_boundary_char(hay[end_pos])
        if left_ok and right_ok:
            return True
        start_search = pos + 1


def name_contains_keyword(name: str, keyword: str) -> bool:
    """规范化后判断 ``name`` 是否在 **token 边界** 下包含 ``keyword``。

    空 ``keyword`` 视为不匹配。
    """
    if not keyword:
        return False
    hay = normalize_for_match(name)
    needle = normalize_for_match(keyword)
    return _haystack_contains_bounded_needle(hay, needle)


def name_matches_any_keyword(name: str, keywords: tuple[str, ...]) -> bool:
    """规范化后判断是否任一非空 ``keywords`` 以 token 边界出现在 ``name`` 中。

    ``keywords`` 可为原始配置元组或 ``normalize_keyword_tokens`` 结果。
    """
    if not keywords:
        return False
    hay = normalize_for_match(name)
    for raw in keywords:
        if not raw:
            continue
        needle = normalize_for_match(raw)
        if _haystack_contains_bounded_needle(hay, needle):
            return True
    return False


def dir_name_matches(dir_path: Path, keywords_norm: tuple[str, ...]) -> bool:
    """目录 basename 是否命中任一关键字（代理码安全清洗 + 统一匹配口径）。"""
    name = sanitize_surrogate_str(dir_path.name)
    return name_matches_any_keyword(name, keywords_norm)
