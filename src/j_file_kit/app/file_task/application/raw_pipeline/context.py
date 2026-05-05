"""Raw 管道阶段共享上下文。

各 phase 函数仅需一次注入 run 标识与仓储，避免参数列表膨胀。
放在独立模块而非 `pipeline.py`，防止 pipeline 与 phase 子模块的导入环。
"""

from dataclasses import dataclass
from pathlib import Path

from j_file_kit.app.file_task.application.config import RawAnalyzeConfig
from j_file_kit.app.file_task.domain.ports import FileResultRepository


@dataclass(frozen=True, slots=True)
class PhaseContext:
    """一次 Raw 管道 run 在三个阶段间共享的注入项（非领域模型，仅减少函数参数面）。"""

    run_id: int
    run_name: str
    scan_root: Path
    analyze_config: RawAnalyzeConfig
    file_result_repository: FileResultRepository
