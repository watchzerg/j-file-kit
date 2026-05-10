"""视频桶分类器：按关键词与 JAV 番号将视频 stem 映射到目标桶。

提供两个公开接口：
- ``classify_video_bucket_and_subdir`` — 返回 (桶名, 子目录名) 二元组
- ``classify_video_bucket`` — 仅返回桶名

桶名：``movie`` | ``us_vr`` | ``us`` | ``jav_vr`` | ``jav`` | ``misc``。
关键词匹配使用 CamelCase 变体展开，各桶内保序首中即止；
jav_vr / jav 通过 JAV 番号识别决定。

另导出 ``_JUNK_KW_EX``，供阶段 3.0 预清理使用。
"""

from j_file_kit.app.file_task.application.jav_filename_util import generate_jav_filename
from j_file_kit.app.file_task.domain.jav_defaults import (
    DEFAULT_JAV_FILENAME_STRIP_SUBSTRINGS,
    DEFAULT_JAV_VR_SERIAL_PREFIXES,
)
from j_file_kit.app.file_task.domain.organizer_defaults import (
    DEFAULT_CAMELCASE_NO_SPLIT_WORDS,
)
from j_file_kit.app.file_task.domain.raw_defaults import (
    DEFAULT_RAW_JUNK_KEYWORDS,
    DEFAULT_RAW_VIDEO_BUCKET_MOVIE_KEYWORDS,
    DEFAULT_RAW_VIDEO_BUCKET_US_KEYWORDS,
    DEFAULT_RAW_VIDEO_BUCKET_US_VR_KEYWORDS,
)
from j_file_kit.shared.utils.name_keyword_match import (
    expand_keyword_to_variants,
    expand_keywords_camelcase,
    name_matches_any_keyword,
)

# 各视频桶关键词及 junk 关键词的 CamelCase 变体展开，模块初始化时计算一次
_JUNK_KW_EX: tuple[str, ...] = expand_keywords_camelcase(
    DEFAULT_RAW_JUNK_KEYWORDS, DEFAULT_CAMELCASE_NO_SPLIT_WORDS
)
# movie 桶：保留 (原始关键词, 归一化变体元组) 的有序结构，用于保序首中即止匹配并返回原始关键词
_MOVIE_KW_ORDERED: tuple[tuple[str, tuple[str, ...]], ...] = tuple(
    (kw, expand_keyword_to_variants(kw, DEFAULT_CAMELCASE_NO_SPLIT_WORDS))
    for kw in DEFAULT_RAW_VIDEO_BUCKET_MOVIE_KEYWORDS
    if kw
)
# US_VR 桶：保留 (原始关键词, 归一化变体元组) 的有序结构，用于保序首中即止匹配并返回原始关键词
_US_VR_KW_ORDERED: tuple[tuple[str, tuple[str, ...]], ...] = tuple(
    (kw, expand_keyword_to_variants(kw, DEFAULT_CAMELCASE_NO_SPLIT_WORDS))
    for kw in DEFAULT_RAW_VIDEO_BUCKET_US_VR_KEYWORDS
    if kw
)
# US 桶：保留 (原始关键词, 归一化变体元组) 的有序结构，用于保序首中即止匹配并返回原始关键词
_US_KW_ORDERED: tuple[tuple[str, tuple[str, ...]], ...] = tuple(
    (kw, expand_keyword_to_variants(kw, DEFAULT_CAMELCASE_NO_SPLIT_WORDS))
    for kw in DEFAULT_RAW_VIDEO_BUCKET_US_KEYWORDS
    if kw
)


def _find_first_movie_keyword_match(stem: str) -> str | None:
    """按配置顺序匹配 movie 桶关键词，返回第一个命中的原始关键词；均未命中返回 None。

    匹配保序（首中即止），命中时返回原始配置关键词（如 ``AMZN``），
    而非归一化变体，用作 ``files_video_movie/`` 的子目录名。
    """
    for original_kw, variants in _MOVIE_KW_ORDERED:
        if name_matches_any_keyword(stem, variants):
            return original_kw
    return None


def _find_first_us_vr_keyword_match(stem: str) -> str | None:
    """按配置顺序匹配 US_VR 桶关键词，返回第一个命中的原始关键词；均未命中返回 None。

    匹配保序（首中即止），命中时返回原始配置关键词（如 ``VirtualTaboo``），
    而非归一化变体，用作 ``files_video_us_vr/`` 的子目录名。
    """
    for original_kw, variants in _US_VR_KW_ORDERED:
        if name_matches_any_keyword(stem, variants):
            return original_kw
    return None


def _find_first_us_keyword_match(stem: str) -> str | None:
    """按配置顺序匹配 US 桶关键词，返回第一个命中的原始关键词；均未命中返回 None。

    匹配保序（首中即止），命中时返回原始配置关键词（如 ``HardcoreGangBang``），
    而非归一化变体，用作 ``files_video_us/`` 的子目录名。
    """
    for original_kw, variants in _US_KW_ORDERED:
        if name_matches_any_keyword(stem, variants):
            return original_kw
    return None


def classify_video_bucket_and_subdir(stem: str) -> tuple[str, str | None]:
    """按产品顺序返回 (桶名, 子目录名)。

    桶名：``movie`` | ``us_vr`` | ``us`` | ``jav_vr`` | ``jav`` | ``misc``。
    子目录名：桶名为 ``movie``、``us_vr`` 或 ``us`` 时非 None，值为命中的原始配置关键词
    （如 ``AMZN``、``VirtualTaboo``、``HardcoreGangBang``），分别用作
    ``files_video_movie/{keyword}/``、``files_video_us_vr/{keyword}/`` 和
    ``files_video_us/{keyword}/`` 子目录名。其余桶均返回 None。

    关键词匹配（movie / us_vr / us 桶）使用 CamelCase 变体展开，各桶内保序首中即止。
    jav_vr / jav 桶通过 JAV 番号识别决定：调用 ``generate_jav_filename`` 提取 ``SerialId``，
    番号前缀属于 ``DEFAULT_JAV_VR_SERIAL_PREFIXES`` 白名单则归入 ``jav_vr``，
    其余已识别番号归入 ``jav``，无法识别番号则归入 ``misc``。
    番号识别口径与 JAV 管线共享，JAV 匹配策略演进后此处天然受益。
    """
    movie_kw = _find_first_movie_keyword_match(stem)
    if movie_kw is not None:
        return "movie", movie_kw
    us_vr_kw = _find_first_us_vr_keyword_match(stem)
    if us_vr_kw is not None:
        return "us_vr", us_vr_kw
    us_kw = _find_first_us_keyword_match(stem)
    if us_kw is not None:
        return "us", us_kw
    _, serial_id = generate_jav_filename(
        stem, strip_substrings=DEFAULT_JAV_FILENAME_STRIP_SUBSTRINGS
    )
    if serial_id is not None:
        if serial_id.prefix in DEFAULT_JAV_VR_SERIAL_PREFIXES:
            return "jav_vr", None
        return "jav", None
    return "misc", None


def classify_video_bucket(stem: str) -> str:
    """按产品顺序返回视频归宿桶标识（首个关键字命中即停）。

    返回值：``movie`` | ``us_vr`` | ``us`` | ``jav_vr`` | ``jav`` | ``misc``。
    ``misc`` 表示未命中任一关键字桶（迁入 ``files_video_misc``）。
    关键词匹配使用 CamelCase 变体展开，``LethalHardcoreVR`` 可命中 ``Lethal.Hardcore.VR`` 等变体。
    """
    bucket, _ = classify_video_bucket_and_subdir(stem)
    return bucket
