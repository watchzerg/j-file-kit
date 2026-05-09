"""整理管线共享的产品级默认值（非 YAML / 非用户配置）。

扩展名集合与（JAV 用）站标去噪子串变更频率低，由代码单点维护；`JavVideoOrganizer` 组装 `JavAnalyzeConfig`
时注入这些常量；`RawFileOrganizer` 组装 `RawAnalyzeConfig` 时复用扩展名相关常量。
`misc_file_delete_rules` 中的扩展名命中优先级最高（见 `analyzer._check_misc_delete_rules`），
其列表同样由此模块提供；YAML 仅保留 misc 删除的 max_size。

`DEFAULT_MUSIC_EXTENSIONS`：音乐类扩展名，在 Raw 分析配置中作 `audio_extensions` 注入；JAV **`JavAnalyzeConfig`** 尚未接入。

Raw **junk** 相关产品常量：

- **`DEFAULT_RAW_JUNK_KEYWORDS`**：2.1 目录 basename、2.2 / 3.0 stem 的子串关键字。
- **`DEFAULT_RAW_PHASE22_JUNK_DELETE_MAX_BYTES`**：2.2 中仅当 stem 命中 junk 关键字时，单文件须 **`st_size` 严格小于** 该值（默认 100MiB）才删除；扩展名 / 0 字节规则不受此上限约束。

Raw **阶段 3.4**（`files_misc` 第一层视频）：stem 子串关键字，规范化口径与 junk 相同（见 `raw_pipeline/keywords`）。匹配顺序：`movie` → `video_US_VR` → `video_US` → `video_jav_vr` → `video_jav`；均未命中则 **`files_video_misc`**。

六类扩展名集合（video / image / subtitle / archive / music / misc_delete）在分类与删除规则中按互斥假设使用；**启动时**须通过 `validate_organizer_extension_sets_disjoint()` 校验两两交集为空。
"""

DEFAULT_RAW_JUNK_KEYWORDS: tuple[str, ...] = (
    "扫码下载1024安卓APP",
    "1024手机网址",
    "FC2-PPV",
)

DEFAULT_RAW_PHASE22_JUNK_DELETE_MAX_BYTES: int = 100 * 1024 * 1024

DEFAULT_RAW_PHASE34_VIDEO_MOVIE_KEYWORDS: tuple[str, ...] = ("AMZN",)

DEFAULT_RAW_PHASE34_VIDEO_US_VR_KEYWORDS: tuple[str, ...] = ("VirtualTaboo",)

DEFAULT_RAW_PHASE34_VIDEO_US_KEYWORDS: tuple[str, ...] = ("HardCoreGangbang",)

DEFAULT_RAW_PHASE34_VIDEO_JAV_VR_KEYWORDS: tuple[str, ...] = ("JAV-VR",)

DEFAULT_RAW_PHASE34_VIDEO_JAV_KEYWORDS: tuple[str, ...] = ()

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
