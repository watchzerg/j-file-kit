"""跨模块共享的工具函数。"""

from pathlib import Path

from fastapi import HTTPException, status

from j_file_kit.app.file_task.domain.task_run import FileTaskRun


def _parse_run_id(run_id_str: str) -> int:
    """解析执行实例ID字符串为整数。

    Raises:
        HTTPException: 如果 run_id 格式无效
    """
    try:
        return int(run_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的执行实例ID格式: {run_id_str}",
        ) from None


def _task_log_file_path(log_dir: Path, run: FileTaskRun) -> Path:
    return log_dir / f"{run.run_name}_{run.run_id}.jsonl"
