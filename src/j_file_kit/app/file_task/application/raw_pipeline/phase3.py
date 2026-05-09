"""Raw 管道阶段 3：`files_misc` 第一层文件分流。

阶段 3.0：stem 命中 junk 关键字的第一层文件迁入 ``files_to_delete``（无体积条件），
不再参与后续 3.1~3.4。

阶段 3.1~3.3：压缩 / 图片 / 音频迁入 ``files_compressed`` / ``files_pic`` / ``files_audio``。

阶段 3.4：视频扩展名归桶——按 stem 关键字顺序匹配迁入 ``files_video_*``；
均未命中则迁入 ``files_video_misc``。非视频且未知扩展名留在 ``files_misc``。

命名与冲突：``normalize_move_basename`` + ``move_file_with_conflict_resolution``（``-jfk-xxxx``）。
见 ``docs/RAW_FILE_PROCESSING_PIPELINE.md``。
"""

from pathlib import Path

from loguru import logger

from j_file_kit.app.file_task.application.file_ops import (
    move_file_with_conflict_resolution,
    normalize_move_basename,
)
from j_file_kit.app.file_task.application.raw_analyze_config import (
    RawAnalyzeConfig,
    classify_file_media_kind,
)
from j_file_kit.app.file_task.application.raw_pipeline.context import PhaseContext
from j_file_kit.app.file_task.application.raw_pipeline.counters import RawPhaseCounters
from j_file_kit.app.file_task.domain.organizer_defaults import (
    DEFAULT_CAMELCASE_NO_SPLIT_WORDS,
    DEFAULT_RAW_JUNK_KEYWORDS,
    DEFAULT_RAW_VIDEO_BUCKET_JAV_KEYWORDS,
    DEFAULT_RAW_VIDEO_BUCKET_JAV_VR_KEYWORDS,
    DEFAULT_RAW_VIDEO_BUCKET_MOVIE_KEYWORDS,
    DEFAULT_RAW_VIDEO_BUCKET_US_KEYWORDS,
    DEFAULT_RAW_VIDEO_BUCKET_US_VR_KEYWORDS,
)
from j_file_kit.shared.utils.file_utils import ensure_directory, sanitize_surrogate_str
from j_file_kit.shared.utils.name_keyword_match import (
    expand_keywords_camelcase,
    name_matches_any_keyword,
)

# 各视频桶关键词及 junk 关键词的 CamelCase 变体展开，模块初始化时计算一次
_JUNK_KW_EX: tuple[str, ...] = expand_keywords_camelcase(
    DEFAULT_RAW_JUNK_KEYWORDS, DEFAULT_CAMELCASE_NO_SPLIT_WORDS
)
_MOVIE_KW_EX: tuple[str, ...] = expand_keywords_camelcase(
    DEFAULT_RAW_VIDEO_BUCKET_MOVIE_KEYWORDS, DEFAULT_CAMELCASE_NO_SPLIT_WORDS
)
_US_VR_KW_EX: tuple[str, ...] = expand_keywords_camelcase(
    DEFAULT_RAW_VIDEO_BUCKET_US_VR_KEYWORDS, DEFAULT_CAMELCASE_NO_SPLIT_WORDS
)
_US_KW_EX: tuple[str, ...] = expand_keywords_camelcase(
    DEFAULT_RAW_VIDEO_BUCKET_US_KEYWORDS, DEFAULT_CAMELCASE_NO_SPLIT_WORDS
)
_JAV_VR_KW_EX: tuple[str, ...] = expand_keywords_camelcase(
    DEFAULT_RAW_VIDEO_BUCKET_JAV_VR_KEYWORDS, DEFAULT_CAMELCASE_NO_SPLIT_WORDS
)
_JAV_KW_EX: tuple[str, ...] = expand_keywords_camelcase(
    DEFAULT_RAW_VIDEO_BUCKET_JAV_KEYWORDS, DEFAULT_CAMELCASE_NO_SPLIT_WORDS
)


def classify_video_bucket(stem: str) -> str:
    """按产品顺序返回视频归宿桶标识（首个关键字命中即停）。

    返回值：``movie`` | ``us_vr`` | ``us`` | ``jav_vr`` | ``jav`` | ``misc``。
    ``misc`` 表示未命中任一关键字桶（迁入 ``files_video_misc``）。
    关键词匹配使用 CamelCase 变体展开，``LethalHardcoreVR`` 可命中 ``Lethal.Hardcore.VR`` 等变体。
    """
    if _stem_matches_any_bucket_keyword(stem, _MOVIE_KW_EX):
        return "movie"
    if _stem_matches_any_bucket_keyword(stem, _US_VR_KW_EX):
        return "us_vr"
    if _stem_matches_any_bucket_keyword(stem, _US_KW_EX):
        return "us"
    if _stem_matches_any_bucket_keyword(stem, _JAV_VR_KW_EX):
        return "jav_vr"
    if _stem_matches_any_bucket_keyword(stem, _JAV_KW_EX):
        return "jav"
    return "misc"


def _stem_matches_any_bucket_keyword(stem: str, keywords_ex: tuple[str, ...]) -> bool:
    return name_matches_any_keyword(stem, keywords_ex)


def _list_files_misc_level1(misc: Path) -> list[Path]:
    """``files_misc`` 下第一层普通文件，确定性排序。"""
    return sorted(p for p in misc.iterdir() if p.is_file())


def _phase30_stem_matches_probable_junk_keywords(
    path: Path,
    junk_keywords_norm: tuple[str, ...],
) -> bool:
    """与阶段 2.2 相同的 stem 关键字子串口径（规范化后）。"""
    return name_matches_any_keyword(path.stem, junk_keywords_norm)


def _phase30_preclean_misc_level1(
    ctx: PhaseContext,
    *,
    files: list[Path],
    junk_keywords_norm: tuple[str, ...],
    cfg: RawAnalyzeConfig,
    dry_run: bool,
    counters: RawPhaseCounters,
) -> list[Path]:
    """3.0：将 junk stem 第一层文件迁入 ``files_to_delete``（或 dry_run 预览）；返回剩余队列。"""
    remaining: list[Path] = []
    for path in files:
        if not _phase30_stem_matches_probable_junk_keywords(path, junk_keywords_norm):
            remaining.append(path)
            continue

        dest_root = cfg.files_to_delete

        if dry_run:
            counters.phase3_deleted_junk_misc += 1
            logger.bind(
                run_id=str(ctx.run_id),
                run_name=ctx.run_name,
                level="RAW_PHASE",
                phase=3,
                subphase="preclean_preview",
                source=str(path),
                target_dir=str(dest_root),
            ).info("阶段3.0（dry_run）：预览按 junk stem 迁出")
            continue

        basename = normalize_move_basename(sanitize_surrogate_str(path.name))
        target = dest_root / basename

        try:
            ensure_directory(dest_root, parents=True)
            final = move_file_with_conflict_resolution(path, target)
        except (OSError, RuntimeError) as e:
            logger.bind(
                run_id=str(ctx.run_id),
                run_name=ctx.run_name,
                level="RAW_PHASE",
                phase=3,
                subphase="preclean_move_error",
                source=str(path),
                target=str(target),
                error=str(e),
            ).warning("阶段3.0：junk stem 迁出失败")
            remaining.append(path)
            continue

        counters.phase3_deleted_junk_misc += 1
        logger.bind(
            run_id=str(ctx.run_id),
            run_name=ctx.run_name,
            level="RAW_PHASE",
            phase=3,
            subphase="preclean",
            source=str(path),
            target=str(final),
        ).info("阶段3.0：已按 junk stem 迁入 files_to_delete")

    return remaining


def _video_destination_root(bucket: str, cfg: RawAnalyzeConfig) -> Path:
    match bucket:
        case "movie":
            return cfg.files_video_movie
        case "us_vr":
            return cfg.files_video_us_vr
        case "us":
            return cfg.files_video_us
        case "jav_vr":
            return cfg.files_video_jav_vr
        case "jav":
            return cfg.files_video_jav
        case "misc":
            return cfg.files_video_misc
        case _:
            msg = f"阶段3.4 未知视频桶: {bucket}"
            raise RuntimeError(msg)


def _destination_root_for_routed_kind(kind: str, cfg: RawAnalyzeConfig) -> Path:
    match kind:
        case "archive":
            return cfg.files_compressed
        case "image":
            return cfg.files_pic
        case "audio":
            return cfg.files_audio
        case _:
            msg = f"阶段3 不支持的路由类型: {kind}"
            raise RuntimeError(msg)


def _move_routed_file(
    ctx: PhaseContext,
    path: Path,
    dest_root: Path,
    *,
    kind: str,
    video_bucket: str | None,
    dry_run: bool,
) -> bool:
    """迁移单个文件到目标目录；返回 True 表示成功（含 dry_run 预览），False 表示失败。"""
    basename = normalize_move_basename(sanitize_surrogate_str(path.name))
    target = dest_root / basename
    extra: dict[str, str] = {"kind": kind}
    if video_bucket is not None:
        extra["video_bucket"] = video_bucket

    if dry_run:
        logger.bind(
            run_id=str(ctx.run_id),
            run_name=ctx.run_name,
            level="RAW_PHASE",
            phase=3,
            subphase="route_preview",
            source=str(path),
            target=str(target),
            **extra,
        ).info("阶段3（dry_run）：预览分流")
        return True

    try:
        ensure_directory(dest_root, parents=True)
        final = move_file_with_conflict_resolution(path, target)
        logger.bind(
            run_id=str(ctx.run_id),
            run_name=ctx.run_name,
            level="RAW_PHASE",
            phase=3,
            subphase="route",
            source=str(path),
            target=str(final),
            **extra,
        ).info("阶段3：文件已分流")
        return True
    except (OSError, RuntimeError) as e:
        logger.bind(
            run_id=str(ctx.run_id),
            run_name=ctx.run_name,
            level="RAW_PHASE",
            phase=3,
            subphase="route_error",
            source=str(path),
            error=str(e),
            **extra,
        ).error("阶段3：分流失败")
        return False


def run_phase3(
    ctx: PhaseContext,
    counters: RawPhaseCounters,
    *,
    dry_run: bool,
) -> None:
    """阶段 3：``files_misc`` 第一层预清理后按扩展名与视频关键字迁入各类 ``files_*``。"""
    misc = ctx.analyze_config.files_misc
    if not misc.exists() or not misc.is_dir():
        counters.phase3_seen_files_misc = 0
        counters.phase3_deleted_junk_misc = 0
        counters.phase3_deferred_files_misc = 0
        logger.bind(
            run_id=str(ctx.run_id),
            run_name=ctx.run_name,
            level="RAW_PHASE",
            phase=3,
        ).info("阶段3：files_misc 不可用或不存在，跳过")
        return

    level1_before = _list_files_misc_level1(misc)
    files = _phase30_preclean_misc_level1(
        ctx,
        files=level1_before,
        junk_keywords_norm=_JUNK_KW_EX,
        cfg=ctx.analyze_config,
        dry_run=dry_run,
        counters=counters,
    )
    counters.phase3_seen_files_misc = len(files)

    deferred = 0
    routed_ok = 0

    for path in files:
        kind = classify_file_media_kind(path.suffix, ctx.analyze_config)
        if kind is None:
            deferred += 1
            continue

        if kind in ("video", "subtitle"):
            # 字幕与视频共用桶路由：stem 关键字匹配决定目标 files_video_* 目录
            bucket = classify_video_bucket(path.stem)
            dest_root = _video_destination_root(bucket, ctx.analyze_config)
            ok = _move_routed_file(
                ctx, path, dest_root, kind=kind, video_bucket=bucket, dry_run=dry_run
            )
        else:
            dest_root = _destination_root_for_routed_kind(kind, ctx.analyze_config)
            ok = _move_routed_file(
                ctx, path, dest_root, kind=kind, video_bucket=None, dry_run=dry_run
            )

        if ok:
            routed_ok += 1
        else:
            deferred += 1

    counters.phase3_deferred_files_misc = deferred

    logger.bind(
        run_id=str(ctx.run_id),
        run_name=ctx.run_name,
        level="RAW_PHASE",
        phase=3,
        misc_level1_before=len(level1_before),
        moved_junk_preclean=counters.phase3_deleted_junk_misc,
        seen_after_preclean=len(files),
        routed=routed_ok,
        deferred=deferred,
    ).info("阶段3完成：files_misc 第一层文件已处理")
