import pytest
from pydantic import BaseModel

from j_file_kit.app.task_config.domain.models import TaskConfig

pytestmark = pytest.mark.unit


class _DummyConfig(BaseModel):
    enabled: bool


def test_task_config_get_config_returns_typed_model() -> None:
    task_config = TaskConfig(
        type="file_organize",
        enabled=True,
        config={"enabled": True},
    )

    parsed: _DummyConfig = task_config.get_config(_DummyConfig)

    assert isinstance(parsed, _DummyConfig)
    assert parsed.enabled is True
