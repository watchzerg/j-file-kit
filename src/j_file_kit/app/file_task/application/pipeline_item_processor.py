"""`FilePipeline` 单文件处理闭环：分析 → 执行 → 映射 → 落库 → 观测更新。"""

import time
from pathlib import Path

from j_file_kit.app.file_task.application.executor import execute_decision
from j_file_kit.app.file_task.application.jav_analysis.runner import analyze_jav_file
from j_file_kit.app.file_task.application.jav_analyze_config import JavAnalyzeConfig
from j_file_kit.app.file_task.application.pipeline_observer import (
    PipelineRunCounters,
    log_file_processing_error,
    log_item_result,
)
from j_file_kit.app.file_task.application.pipeline_result_mapper import (
    build_file_item_data,
)
from j_file_kit.app.file_task.domain.decisions import FileItemData
from j_file_kit.app.file_task.domain.ports import FileResultRepository


def process_single_file_for_run(
    path: Path,
    dry_run: bool,
    *,
    run_id: int,
    run_name: str,
    analyze_config: JavAnalyzeConfig,
    file_result_repository: FileResultRepository,
    counters: PipelineRunCounters,
) -> None:
    """对单个路径执行 JAV 分析与执行，并写入结果。

    任一环节抛错：写 `decision_type=error` 的 `FileItemData`，更新内存 error 计数，不中断整轮扫描。
    """
    start_time = time.time()

    try:
        decision = analyze_jav_file(path, analyze_config)
        result = execute_decision(
            decision,
            dry_run=dry_run,
        )
        duration_ms = (time.time() - start_time) * 1000

        item_data = build_file_item_data(path, decision, result, duration_ms)
        file_result_repository.save_result(run_id, item_data)
        counters.apply_execution_result(result, duration_ms)
        log_item_result(run_id, run_name, path, decision, result, duration_ms)

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        log_file_processing_error(run_id, run_name, path, e)

        error_data = FileItemData(
            path=path,
            stem=path.stem,
            file_type=None,
            serial_id=None,
            decision_type="error",
            target_path=None,
            success=False,
            error_message=str(e),
            duration_ms=duration_ms,
        )
        file_result_repository.save_result(run_id, error_data)
        counters.record_file_processing_exception(duration_ms)
