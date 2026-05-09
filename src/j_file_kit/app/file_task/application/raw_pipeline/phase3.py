"""Raw 管道阶段 3：`files_misc` 第一层文件按扩展名分流。

阶段 3.0：对 stem 命中垃圾关键字且体积低于阈值的单层文件预先删除；
再将压缩 / 图片 / 音频迁入 ``files_compressed`` / ``files_pic`` / ``files_audio``；
视频与未知扩展名暂留在 ``files_misc``（视频占位，后续迭代）。
命名与冲突与阶段 1 / 阶段 2.4 拆解一致：``normalize_move_basename`` +
``move_file_with_conflict_resolution``（``-jfk-xxxx``）。见
``docs/RAW_FILE_PROCESSING_PIPELINE.md``。
"""

from pathlib import Path

from loguru import logger

from j_file_kit.app.file_task.application.file_ops import (
    move_file_with_conflict_resolution,
    normalize_move_basename,
)
from j_file_kit.app.file_task.application.raw_analyze_config import RawAnalyzeConfig
from j_file_kit.app.file_task.application.raw_pipeline.context import PhaseContext
from j_file_kit.app.file_task.application.raw_pipeline.counters import RawPhaseCounters
from j_file_kit.app.file_task.application.raw_pipeline.keywords import (
    normalize_for_match,
    normalize_keyword_tokens,
)
from j_file_kit.app.file_task.domain.organizer_defaults import (
    DEFAULT_RAW_JUNK_KEYWORDS,
    DEFAULT_RAW_PHASE30_FILE_MAX_BYTES,
)
from j_file_kit.shared.utils.file_utils import ensure_directory, sanitize_surrogate_str


def _list_files_misc_level1(misc: Path) -> list[Path]:
    """``files_misc`` 下第一层普通文件，确定性排序。"""
    return sorted(p for p in misc.iterdir() if p.is_file())


def _phase30_stem_matches_probable_junk_keywords(
    path: Path,
    junk_keywords_norm: tuple[str, ...],
) -> bool:
    """与阶段 2.2 相同的 stem 关键字子串口径（规范化后）。"""
    stem_norm = normalize_for_match(path.stem)
    return any(k in stem_norm for k in junk_keywords_norm if k)


def _phase30_preclean_misc_level1(
    ctx: PhaseContext,
    *,
    files: list[Path],
    junk_keywords_norm: tuple[str, ...],
    dry_run: bool,
    counters: RawPhaseCounters,
) -> list[Path]:
    """3.0：删除（或 dry_run 预览）stem junk 且单文件体积 < 阈值的第一层文件；返回剩余队列。"""
    remaining: list[Path] = []
    for path in files:
        if not _phase30_stem_matches_probable_junk_keywords(path, junk_keywords_norm):
            remaining.append(path)
            continue
        try:
            size = path.stat().st_size
        except OSError as e:
            logger.bind(
                run_id=str(ctx.run_id),
                run_name=ctx.run_name,
                level="RAW_PHASE",
                phase=3,
                subphase="preclean_stat_error",
                source=str(path),
                error=str(e),
            ).warning("阶段3.0：无法获取文件体积，跳过预删")
            remaining.append(path)
            continue
        if size >= DEFAULT_RAW_PHASE30_FILE_MAX_BYTES:
            remaining.append(path)
            continue

        if dry_run:
            counters.phase3_deleted_junk_misc += 1
            logger.bind(
                run_id=str(ctx.run_id),
                run_name=ctx.run_name,
                level="RAW_PHASE",
                phase=3,
                subphase="preclean_preview",
                source=str(path),
                size_bytes=size,
            ).info("阶段3.0（dry_run）：预览按 junk stem 预删")
            continue

        try:
            path.unlink()
        except OSError as e:
            logger.bind(
                run_id=str(ctx.run_id),
                run_name=ctx.run_name,
                level="RAW_PHASE",
                phase=3,
                subphase="preclean_unlink_error",
                source=str(path),
                error=str(e),
            ).warning("阶段3.0：预删失败")
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
            size_bytes=size,
        ).info("阶段3.0：已按 junk stem 预删")

    return remaining


def _classify_misc_file_suffix(suffix: str, cfg: RawAnalyzeConfig) -> str | None:
    """按扩展名归类；顺序与阶段 2.4 ``_media_kind_flat`` 一致。"""
    ext = suffix.lower()
    if ext in cfg.image_extensions:
        return "image"
    if ext in cfg.video_extensions:
        return "video"
    if ext in cfg.audio_extensions:
        return "audio"
    if ext in cfg.archive_extensions:
        return "archive"
    return None


def _preflight_phase3_destinations(files: list[Path], cfg: RawAnalyzeConfig) -> None:
    """若存在待分流的压缩 / 图片 / 音频文件，则要求对应 ``files_*`` 目录已配置。"""
    needs_archive = needs_image = needs_audio = False
    for path in files:
        kind = _classify_misc_file_suffix(path.suffix, cfg)
        if kind == "archive":
            needs_archive = True
        elif kind == "image":
            needs_image = True
        elif kind == "audio":
            needs_audio = True
    if needs_archive and cfg.files_compressed is None:
        msg = "files_compressed 未设置（files_misc 中存在待分流的压缩文件）"
        raise ValueError(msg)
    if needs_image and cfg.files_pic is None:
        msg = "files_pic 未设置（files_misc 中存在待分流的图片文件）"
        raise ValueError(msg)
    if needs_audio and cfg.files_audio is None:
        msg = "files_audio 未设置（files_misc 中存在待分流的音频文件）"
        raise ValueError(msg)


def _destination_root_for_routed_kind(kind: str, cfg: RawAnalyzeConfig) -> Path:
    match kind:
        case "archive":
            dest = cfg.files_compressed
        case "image":
            dest = cfg.files_pic
        case "audio":
            dest = cfg.files_audio
        case _:
            msg = f"阶段3 不支持的路由类型: {kind}"
            raise RuntimeError(msg)
    if dest is None:
        msg = f"阶段3 归宿目录未注入: {kind}"
        raise RuntimeError(msg)
    return dest


def run_phase3(
    ctx: PhaseContext,
    counters: RawPhaseCounters,
    *,
    dry_run: bool,
) -> None:
    """阶段 3：将 ``files_misc`` 第一层中可归类的文件迁入 ``files_*``；视频与未知扩展名延后。"""
    misc = ctx.analyze_config.files_misc
    if misc is None or not misc.exists() or not misc.is_dir():
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
    junk_norm = normalize_keyword_tokens(DEFAULT_RAW_JUNK_KEYWORDS)
    files = _phase30_preclean_misc_level1(
        ctx,
        files=level1_before,
        junk_keywords_norm=junk_norm,
        dry_run=dry_run,
        counters=counters,
    )
    counters.phase3_seen_files_misc = len(files)
    _preflight_phase3_destinations(files, ctx.analyze_config)

    deferred = 0
    routed_ok = 0

    for path in files:
        kind = _classify_misc_file_suffix(path.suffix, ctx.analyze_config)
        if kind is None or kind == "video":
            deferred += 1
            continue

        dest_root = _destination_root_for_routed_kind(kind, ctx.analyze_config)
        basename = normalize_move_basename(sanitize_surrogate_str(path.name))
        target = dest_root / basename

        if dry_run:
            routed_ok += 1
            logger.bind(
                run_id=str(ctx.run_id),
                run_name=ctx.run_name,
                level="RAW_PHASE",
                phase=3,
                subphase="route_preview",
                kind=kind,
                source=str(path),
                target=str(target),
            ).info("阶段3（dry_run）：预览分流")
            continue

        try:
            ensure_directory(dest_root, parents=True)
            final = move_file_with_conflict_resolution(path, target)
            routed_ok += 1
            logger.bind(
                run_id=str(ctx.run_id),
                run_name=ctx.run_name,
                level="RAW_PHASE",
                phase=3,
                subphase="route",
                kind=kind,
                source=str(path),
                target=str(final),
            ).info("阶段3：文件已分流")
        except (OSError, RuntimeError) as e:
            deferred += 1
            logger.bind(
                run_id=str(ctx.run_id),
                run_name=ctx.run_name,
                level="RAW_PHASE",
                phase=3,
                subphase="route_error",
                kind=kind,
                source=str(path),
                error=str(e),
            ).error("阶段3：分流失败")

    counters.phase3_deferred_files_misc = deferred

    logger.bind(
        run_id=str(ctx.run_id),
        run_name=ctx.run_name,
        level="RAW_PHASE",
        phase=3,
        misc_level1_before=len(level1_before),
        deleted_junk_preclean=counters.phase3_deleted_junk_misc,
        seen_after_preclean=len(files),
        routed=routed_ok,
        deferred=deferred,
    ).info("阶段3完成：files_misc 第一层文件已处理")
