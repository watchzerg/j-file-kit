"""整理管线共享的产品级默认值（非 YAML / 非用户配置）。

六类扩展名集合（video / image / subtitle / archive / music / misc_delete）在分类与删除规则中按互斥假设使用；
**启动时**须通过 `validate_organizer_extension_sets_disjoint()` 校验两两交集为空。

`DEFAULT_CAMELCASE_NO_SPLIT_WORDS` 供 JAV 与 Raw 管线共用，传入 ``expand_keywords_camelcase`` 保留不可拆词根。

JAV 专属常量见 `jav_defaults`；Raw 专属常量见 `raw_defaults`。
"""

DEFAULT_CAMELCASE_NO_SPLIT_WORDS: frozenset[str] = frozenset(
    {
        "VR",
        "TGirls",
    }
)
"""CamelCase 拆词时不可细拆的词根黑名单。

用于 ``expand_keywords_camelcase``：黑名单内的词根在拆词时保持完整，
例如 ``VRedging`` 拆为 ``["VR", "edging"]`` 而非 ``["V", "Redging"]``。
可按需手工扩充。
"""

DEFAULT_VIDEO_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".asf",
        ".mp4",
        ".avi",
        ".mkv",
        ".mov",
        ".wmv",
        ".flv",
        ".webm",
        ".rmvb",
        ".rm",
        ".mpg",
        ".mpeg",
        ".m4v",
        ".ts",
        ".m2ts",
        ".vob",
        ".divx",
        ".3gp",
    },
)

DEFAULT_IMAGE_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".bmp",
        ".gif",
        ".tiff",
    },
)

DEFAULT_SUBTITLE_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".srt",
        ".ass",
        ".ssa",
        ".sub",
        ".vtt",
        ".idx",
        ".sup",
    },
)

DEFAULT_ARCHIVE_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".zip",
        ".rar",
        ".7z",
        ".tar",
        ".gz",
        ".bz2",
        ".xz",
    },
)

DEFAULT_MUSIC_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".flac",
        ".ape",
        ".mp3",
        ".m4b",
        ".m4a",
        ".fxp",
        ".mka",
        ".cue",
        ".m3u",
        ".m3u8",
        ".wav",
        ".aac",
        ".ogg",
        ".opus",
        ".wma",
        ".aiff",
        ".aif",
        ".dsf",
        ".dff",
        ".wv",
        ".mpc",
        ".tta",
        ".pls",
    },
)

DEFAULT_MISC_FILE_DELETE_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".tmp",
        ".temp",
        ".bak",
        ".old",
        ".url",
        ".lnk",
        ".mhtml",
        ".html",
        ".htm",
        ".nfo",
        ".chm",
        ".txt",
        ".xml",
        ".exe",
        ".scr",
        ".md",
        ".sfv",
        ".pdf",
        ".doc",
        ".docs",
        ".bat",
        ".cmd",
        ".pif",
        ".js",
        ".vbs",
        ".log",
        ".website",
        ".desktop",
        ".webloc",
        ".ds_store",
        ".torrent",
        ".rtf",
        ".ini",
        ".cfg",
        ".db",
        ".nzb",
        ".!ut",
        ".part",
        ".crdownload",
        ".aria2",
        ".ydl",
        ".apk",
        ".!qb",
        ".nrg",
        ".iso",
        ".dmg",
        ".mdf",
        ".mds",
        ".mdx",
        ".mht",
        ".dat",
        ".xltd",
    },
)


def validate_organizer_extension_sets_disjoint() -> None:
    """断言六类默认扩展名集合两两不交；若有交集则拒绝启动（见模块 docstring）。"""
    groups: tuple[tuple[str, frozenset[str]], ...] = (
        ("video", DEFAULT_VIDEO_EXTENSIONS),
        ("image", DEFAULT_IMAGE_EXTENSIONS),
        ("subtitle", DEFAULT_SUBTITLE_EXTENSIONS),
        ("archive", DEFAULT_ARCHIVE_EXTENSIONS),
        ("music", DEFAULT_MUSIC_EXTENSIONS),
        ("misc_delete", DEFAULT_MISC_FILE_DELETE_EXTENSIONS),
    )
    for i, (name_a, set_a) in enumerate(groups):
        for name_b, set_b in groups[i + 1 :]:
            overlap = set_a & set_b
            if overlap:
                sorted_overlap = ", ".join(sorted(overlap))
                msg = (
                    "organizer_defaults：扩展名集合须两两互斥，"
                    f"但 {name_a!r} 与 {name_b!r} 交集非空：{sorted_overlap}"
                )
                raise RuntimeError(msg)
