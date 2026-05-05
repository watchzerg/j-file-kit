"""Raw 阶段 2 目录名关键字匹配工具。

NFKC + casefold 统一形态，使配置关键字与目录名在大小写/ Unicode 等价性上一致。
"""

import unicodedata
from pathlib import Path

from j_file_kit.shared.utils.file_utils import sanitize_surrogate_str


def normalize_for_match(text: str) -> str:
    """NFKC + casefold：用于目录名与子串关键字匹配的统一形态。"""
    return unicodedata.normalize("NFKC", text.casefold())


def normalize_keyword_tokens(tokens: tuple[str, ...]) -> tuple[str, ...]:
    """预归一化配置中的关键字，避免热路径重复 NFKC。"""
    return tuple(normalize_for_match(t) for t in tokens if t != "")


def dir_name_matches(dir_path: Path, keywords_norm: tuple[str, ...]) -> bool:
    """第一层目录名是否包含任一已归一化关键字子串。"""
    name = sanitize_surrogate_str(dir_path.name)
    hay = normalize_for_match(name)
    return any(k in hay for k in keywords_norm if k)
