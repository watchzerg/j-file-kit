import pytest

from j_file_kit.app.global_config.domain.models import (
    create_default_global_config,
)

pytestmark = pytest.mark.unit


def test_create_default_global_config_has_none_fields() -> None:
    global_config = create_default_global_config()

    assert global_config.inbox_dir is None
    assert global_config.sorted_dir is None
    assert global_config.unsorted_dir is None
    assert global_config.archive_dir is None
    assert global_config.misc_dir is None
    assert global_config.starred_dir is None
