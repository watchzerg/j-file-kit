"""phase2_collapse：单链合并名预算等纯逻辑单元测试。"""

import pytest

from j_file_kit.app.file_task.application.file_ops import MAX_FILENAME_BYTES
from j_file_kit.app.file_task.application.raw_pipeline.phase2_collapse import (
    merge_chain_segments_to_basename,
)

pytestmark = pytest.mark.unit


def test_merge_chain_segments_joins_when_under_byte_limit() -> None:
    segments = ["a", "b", "c"]
    assert merge_chain_segments_to_basename(segments) == "a_b_c"


def test_merge_chain_segments_none_when_only_short_segments_and_over_limit() -> None:
    """全部为短段且总超长时，长段列表为空，算法放弃折叠。"""
    many = ["x"] * 300
    raw = "_".join(many)
    assert len(raw.encode()) > MAX_FILENAME_BYTES
    assert merge_chain_segments_to_basename(many) is None
