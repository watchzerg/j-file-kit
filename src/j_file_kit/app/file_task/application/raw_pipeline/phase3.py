"""Raw 管道阶段 3：`files_misc` 第一层文件按扩展名分流。

将压缩 / 图片 / 音频迁入 ``files_compressed`` / ``files_pic`` / ``files_audio``；
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
from j_file_kit.shared.utils.file_utils import ensure_directory, sanitize_surrogate_str


def _list_files_misc_level1(misc: Path) -> list[Path]:
    """``files_misc`` 下第一层普通文件，确定性排序。"""
    return sorted(p for p in misc.iterdir() if p.is_file())


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
        counters.phase3_deferred_files_misc = 0
        logger.bind(
            run_id=str(ctx.run_id),
            run_name=ctx.run_name,
            level="RAW_PHASE",
            phase=3,
        ).info("阶段3：files_misc 不可用或不存在，跳过")
        return

    files = _list_files_misc_level1(misc)
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
        seen=len(files),
        routed=routed_ok,
        deferred=deferred,
    ).info("阶段3完成：files_misc 第一层文件已处理")
