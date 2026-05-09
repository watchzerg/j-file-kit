"""Raw 管道阶段 2 编排入口：inbox 第一层目录（2.1→2.2→2.3→2.4）。

具体规则实现在同包 ``phase2_*`` 子模块；本文件仅负责取消检测、目录循环与阶段顺序。
归宿路径由 workspace 派生；关键字目录迁至 ``folders_to_delete``。
"""

import threading
from pathlib import Path

from loguru import logger

from j_file_kit.app.file_task.application.raw_pipeline.context import PhaseContext
from j_file_kit.app.file_task.application.raw_pipeline.counters import RawPhaseCounters
from j_file_kit.app.file_task.application.raw_pipeline.phase2_classify import (
    run_phase2_classify,
)
from j_file_kit.app.file_task.application.raw_pipeline.phase2_clean import (
    clean_level1_dir,
)
from j_file_kit.app.file_task.application.raw_pipeline.phase2_collapse import (
    collapse_level1_single_chain,
)
from j_file_kit.app.file_task.application.raw_pipeline.phase2_delete_move import (
    move_dir_to_delete,
)
from j_file_kit.app.file_task.application.raw_pipeline.phase2_preflight import (
    build_phase2_normalized_keywords,
    list_inbox_level1_dirs,
    validate_phase2_preflight_paths,
)
from j_file_kit.shared.utils.name_keyword_match import dir_name_matches


def _phase2_process_one_level1_dir(
    ctx: PhaseContext,
    dir_path: Path,
    phases: RawPhaseCounters,
    *,
    dir_keywords_norm: tuple[str, ...],
    junk_keywords_norm: tuple[str, ...],
    dest_delete: Path,
    dry_run: bool,
    cancellation_event: threading.Event | None,
) -> bool:
    """处理 inbox 下单个第一层目录（2.1 / 2.2 / 2.3 / 2.4）。

    Returns:
        ``True`` 表示应终止阶段 2（取消）。
    """
    if dir_name_matches(dir_path, dir_keywords_norm):
        move_dir_to_delete(
            ctx,
            dir_path,
            phases,
            dest_delete=dest_delete,
            dry_run=dry_run,
        )
        return False

    cancelled_inside = clean_level1_dir(
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
        return False

    dir_for_classify, cancelled_collapse = collapse_level1_single_chain(
        ctx,
        dir_path,
        phases,
        scan_root=ctx.scan_root,
        dry_run=dry_run,
        cancellation_event=cancellation_event,
    )
    if cancelled_collapse:
        return True

    if not dir_for_classify.exists():
        phases.phase2_removed_dirs += 1
        return False

    cancelled_classify = run_phase2_classify(
        ctx,
        dir_for_classify,
        phases,
        dry_run=dry_run,
        cancellation_event=cancellation_event,
    )
    return bool(cancelled_classify)


def run_phase2(
    ctx: PhaseContext,
    phases: RawPhaseCounters,
    *,
    dry_run: bool,
    cancellation_event: threading.Event | None,
) -> bool:
    """阶段 2：第一层目录 — 迁出 / 清洗 / 单链折叠 / 分类；返回 True 表示已请求取消。"""
    if cancellation_event and cancellation_event.is_set():
        logger.bind(
            run_id=str(ctx.run_id),
            run_name=ctx.run_name,
        ).info("任务已被取消（阶段2 前）")
        return True

    dirs = list_inbox_level1_dirs(ctx.scan_root)
    phases.phase2_seen_dirs = len(dirs)

    dir_keywords_norm, junk_keywords_norm = build_phase2_normalized_keywords()
    dest_delete = validate_phase2_preflight_paths(
        dirs,
        ctx.analyze_config,
        dir_keywords_norm=dir_keywords_norm,
    )

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

        stop = _phase2_process_one_level1_dir(
            ctx,
            dir_path,
            phases,
            dir_keywords_norm=dir_keywords_norm,
            junk_keywords_norm=junk_keywords_norm,
            dest_delete=dest_delete,
            dry_run=dry_run,
            cancellation_event=cancellation_event,
        )
        if stop:
            return True

    return False
