"""Raw 阶段 2.2：第一层目录内垃圾文件删除与空目录收缩。"""

import threading
from pathlib import Path

from loguru import logger

from j_file_kit.app.file_task.application.file_ops import scan_directory_items
from j_file_kit.app.file_task.application.raw_pipeline.context import PhaseContext
from j_file_kit.app.file_task.application.raw_pipeline.counters import RawPhaseCounters
from j_file_kit.app.file_task.application.raw_pipeline.keywords import (
    normalize_for_match,
)
from j_file_kit.app.file_task.domain.file_types import PathEntryType
from j_file_kit.app.file_task.domain.organizer_defaults import (
    DEFAULT_MISC_FILE_DELETE_EXTENSIONS,
)


def should_delete_clean_file(
    path: Path,
    *,
    misc_delete_ext: frozenset[str],
    junk_keywords_norm: tuple[str, ...],
) -> bool:
    """是否应删除该文件（扩展名 / stem 关键字 / 0 字节）。"""
    ext = path.suffix.lower()
    if ext in misc_delete_ext:
        return True
    stem_norm = normalize_for_match(path.stem)
    if any(k in stem_norm for k in junk_keywords_norm if k):
        return True
    try:
        if path.is_file() and path.stat().st_size == 0:
            return True
    except OSError:
        return False
    return False


def _maybe_delete_candidate_file(
    ctx: PhaseContext,
    path: Path,
    phases: RawPhaseCounters,
    *,
    misc_ext: frozenset[str],
    junk_keywords_norm: tuple[str, ...],
    dry_run: bool,
) -> None:
    if not should_delete_clean_file(
        path,
        misc_delete_ext=misc_ext,
        junk_keywords_norm=junk_keywords_norm,
    ):
        return
    if dry_run:
        phases.phase2_cleaned_deleted_files += 1
        return
    try:
        path.unlink()
        phases.phase2_cleaned_deleted_files += 1
    except OSError as e:
        logger.bind(
            run_id=str(ctx.run_id),
            run_name=ctx.run_name,
            error=str(e),
        ).warning(f"阶段2.2：删除文件失败 {path}")


def _maybe_rmdir_below_root(
    ctx: PhaseContext,
    path: Path,
    root_resolved: Path,
    phases: RawPhaseCounters,
    *,
    dry_run: bool,
) -> None:
    if path.resolve(strict=False) == root_resolved:
        return
    if not path.exists() or not path.is_dir():
        return
    if any(path.iterdir()):
        return
    if dry_run:
        phases.phase2_cleaned_deleted_empty_dirs += 1
        return
    try:
        path.rmdir()
        phases.phase2_cleaned_deleted_empty_dirs += 1
    except OSError as e:
        logger.bind(
            run_id=str(ctx.run_id),
            run_name=ctx.run_name,
            error=str(e),
        ).warning(f"阶段2.2：删除空目录失败 {path}")


def _maybe_rmdir_root(
    ctx: PhaseContext,
    root_dir: Path,
    phases: RawPhaseCounters,
    *,
    dry_run: bool,
) -> None:
    if not root_dir.exists() or not root_dir.is_dir():
        return
    if any(root_dir.iterdir()):
        return
    if dry_run:
        phases.phase2_cleaned_deleted_empty_dirs += 1
        return
    try:
        root_dir.rmdir()
        phases.phase2_cleaned_deleted_empty_dirs += 1
    except OSError as e:
        logger.bind(
            run_id=str(ctx.run_id),
            run_name=ctx.run_name,
            error=str(e),
        ).warning(f"阶段2.2：删除空的第一层目录失败 {root_dir}")


def clean_level1_dir(
    ctx: PhaseContext,
    root_dir: Path,
    phases: RawPhaseCounters,
    *,
    junk_keywords_norm: tuple[str, ...],
    dry_run: bool,
    cancellation_event: threading.Event | None,
) -> bool:
    """遍历目录删除垃圾文件与空子目录；返回 True 表示已请求取消。"""
    misc_ext = DEFAULT_MISC_FILE_DELETE_EXTENSIONS
    root_resolved = root_dir.resolve(strict=False)

    try:
        for path, kind in scan_directory_items(root_dir):
            if cancellation_event and cancellation_event.is_set():
                return True
            if kind == PathEntryType.FILE:
                _maybe_delete_candidate_file(
                    ctx,
                    path,
                    phases,
                    misc_ext=misc_ext,
                    junk_keywords_norm=junk_keywords_norm,
                    dry_run=dry_run,
                )
            elif kind == PathEntryType.DIRECTORY:
                _maybe_rmdir_below_root(
                    ctx,
                    path,
                    root_resolved,
                    phases,
                    dry_run=dry_run,
                )

        _maybe_rmdir_root(ctx, root_dir, phases, dry_run=dry_run)
    except FileNotFoundError:
        pass
    except NotADirectoryError:
        pass

    return False
