"""Raw 管道阶段 3：`files_misc` 第一层计数占位。

分流规则尚未实现；先统计第一层文件数以支撑后续迭代与观测。见 `docs/RAW_FILE_PROCESSING_PIPELINE.md`。
"""

from loguru import logger

from j_file_kit.app.file_task.application.raw_pipeline.context import PhaseContext
from j_file_kit.app.file_task.application.raw_pipeline.counters import RawPhaseCounters


def run_phase3(ctx: PhaseContext, counters: RawPhaseCounters) -> None:
    """阶段 3 占位：统计 `files_misc` 第一层文件数，分流规则后续迭代。"""
    misc = ctx.analyze_config.files_misc
    if misc is None or not misc.exists() or not misc.is_dir():
        counters.phase3_seen_files_misc = 0
        counters.phase3_deferred_files_misc = 0
        logger.bind(
            run_id=str(ctx.run_id),
            run_name=ctx.run_name,
            level="RAW_PHASE",
            phase=3,
        ).info("阶段3（占位）：files_misc 不可用或不存在，跳过计数")
        return

    seen = sum(1 for p in misc.iterdir() if p.is_file())
    counters.phase3_seen_files_misc = seen
    counters.phase3_deferred_files_misc = seen

    logger.bind(
        run_id=str(ctx.run_id),
        run_name=ctx.run_name,
        level="RAW_PHASE",
        phase=3,
    ).info(
        f"阶段3（占位）：files_misc 第一层文件 {seen} 个，暂未分流到 files_*",
    )
