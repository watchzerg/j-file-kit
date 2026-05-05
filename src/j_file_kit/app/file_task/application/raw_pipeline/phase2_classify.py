"""Raw 阶段 2.4：小目录拆解到 ``files_misc`` 或整目录按媒体画像迁入 ``folders_*``。"""

import threading
from pathlib import Path

from loguru import logger

from j_file_kit.app.file_task.application.file_ops import (
    move_directory_with_conflict_resolution,
    move_file_with_conflict_resolution,
    normalize_move_basename,
    scan_directory_items,
)
from j_file_kit.app.file_task.application.raw_analyze_config import RawAnalyzeConfig
from j_file_kit.app.file_task.application.raw_pipeline.context import PhaseContext
from j_file_kit.app.file_task.application.raw_pipeline.counters import RawPhaseCounters
from j_file_kit.app.file_task.domain.file_types import PathEntryType
from j_file_kit.shared.utils.file_utils import ensure_directory, sanitize_surrogate_str


def _list_direct_entries(dir_path: Path) -> tuple[list[Path], list[Path]]:
    files: list[Path] = []
    subdirs: list[Path] = []
    try:
        for p in dir_path.iterdir():
            if p.is_dir():
                subdirs.append(p)
            elif p.is_file():
                files.append(p)
    except OSError:
        return [], []
    files.sort(key=lambda x: x.name)
    subdirs.sort(key=lambda x: x.name)
    return files, subdirs


def _media_kind_flat(suffix: str, cfg: RawAnalyzeConfig) -> str | None:
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


def _media_kind_dir(suffix: str, cfg: RawAnalyzeConfig) -> str:
    ext = suffix.lower()
    if ext in cfg.image_extensions:
        return "image"
    if ext in cfg.video_extensions:
        return "video"
    if ext in cfg.audio_extensions:
        return "audio"
    if ext in cfg.archive_extensions:
        return "archive"
    if ext in cfg.subtitle_extensions:
        return "subtitle"
    return "unknown"


def _flatten_kinds_allowed(kinds: set[str]) -> bool:
    if len(kinds) == 1:
        return True
    return len(kinds) == 2 and "image" in kinds


def should_flatten_small_dir(files: list[Path], cfg: RawAnalyzeConfig) -> bool:
    """单层且文件数<=5，且扩展名均在拆解允许集合内且类型组合合法。"""
    if len(files) == 0 or len(files) > 5:
        return False
    kinds: set[str] = set()
    for p in files:
        k = _media_kind_flat(p.suffix, cfg)
        if k is None:
            return False
        kinds.add(k)
    return _flatten_kinds_allowed(kinds)


def _whole_dir_destination_for_kinds(
    kinds: set[str],
    cfg: RawAnalyzeConfig,
) -> tuple[Path, str]:
    pic = cfg.folders_pic
    audio = cfg.folders_audio
    compressed = cfg.folders_compressed
    video = cfg.folders_video
    misc_root = cfg.folders_misc
    if (
        pic is None
        or audio is None
        or compressed is None
        or video is None
        or misc_root is None
    ):
        msg = "阶段2.4 归宿目录未注入（违反前置校验）"
        raise RuntimeError(msg)

    if not kinds:
        return misc_root, "misc"
    if kinds <= {"image"}:
        return pic, "pic"
    if kinds <= {"audio", "image"} and "audio" in kinds:
        return audio, "audio"
    if kinds <= {"archive", "image"} and "archive" in kinds:
        return compressed, "compressed"
    if kinds <= {"video", "image"} and "video" in kinds:
        return video, "video"
    return misc_root, "misc"


def _inc_whole_dir_bucket(phases: RawPhaseCounters, bucket: str) -> None:
    if bucket == "pic":
        phases.phase2_moved_to_pic_dirs += 1
    elif bucket == "audio":
        phases.phase2_moved_to_audio_dirs += 1
    elif bucket == "compressed":
        phases.phase2_moved_to_compressed_dirs += 1
    elif bucket == "video":
        phases.phase2_moved_to_video_dirs += 1
    else:
        phases.phase2_moved_to_misc_dirs += 1


def _collect_descendant_file_media_kinds(
    dir_path: Path,
    cfg: RawAnalyzeConfig,
) -> set[str]:
    kinds: set[str] = set()
    try:
        for path, kind in scan_directory_items(dir_path):
            if kind == PathEntryType.FILE:
                kinds.add(_media_kind_dir(path.suffix, cfg))
    except FileNotFoundError, NotADirectoryError:
        pass
    return kinds


def _move_whole_classified_dir(
    ctx: PhaseContext,
    dir_path: Path,
    phases: RawPhaseCounters,
    *,
    dry_run: bool,
) -> None:
    kinds = _collect_descendant_file_media_kinds(dir_path, ctx.analyze_config)

    dest_root, bucket = _whole_dir_destination_for_kinds(
        kinds,
        ctx.analyze_config,
    )
    target = dest_root / dir_path.name
    safe = sanitize_surrogate_str(str(dir_path))

    if dry_run:
        _inc_whole_dir_bucket(phases, bucket)
        logger.bind(
            run_id=str(ctx.run_id),
            run_name=ctx.run_name,
            level="RAW_PHASE",
            phase=2,
            subphase="classify_whole_preview",
            source=safe,
            target=str(target),
            bucket=bucket,
        ).info("阶段2.4（dry_run）：预览整目录分类迁移")
        return

    try:
        ensure_directory(dest_root, parents=True)
        final = move_directory_with_conflict_resolution(dir_path, target)
        _inc_whole_dir_bucket(phases, bucket)
        logger.bind(
            run_id=str(ctx.run_id),
            run_name=ctx.run_name,
            level="RAW_PHASE",
            phase=2,
            subphase="classify_whole",
            source=safe,
            target=str(final),
            bucket=bucket,
        ).info("阶段2.4：整目录已迁入归宿")
    except Exception as e:
        phases.phase2_classification_errors += 1
        logger.bind(
            run_id=str(ctx.run_id),
            run_name=ctx.run_name,
            error=str(e),
            source=safe,
            bucket=bucket,
        ).error("阶段2.4：整目录迁移失败")


def flatten_dir_into_misc(
    ctx: PhaseContext,
    dir_path: Path,
    phases: RawPhaseCounters,
    *,
    dry_run: bool,
    cancellation_event: threading.Event | None,
) -> bool:
    """拆解单层目录；``True`` 表示迁移过程中检测到取消。"""
    misc = ctx.analyze_config.files_misc
    if misc is None:
        phases.phase2_classification_errors += 1
        return False

    files, subdirs = _list_direct_entries(dir_path)
    if subdirs or not files:
        phases.phase2_classification_errors += 1
        return False

    dir_name = dir_path.name
    safe_dir = sanitize_surrogate_str(str(dir_path))

    if dry_run:
        phases.phase2_flattened_dirs += 1
        phases.phase2_flattened_files += len(files)
        logger.bind(
            run_id=str(ctx.run_id),
            run_name=ctx.run_name,
            level="RAW_PHASE",
            phase=2,
            subphase="classify_flatten_preview",
            dir=safe_dir,
            files=len(files),
        ).info("阶段2.4（dry_run）：预览拆解目录到 files_misc")
        return False

    try:
        ensure_directory(misc, parents=True)
        for path in files:
            if cancellation_event and cancellation_event.is_set():
                logger.bind(
                    run_id=str(ctx.run_id),
                    run_name=ctx.run_name,
                    level="RAW_PHASE",
                    phase=2,
                    subphase="classify_flatten_cancelled",
                    dir=safe_dir,
                ).info("任务已被取消（阶段2.4 拆解迁移文件循环内）")
                return True
            dest_base = (
                path.name
                if path.stem == dir_name
                else f"{dir_name}_{path.stem}{path.suffix}"
            )
            normalized = normalize_move_basename(dest_base)
            target = misc / normalized
            move_file_with_conflict_resolution(path, target)

        phases.phase2_flattened_dirs += 1
        phases.phase2_flattened_files += len(files)

        try:
            if dir_path.is_dir() and not any(dir_path.iterdir()):
                dir_path.rmdir()
                phases.phase2_removed_dirs += 1
        except OSError:
            pass

        logger.bind(
            run_id=str(ctx.run_id),
            run_name=ctx.run_name,
            level="RAW_PHASE",
            phase=2,
            subphase="classify_flatten",
            dir=safe_dir,
            files=len(files),
        ).info("阶段2.4：目录已拆解并入 files_misc")
    except Exception as e:
        phases.phase2_classification_errors += 1
        logger.bind(
            run_id=str(ctx.run_id),
            run_name=ctx.run_name,
            error=str(e),
            dir=safe_dir,
        ).error("阶段2.4：拆解目录失败")

    return False


def run_phase2_classify(
    ctx: PhaseContext,
    dir_path: Path,
    phases: RawPhaseCounters,
    *,
    dry_run: bool,
    cancellation_event: threading.Event | None,
) -> bool:
    """先尝试小目录拆解，否则整目录归入 ``folders_*``；``True`` 表示应终止阶段 2（取消）。"""
    if cancellation_event and cancellation_event.is_set():
        return True
    if not dir_path.exists() or not dir_path.is_dir():
        return False

    files, subdirs = _list_direct_entries(dir_path)
    if subdirs:
        if cancellation_event and cancellation_event.is_set():
            return True
        _move_whole_classified_dir(ctx, dir_path, phases, dry_run=dry_run)
        return False

    if should_flatten_small_dir(files, ctx.analyze_config):
        return flatten_dir_into_misc(
            ctx,
            dir_path,
            phases,
            dry_run=dry_run,
            cancellation_event=cancellation_event,
        )

    if cancellation_event and cancellation_event.is_set():
        return True
    _move_whole_classified_dir(ctx, dir_path, phases, dry_run=dry_run)
    return False
