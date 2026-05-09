"""名称与关键字的 token 边界匹配。

先对目录 basename、文件名 stem、配置关键字做 **NFKC + casefold**，再在规范化串上判定：
关键字某一出现之 **左邻**（串首除外）与 **右邻**（串尾除外）须为「分隔符」。

分隔符：① **显式字符集**（含 ``.``、常见文件名分段符）；② **Unicode 类别兜底**
``unicodedata.category(ch)[0]`` 为 ``Z``（空白类）或 ``P``（标点类）。
不对 grapheme cluster 做拆分（按 Unicode 标量字符迭代边界）。

**不设 ``S*``（符号）整类为边界**：避免误切 token；若个别符号需当边界，加入显式集。

CJK 等 ``Lo`` 与相邻汉字粘连且无标点/空白时，**不构成边界**，可能不再命中（相对纯子串匹配的语义变化）。

CamelCase 展开（``expand_keywords_camelcase``）：将 ``LethalHardcoreVR`` 等无分隔符 CamelCase 关键词
拆成词根，再用 ``.``、``_``、``-``、`` `` 组合为变体，使文件名 ``Lethal.Hardcore.VR`` 同样命中。
已含分隔符的关键词（如 ``JAV-VR``）不做 CamelCase 展开，直接归一化使用。
"""

import re
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


# CamelCase 拆词相关常量
# 两条规则：小写→大写边界；连续大写后遇到"大写+小写"时，在前一个大写前断开
_CAMEL_SPLIT_RE: re.Pattern[str] = re.compile(
    r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])"
)
# 关键词内已有分隔符时不做 CamelCase 展开，避免产生无意义变体（如 JAV-.VR）
_HAS_SEPARATOR_RE: re.Pattern[str] = re.compile(r"[._\- ]")

_DEFAULT_VARIANT_SEPARATORS: tuple[str, ...] = (".", "_", "-", " ")


def split_camelcase_tokens(keyword: str, no_split: frozenset[str]) -> list[str]:
    """将 CamelCase 关键词拆分为词根列表，``no_split`` 中的词根保持完整不细拆。

    算法：先用 ``no_split`` 词根作捕获分隔符将原串分段，受保护段直接保留，
    非受保护段再按 CamelCase 边界拆分，最后按原顺序合并。

    Examples::

        split_camelcase_tokens("LethalHardcoreVR", {"VR"})
        # → ["Lethal", "Hardcore", "VR"]

        split_camelcase_tokens("VRedging", {"VR"})
        # → ["VR", "edging"]

        split_camelcase_tokens("SLR", {"VR"})
        # → ["SLR"]
    """
    if not no_split:
        return [t for t in _CAMEL_SPLIT_RE.split(keyword) if t]

    # 按词根长度降序排列，确保较长词根优先匹配
    sorted_ns: list[str] = sorted(no_split, key=lambda w: len(w), reverse=True)
    ns_pattern = "|".join(re.escape(w) for w in sorted_ns)
    # re.split 带捕获组时，结果交替为：未保护段、保护段、未保护段…
    parts = re.split(f"({ns_pattern})", keyword)

    tokens: list[str] = []
    for i, part in enumerate(parts):
        if not part:
            continue
        if i % 2 == 1:
            # 奇数位为捕获到的 no_split 词根，直接保留
            tokens.append(part)
        else:
            tokens.extend(t for t in _CAMEL_SPLIT_RE.split(part) if t)
    return tokens


def expand_keyword_to_variants(
    keyword: str,
    no_split: frozenset[str],
    separators: tuple[str, ...] = _DEFAULT_VARIANT_SEPARATORS,
) -> tuple[str, ...]:
    """将单个关键词展开为 CamelCase 变体的归一化元组。

    - 若 ``keyword`` 已含分隔符（``.`` ``_`` ``-`` `` ``），直接返回归一化原始形式，不展开。
    - 否则拆词；若仅 1 个词根，同样只返回归一化原始形式。
    - 多词根时：归一化原始形式 + 各分隔符连接后的归一化变体（去重保序）。

    返回值均已预归一化，可直接传入 ``name_matches_any_keyword``。

    Examples::

        expand_keyword_to_variants("LethalHardcoreVR", {"VR"})
        # → ("lethalhardcorevr", "lethal.hardcore.vr",
        #    "lethal_hardcore_vr", "lethal-hardcore-vr", "lethal hardcore vr")

        expand_keyword_to_variants("JAV-VR", {"VR"})
        # → ("jav-vr",)   # 已含分隔符，不展开
    """
    if _HAS_SEPARATOR_RE.search(keyword):
        return (normalize_for_match(keyword),)

    tokens = split_camelcase_tokens(keyword, no_split)
    if len(tokens) <= 1:
        return (normalize_for_match(keyword),)

    seen: list[str] = []

    def _add(v: str) -> None:
        n = normalize_for_match(v)
        if n not in seen:
            seen.append(n)

    _add(keyword)
    for sep in separators:
        _add(sep.join(tokens))
    return tuple(seen)


def expand_keywords_camelcase(
    keywords: tuple[str, ...],
    no_split: frozenset[str],
    separators: tuple[str, ...] = _DEFAULT_VARIANT_SEPARATORS,
) -> tuple[str, ...]:
    """将关键词元组中每个词展开为 CamelCase 变体，返回扁平化的归一化元组。

    结果可直接传入 ``name_matches_any_keyword``（已预归一化）。
    建议在模块初始化时调用一次并缓存，避免热路径重复计算。

    Examples::

        expand_keywords_camelcase(
            ("LethalHardcoreVR", "SLR", "JAV-VR"),
            frozenset({"VR"}),
        )
        # 包含 "lethal.hardcore.vr"、"slr"、"jav-vr" 等
    """
    result: list[str] = []
    for kw in keywords:
        if kw:
            result.extend(expand_keyword_to_variants(kw, no_split, separators))
    return tuple(result)
