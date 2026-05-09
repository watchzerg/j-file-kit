"""raw_pipeline 测试共享 fixtures。

集中封装 RawFilePipeline 与 phase3 context 的构造，减少场景样板代码。
"""

from collections.abc import Callable
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from j_file_kit.app.file_task.application.raw_analyze_config import RawAnalyzeConfig
from j_file_kit.app.file_task.application.raw_pipeline.context import PhaseContext
from j_file_kit.app.file_task.application.raw_pipeline.pipeline import RawFilePipeline
from j_file_kit.infrastructure.persistence.sqlite.file_task.file_result_repository import (
    FileResultRepositoryImpl,
)


@pytest.fixture
def phase_context_factory(tmp_path: Path) -> Callable[[RawAnalyzeConfig], PhaseContext]:
    """构造 phase 级执行上下文。"""

    def _create(config: RawAnalyzeConfig) -> PhaseContext:
        return PhaseContext(
            run_id=1,
            run_name="raw_file_organizer",
            scan_root=tmp_path / "inbox",
            analyze_config=config,
            file_result_repository=MagicMock(),
        )

    return _create


@pytest.fixture
def raw_pipeline_factory(
    tmp_path: Path,
    file_result_repository: FileResultRepositoryImpl,
    raw_analyze_config_factory: Callable[..., RawAnalyzeConfig],
) -> Callable[..., RawFilePipeline]:
    """构造 RawFilePipeline 并初始化常用目录。"""

    def _create(run_id: int = 1) -> RawFilePipeline:
        inbox = tmp_path / "inbox"
        files_misc = tmp_path / "files_misc"
        folders_to_delete = tmp_path / "folders_to_delete"
        inbox.mkdir(parents=True, exist_ok=True)
        files_misc.mkdir(parents=True, exist_ok=True)
        folders_to_delete.mkdir(parents=True, exist_ok=True)
        config = raw_analyze_config_factory(
            tmp_path,
            files_misc=files_misc,
            folders_to_delete=folders_to_delete,
        )
        return RawFilePipeline(
            run_id=run_id,
            run_name="raw_file_organizer",
            scan_root=inbox,
            analyze_config=config,
            log_dir=tmp_path / "logs",
            file_result_repository=file_result_repository,
        )

    return _create
