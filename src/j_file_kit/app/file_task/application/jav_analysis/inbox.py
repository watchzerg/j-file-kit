"""收件箱预删除规则（扩展名分类之前）。

OR 语义：stem 完全匹配、stem **在 token 边界上出现**默认垃圾关键词（与 Raw 共用 ``shared/utils/name_keyword_match``：NFKC + casefold + 分隔符 / Unicode ``Z*``、``P*``）、或体积不超过上限（若配置）。
评估顺序：完全匹配 → 关键字 → stat，以减少磁盘访问。

``InboxDeleteRules`` 与默认关键词来自任务配置与 ``organizer_defaults``；
生产路径由 ``JavVideoOrganizer`` 注入 ``JavAnalyzeConfig``。
"""

from pathlib import Path

from j_file_kit.app.file_task.application.config_common import InboxDeleteRules
from j_file_kit.app.file_task.domain.organizer_defaults import (
    DEFAULT_CAMELCASE_NO_SPLIT_WORDS,
)
from j_file_kit.app.file_task.domain.raw_defaults import (
    DEFAULT_RAW_JUNK_KEYWORDS,
)
from j_file_kit.shared.utils.name_keyword_match import (
    expand_keywords_camelcase,
    name_matches_any_keyword,
)

# junk 关键词的 CamelCase 变体展开，模块初始化时计算一次
_JUNK_KW_EX: tuple[str, ...] = expand_keywords_camelcase(
    DEFAULT_RAW_JUNK_KEYWORDS, DEFAULT_CAMELCASE_NO_SPLIT_WORDS
)


def check_inbox_delete_rules(path: Path, rules: InboxDeleteRules) -> str | None:
    """收件箱预删除判定（扩展名分类之前）。

    Args:
        path: 文件路径
        rules: 收件箱删除规则

    Returns:
        删除原因；不应删除则返回 None。体积规则在 ``stat`` 失败时返回 None（不删）。
    """
    stem = path.stem
    if stem in rules.exact_stems:
        return f"stem 完全匹配收件箱删除规则: {stem!r}"
    if name_matches_any_keyword(stem, _JUNK_KW_EX):
        return "stem 包含收件箱删除关键字"
    if rules.max_size_bytes is not None:
        try:
            file_size = path.stat().st_size
        except OSError:
            return None
        if file_size <= rules.max_size_bytes:
            return f"文件大小 {file_size} <= {rules.max_size_bytes}（收件箱删除规则）"
    return None
