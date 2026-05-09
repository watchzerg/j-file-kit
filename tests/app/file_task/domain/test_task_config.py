"""TaskConfig 领域模型测试。"""

from pathlib import Path

import pytest
from pydantic import BaseModel

from j_file_kit.app.file_task.domain.task_config import TaskConfig

pytestmark = pytest.mark.unit


class _SampleConfig(BaseModel):
    workspace_root: Path


def test_get_config_returns_typed_model(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    config = TaskConfig(
        type="sample_task",
        enabled=True,
        config={"workspace_root": str(workspace_root)},
    )
    result = config.get_config(_SampleConfig)
    assert isinstance(result, _SampleConfig)
    assert result.workspace_root == workspace_root
