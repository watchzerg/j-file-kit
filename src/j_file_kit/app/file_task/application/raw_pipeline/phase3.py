"""Raw 管道阶段 3：`files_misc` 第一层文件分流。

阶段 3.0：stem 命中 junk 关键字的第一层文件迁入 ``files_to_delete``（无体积条件），
不再参与后续 3.1~3.4。

阶段 3.1~3.3：压缩 / 图片 / 音频迁入 ``files_compressed`` / ``files_pic`` / ``files_audio``。

阶段 3.4：视频扩展名归桶——movie / us_vr / us 按 stem 关键字顺序匹配；
其余通过 JAV 番号识别分流至 ``files_video_jav_vr`` / ``files_video_jav`` / ``files_video_misc``。
非视频且未知扩展名留在 ``files_misc``。

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
from j_file_kit.app.file_task.application.raw_pipeline.video_bucket_classifier import (
    _JUNK_KW_EX,
    classify_video_bucket_and_subdir,
)
from j_file_kit.shared.utils.file_utils import ensure_directory, sanitize_surrogate_str
from j_file_kit.shared.utils.name_keyword_match import name_matches_any_keyword


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


def _video_destination_root(
    bucket: str, cfg: RawAnalyzeConfig, subdir: str | None = None
) -> Path:
    match bucket:
        case "movie":
            return cfg.files_video_movie / subdir if subdir else cfg.files_video_movie
        case "us_vr":
            return cfg.files_video_us_vr / subdir if subdir else cfg.files_video_us_vr
        case "us":
            return cfg.files_video_us / subdir if subdir else cfg.files_video_us
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
    subdir: str | None = None,
    dry_run: bool,
) -> bool:
    """迁移单个文件到目标目录；返回 True 表示成功（含 dry_run 预览），False 表示失败。"""
    basename = normalize_move_basename(sanitize_surrogate_str(path.name))
    target = dest_root / basename
    extra: dict[str, str] = {"kind": kind}
    if video_bucket is not None:
        extra["video_bucket"] = video_bucket
    if subdir is not None:
        extra["subdir"] = subdir

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


def _increment_video_bucket_counter(counters: RawPhaseCounters, bucket: str) -> None:
    match bucket:
        case "movie":
            counters.phase3_routed_video_movie_files += 1
        case "us_vr":
            counters.phase3_routed_video_us_vr_files += 1
        case "us":
            counters.phase3_routed_video_us_files += 1
        case "jav_vr":
            counters.phase3_routed_video_jav_vr_files += 1
        case "jav":
            counters.phase3_routed_video_jav_files += 1
        case "misc":
            counters.phase3_routed_video_misc_files += 1
        case _:
            msg = f"阶段3.4 未知视频桶: {bucket}"
            raise RuntimeError(msg)


def _increment_routed_counter(
    counters: RawPhaseCounters,
    kind: str,
    *,
    video_bucket: str | None,
) -> None:
    if kind == "archive":
        counters.phase3_routed_archive_files += 1
        return
    if kind == "image":
        counters.phase3_routed_image_files += 1
        return
    if kind == "audio":
        counters.phase3_routed_audio_files += 1
        return
    if kind in ("video", "subtitle"):
        if video_bucket is None:
            msg = "阶段3.4 缺少视频桶信息"
            raise RuntimeError(msg)
        counters.phase3_routed_video_files += 1
        _increment_video_bucket_counter(counters, video_bucket)
        return
    msg = f"阶段3 不支持的路由类型: {kind}"
    raise RuntimeError(msg)


def _route_phase3_file(
    ctx: PhaseContext,
    path: Path,
    *,
    kind: str,
    dry_run: bool,
) -> tuple[bool, str | None]:
    if kind in ("video", "subtitle"):
        bucket, subdir = classify_video_bucket_and_subdir(path.stem)
        dest_root = _video_destination_root(bucket, ctx.analyze_config, subdir)
        ok = _move_routed_file(
            ctx,
            path,
            dest_root,
            kind=kind,
            video_bucket=bucket,
            subdir=subdir,
            dry_run=dry_run,
        )
        return ok, bucket

    dest_root = _destination_root_for_routed_kind(kind, ctx.analyze_config)
    ok = _move_routed_file(
        ctx,
        path,
        dest_root,
        kind=kind,
        video_bucket=None,
        dry_run=dry_run,
    )
    return ok, None


def run_phase3(
    ctx: PhaseContext,
    counters: RawPhaseCounters,
    *,
    dry_run: bool,
) -> None:
    """阶段 3：``files_misc`` 第一层预清理后按扩展名与视频关键字迁入各类 ``files_*``。

    统计口径：
    - `phase3_seen_files_misc` 基于 3.0 预清理后的待分流队列。
    - `phase3_deferred_files_misc` = `phase3_deferred_unknown_extension_files` + `phase3_deferred_error_files`。
    - `phase3_routed_video_files` 为视频总量，等于 6 个视频子桶计数之和。
    """
    misc = ctx.analyze_config.files_misc
    if not misc.exists() or not misc.is_dir():
        counters.phase3_seen_files_misc = 0
        counters.phase3_deleted_junk_misc = 0
        counters.phase3_deferred_files_misc = 0
        counters.phase3_routed_archive_files = 0
        counters.phase3_routed_image_files = 0
        counters.phase3_routed_audio_files = 0
        counters.phase3_routed_video_files = 0
        counters.phase3_routed_video_movie_files = 0
        counters.phase3_routed_video_us_vr_files = 0
        counters.phase3_routed_video_us_files = 0
        counters.phase3_routed_video_jav_vr_files = 0
        counters.phase3_routed_video_jav_files = 0
        counters.phase3_routed_video_misc_files = 0
        counters.phase3_deferred_unknown_extension_files = 0
        counters.phase3_deferred_error_files = 0
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

    deferred_unknown = 0
    deferred_error = 0
    routed_ok = 0

    for path in files:
        kind = classify_file_media_kind(path.suffix, ctx.analyze_config)
        if kind is None:
            deferred_unknown += 1
            continue

        ok, video_bucket = _route_phase3_file(ctx, path, kind=kind, dry_run=dry_run)

        if ok:
            routed_ok += 1
            _increment_routed_counter(counters, kind, video_bucket=video_bucket)
        else:
            deferred_error += 1

    counters.phase3_deferred_unknown_extension_files = deferred_unknown
    counters.phase3_deferred_error_files = deferred_error
    counters.phase3_deferred_files_misc = deferred_unknown + deferred_error

    logger.bind(
        run_id=str(ctx.run_id),
        run_name=ctx.run_name,
        level="RAW_PHASE",
        phase=3,
        misc_level1_before=len(level1_before),
        moved_junk_preclean=counters.phase3_deleted_junk_misc,
        seen_after_preclean=len(files),
        routed=routed_ok,
        deferred_unknown=deferred_unknown,
        deferred_error=deferred_error,
        deferred=counters.phase3_deferred_files_misc,
    ).info("阶段3完成：files_misc 第一层文件已处理")
