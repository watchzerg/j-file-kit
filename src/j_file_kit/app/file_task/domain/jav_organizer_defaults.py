"""JAV 收件箱整理管线的产品级默认值（非 YAML / 非用户配置）。

扩展名集合与站标去噪子串变更频率低，由代码单点维护；`JavVideoOrganizer` 组装 `AnalyzeConfig`
时注入这些常量。`misc_file_delete_rules` 中的扩展名命中优先级最高（见 `analyzer._check_misc_delete_rules`），
其列表同样由此模块提供；YAML 仅保留 misc 删除的 keywords / max_size。

`DEFAULT_MUSIC_EXTENSIONS`：音乐类扩展名，**尚未接入** `AnalyzeConfig` / 分类管线，仅占位供后续使用。
"""

DEFAULT_VIDEO_EXTENSIONS: frozenset[str] = frozenset(
    {
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

DEFAULT_JAV_FILENAME_STRIP_SUBSTRINGS: tuple[str, ...] = (
    "BBS-2048",
    "BIG-2048",
    "CHD-1080",
    "DHD-1080",
    "FUN-2048",
    "HJD-2048",
    "PP-168",
    "RH-2048",
    "XHD-1080",
    "CCTV-12306",
)
