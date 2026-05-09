"""整理管线共享的产品级默认值（非 YAML / 非用户配置）。

扩展名集合与（JAV 用）站标去噪子串变更频率低，由代码单点维护；`JavVideoOrganizer` 组装 `JavAnalyzeConfig`
时注入这些常量；`RawFileOrganizer` 组装 `RawAnalyzeConfig` 时复用扩展名相关常量。
`misc_file_delete_rules` 中的扩展名命中优先级最高（见 `analyzer._check_misc_delete_rules`），
其列表同样由此模块提供；YAML 仅保留 misc 删除的 max_size。

`DEFAULT_MUSIC_EXTENSIONS`：音乐类扩展名，在 Raw 分析配置中作 `audio_extensions` 注入；JAV **`JavAnalyzeConfig`** 尚未接入。

Raw **junk** 相关产品常量：

- **`DEFAULT_RAW_JUNK_KEYWORDS`**：2.1 目录 basename、2.2 / 3.0 stem；命中语义为 **token 边界匹配**（见 ``shared/utils/name_keyword_match``：NFKC + casefold + 分隔符 / Unicode ``Z*``、``P*``），非纯子串包含。
- **`DEFAULT_RAW_CLEANUP_JUNK_MAX_BYTES`**：递归清洗阶段（2.2）中仅当 stem 命中 junk 关键字时，单文件须 **`st_size` 严格小于** 该值（默认 100MiB）才删除；扩展名 / 0 字节规则不受此上限约束。

Raw **视频归桶**（`files_misc` 第一层视频 stem 匹配，即阶段 3.4）：关键字匹配顺序：`movie` → `video_US_VR` → `video_US`；均未命中则通过 ``generate_jav_filename`` 识别番号，番号前缀属于 ``DEFAULT_JAV_VR_SERIAL_PREFIXES`` 归入 `video_jav_vr`，其余已识别番号归入 `video_jav`，无番号归入 **`files_video_misc`**。

六类扩展名集合（video / image / subtitle / archive / music / misc_delete）在分类与删除规则中按互斥假设使用；**启动时**须通过 `validate_organizer_extension_sets_disjoint()` 校验两两交集为空。
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

DEFAULT_RAW_JUNK_KEYWORDS: tuple[str, ...] = (
    "FC2-PPV",
    "RARBG_DO_NOT_MIRROR",
    "發布器",
    "发布器",
    "社区回家指南",
    "論壇文宣",
    "美女直播",
    "手机网址",
    "新地址",
    "扫码",
    "二维码",
    "影视联盟",
    "安卓APP",
    "文宣",
    "手机版网址",
)

DEFAULT_RAW_CLEANUP_JUNK_MAX_BYTES: int = 100 * 1024 * 1024

DEFAULT_RAW_VIDEO_BUCKET_MOVIE_KEYWORDS: tuple[str, ...] = ("AMZN",)

DEFAULT_RAW_VIDEO_BUCKET_US_VR_KEYWORDS: tuple[str, ...] = (
    "LethalHardcoreVR",
    "AsianSexVR",
    "VirtualTaboo",
    "VRLatina",
    "FuckPassVR",
    "TabooVR",
    "BadoinkVR",
    "CzechVR",
    "CzechVRFetish",
    "VRSpy",
    "VRCosplayX",
    "VirtualRealPorn",
    "RealJamVR",
    "BadoinkVR",
    "VRedging",
    # 低优先级，排在后面
    "SLR",
    "VR",
)

DEFAULT_RAW_VIDEO_BUCKET_US_KEYWORDS: tuple[str, ...] = (
    "AcademyPOV",
    "AccidentalGangbang",
    "AllAnalAllTheTime",
    "AltErotic",
    "AnalVids",
    "Assylum",
    "BackroomCastingCouch",
    "BangSurprise",
    "BoundGangBangs",
    "BrookelynneBriar",
    "CathysCraving",
    "CherryPimps",
    "Clips4Sale",
    "ClubSeventeen",
    "ClubSweethearts",
    "DefeatedSexFight",
    "DeviceBondage",
    "DevilsFilm",
    "DigitalPlayground",
    "DivineBitches",
    "DorcelClub",
    "DungeonSex",
    "EvilAngel",
    "ExploitedCollegeGirls",
    "FemdomEmpire",
    "FilthyTaboo",
    "FittingRoom",
    "FootsieBabes",
    "FrolicMe",
    "FTVGirls",
    "GangbangCreampie",
    "GirlsOutWest",
    "GroupBanged",
    "HardcoreGangBang",
    "HardTied",
    "Hentaied",
    "HollandschePassie",
    "HouseOfTaboo",
    "HumiliationPOV",
    "iWantClips",
    "JacquieEtMichelTV",
    "JulesJordan",
    "JuliaAnnLive",
    "KarupsOW",
    "KendraJames",
    "LadySonia",
    "LegalPorno",
    "Lustery",
    "ManyVids",
    "MatureNL",
    "MaxineX",
    "MetArtX",
    "Milfy",
    "MistressT",
    "MomComesFirst",
    "PascalsSubSluts",
    "PerverseFamily",
    "PinkoTGirls",
    "PissVids",
    "PornBox",
    "PornMegaLoad",
    "PowerFetish",
    "PrimalFetish",
    "Private",
    "PureTaboo",
    "RedXXX",
    "SexAndSubmission",
    "SexMex",
    "SexuallyBroken",
    "Shoplyfter",
    "Spizoo",
    "StrapLez",
    "SubmissiveCuckolds",
    "SweetSinner",
    "TabooHeat",
    "TadpolexStudio",
    "TeamSkeetSelects",
    "Teenslikeitbig",
    "TeensLoveBlackCocks",
    "TeenyTaboo",
    "TransAngels",
    "Wanilianna",
    "WankItNow",
    "WetAndPuffy",
    "WhenGirlsPlay",
    "WildOnCam",
    "WoodmanCastingX",
    "XevBellringer",
    "Z-Filmz",
    # 低优先级1
    "Beauty4K",
    "GirlCum",
    # 低优先级2
    "Kink",
    "Brazzers",
    "Babes",
    "Blacked",
    "Throated",
    "Taboo",
)

DEFAULT_JAV_VR_SERIAL_PREFIXES: frozenset[str] = frozenset(
    {
        "3DSVR",
        "AJVR",
        "AQUCO",
        "ASVR",
        "ATVR",
        "AVERV",
        "AVOPVR",
        "AVVR",
        "BIBIVR",
        "BIKMVR",
        "CAFR",
        "CAMI",
        "CAPI",
        "CASMANI",
        "CBIKMV",
        "CCVR",
        "CJVR",
        "CLVR",
        "COSVR",
        "CRVR",
        "DANDYVR",
        "DLVSS",
        "DOCVR",
        "DORI",
        "DOVR",
        "DPVR",
        "DSVR",
        "DTVR",
        "EBVR",
        "ETVTM",
        "EXBVR",
        "EXHQVR",
        "EXVR",
        "FCVR",
        "FSVR",
        "GOPJ",
        "HNVR",
        "HUNVR",
        "HVR",
        "IPVR",
        "JAVR",
        "JUVR",
        "KAVR",
        "KBVR",
        "KIVR",
        "KIWVR",
        "KMVR",
        "KOLVR",
        "MANIVR",
        "MAXVR",
        "MAXVRH",
        "MDVR",
        "MIVR",
        "MMCPVR",
        "MTVR",
        "MUM",
        "MXVR",
        "NHVR",
        "NJVR",
        "NKKVR",
        "OCVR",
        "OPG",
        "OYCVR",
        "PMAXVR",
        "PPVR",
        "PRDVR",
        "PRVR",
        "PXVR",
        "PYDVR",
        "PYMVR",
        "RCTVR",
        "RSRVR",
        "SAVR",
        "SCVR",
        "SIVR",
        "SPIVR",
        "SQTEVR",
        "TKRM",
        "TMAVR",
        "TPVR",
        "URVRSP",
        "VOVS",
        "VRGL",
        "VRKM",
        "VRTB",
        "VRVR",
        "VVVR",
        "WAVR",
        "WOW",
        "WPVR",
    }
)
"""番号前缀属于此集合的 JAV 视频归入 files_video_jav_vr；其余已识别番号归入 files_video_jav。"""

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
