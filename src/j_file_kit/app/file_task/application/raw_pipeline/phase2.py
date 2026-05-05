"""Raw 管道阶段 2：inbox 第一层目录（关键字迁出 / 清洗 / 分类占位）。

迁出前预先判断是否存在「待删除关键字」目录：若存在则必须配置 `folders_to_delete`，
避免半套配置在 run 中途才失败。行为见仓库根目录 `docs/RAW_FILE_PROCESSING_PIPELINE.md`。"""

import threading
from pathlib import Path

from loguru import logger

from j_file_kit.app.file_task.application.file_ops import (
    move_directory_with_conflict_resolution,
    scan_directory_items,
)
from j_file_kit.app.file_task.application.raw_pipeline.context import PhaseContext
from j_file_kit.app.file_task.application.raw_pipeline.counters import RawPhaseCounters
from j_file_kit.app.file_task.application.raw_pipeline.keywords import (
    dir_name_matches,
    normalize_for_match,
    normalize_keyword_tokens,
)
from j_file_kit.app.file_task.domain.models import PathEntryType
from j_file_kit.app.file_task.domain.organizer_defaults import (
    DEFAULT_MISC_FILE_DELETE_EXTENSIONS,
    DEFAULT_PROBABLE_JUNK_MEDIA_KEYWORDS,
    DEFAULT_RAW_DIR_TO_DELETE_KEYWORDS,
)
from j_file_kit.shared.utils.file_utils import ensure_directory, sanitize_surrogate_str


def _list_inbox_level1_dirs(scan_root: Path) -> list[Path]:
    """第一层子目录，确定性排序；与旧 `RawFilePipeline.list_inbox_level1_dirs` 前置条件一致。"""
    if not scan_root.exists():
        raise FileNotFoundError(f"扫描目录不存在: {scan_root}")
    if not scan_root.is_dir():
        raise NotADirectoryError(f"路径不是目录: {scan_root}")
    return sorted(p for p in scan_root.iterdir() if p.is_dir())


def _should_delete_clean_file(
    path: Path,
    *,
    misc_delete_ext: frozenset[str],
    junk_keywords_norm: tuple[str, ...],
) -> bool:
    """阶段 2.2：是否应删除该文件（扩展名 / stem 关键字 / 0 字节）。"""
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


def _move_dir_to_delete(
    ctx: PhaseContext,
    dir_path: Path,
    phases: RawPhaseCounters,
    *,
    dest_delete: Path,
    dry_run: bool,
) -> None:
    """阶段 2.1：整目录迁入 `folders_to_delete`（目录级冲突消解）。"""
    target = dest_delete / dir_path.name
    safe = sanitize_surrogate_str(str(dir_path))
    if dry_run:
        phases.phase2_moved_to_delete_dirs += 1
        logger.bind(
            run_id=str(ctx.run_id),
            run_name=ctx.run_name,
            level="RAW_PHASE",
            phase=2,
            subphase="to_delete_preview",
            source=safe,
            target=str(target),
        ).info("阶段2.1（dry_run）：预览整目录迁出到 folders_to_delete")
        return

    try:
        ensure_directory(dest_delete, parents=True)
        final = move_directory_with_conflict_resolution(dir_path, target)
        phases.phase2_moved_to_delete_dirs += 1
        logger.bind(
            run_id=str(ctx.run_id),
            run_name=ctx.run_name,
            level="RAW_PHASE",
            phase=2,
            subphase="to_delete",
            source=safe,
            target=str(final),
        ).info("阶段2.1：整目录已迁入 folders_to_delete")
    except Exception as e:
        logger.bind(
            run_id=str(ctx.run_id),
            run_name=ctx.run_name,
            error=str(e),
            source=safe,
        ).error("阶段2.1：整目录迁出失败")


def _maybe_delete_candidate_file(
    ctx: PhaseContext,
    path: Path,
    phases: RawPhaseCounters,
    *,
    misc_ext: frozenset[str],
    junk_keywords_norm: tuple[str, ...],
    dry_run: bool,
) -> None:
    """删除符合 2.2 规则的单个文件。"""
    if not _should_delete_clean_file(
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
    """删空第一层目录下的空子目录；不在此处删 root 本体。"""
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
    """若第一层目录在清洗后已空则移除（不触碰 inbox）。"""
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


def _clean_level1_dir(
    ctx: PhaseContext,
    root_dir: Path,
    phases: RawPhaseCounters,
    *,
    junk_keywords_norm: tuple[str, ...],
    dry_run: bool,
    cancellation_event: threading.Event | None,
) -> bool:
    """阶段 2.2：遍历目录删除垃圾文件与空子目录；返回 True 表示已请求取消。"""
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
    except FileNotFoundError, NotADirectoryError:
        pass

    return False


def _classification_placeholder(
    ctx: PhaseContext,
    dir_path: Path,
    phases: RawPhaseCounters,
) -> None:
    """阶段 2.3：分类策略占位 — 打点 + 日志；目录仍保留于 inbox。"""
    phases.phase2_deferred_classification_dirs += 1
    logger.bind(
        run_id=str(ctx.run_id),
        run_name=ctx.run_name,
        level="RAW_PHASE",
        phase=2,
        subphase="classify_deferred",
        dir=str(dir_path),
    ).info("阶段2.3（占位）：第一层目录保留，后续分类逻辑待补充")


def run_phase2(
    ctx: PhaseContext,
    phases: RawPhaseCounters,
    *,
    dry_run: bool,
    cancellation_event: threading.Event | None,
) -> bool:
    """阶段 2：第一层目录 — 迁出 / 清洗 / 分类占位；返回 True 表示已请求取消。"""
    if cancellation_event and cancellation_event.is_set():
        logger.bind(
            run_id=str(ctx.run_id),
            run_name=ctx.run_name,
        ).info("任务已被取消（阶段2 前）")
        return True

    dirs = _list_inbox_level1_dirs(ctx.scan_root)
    phases.phase2_seen_dirs = len(dirs)

    dir_keywords_norm = normalize_keyword_tokens(
        DEFAULT_RAW_DIR_TO_DELETE_KEYWORDS,
    )
    junk_keywords_norm = normalize_keyword_tokens(
        DEFAULT_PROBABLE_JUNK_MEDIA_KEYWORDS,
    )

    needs_delete_dest = any(
        dir_name_matches(dir_path, dir_keywords_norm) for dir_path in dirs
    )
    dest_delete = ctx.analyze_config.folders_to_delete
    if needs_delete_dest and dest_delete is None:
        raise ValueError("folders_to_delete 未设置（存在待迁出的关键字目录）")

    logger.bind(
        run_id=str(ctx.run_id),
        run_name=ctx.run_name,
        level="RAW_PHASE",
        phase=2,
    ).info(f"阶段2：处理 inbox 第一层目录 {len(dirs)} 个")

    for dir_path in dirs:
        if cancellation_event and cancellation_event.is_set():
            logger.bind(
                run_id=str(ctx.run_id),
                run_name=ctx.run_name,
            ).info("任务已被取消（阶段2）")
            return True

        if dir_name_matches(dir_path, dir_keywords_norm):
            if dest_delete is None:
                msg = "folders_to_delete 未设置"
                raise ValueError(msg)
            _move_dir_to_delete(
                ctx,
                dir_path,
                phases,
                dest_delete=dest_delete,
                dry_run=dry_run,
            )
            continue

        cancelled_inside = _clean_level1_dir(
            ctx,
            dir_path,
            phases,
            junk_keywords_norm=junk_keywords_norm,
            dry_run=dry_run,
            cancellation_event=cancellation_event,
        )
        if cancelled_inside:
            logger.bind(
                run_id=str(ctx.run_id),
                run_name=ctx.run_name,
            ).info("任务已被取消（阶段2 清洗循环内）")
            return True

        if not dir_path.exists():
            phases.phase2_removed_dirs += 1
            continue

        _classification_placeholder(ctx, dir_path, phases)

    return False
