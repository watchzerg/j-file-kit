"""Raw 阶段 2.1：关键字匹配的第一层整目录迁出到 ``folders_to_delete``。"""

from pathlib import Path

from loguru import logger

from j_file_kit.app.file_task.application.file_ops import (
    move_directory_with_conflict_resolution,
)
from j_file_kit.app.file_task.application.raw_pipeline.context import PhaseContext
from j_file_kit.app.file_task.application.raw_pipeline.counters import RawPhaseCounters
from j_file_kit.shared.utils.file_utils import ensure_directory, sanitize_surrogate_str


def move_dir_to_delete(
    ctx: PhaseContext,
    dir_path: Path,
    phases: RawPhaseCounters,
    *,
    dest_delete: Path,
    dry_run: bool,
) -> None:
    """整目录迁入 ``folders_to_delete``（目录级 ``-jfk-xxxx`` 冲突消解）。"""
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
