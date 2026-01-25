from pathlib import Path

import pytest

from j_file_kit.app.file_task.application import executor
from j_file_kit.app.file_task.domain.decisions import (
    DeleteDecision,
    MoveDecision,
    SkipDecision,
)
from j_file_kit.app.file_task.domain.models import FileType, SerialId

pytestmark = pytest.mark.unit


def test_execute_decision_dry_run_returns_preview(tmp_path: Path) -> None:
    decision = MoveDecision(
        source_path=tmp_path / "source.mp4",
        target_path=tmp_path / "target.mp4",
        file_type=FileType.VIDEO,
        serial_id=SerialId(prefix="AB", number="12"),
    )

    result = executor.execute_decision(decision, dry_run=True)

    assert result.status == executor.ExecutionStatus.PREVIEW
    assert result.target_path == decision.target_path


def test_execute_decision_skip_returns_skipped(tmp_path: Path) -> None:
    decision = SkipDecision(
        source_path=tmp_path / "source.mp4",
        file_type=FileType.VIDEO,
        reason="skip",
    )

    result = executor.execute_decision(decision, dry_run=False)

    assert result.status == executor.ExecutionStatus.SKIPPED
    assert result.message == "skip"


def test_execute_decision_move_returns_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.mp4"
    target = tmp_path / "target.mp4"
    decision = MoveDecision(
        source_path=source,
        target_path=target,
        file_type=FileType.VIDEO,
        serial_id=None,
    )
    monkeypatch.setattr(executor, "ensure_directory", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        executor,
        "move_file_with_conflict_resolution",
        lambda *_args, **_kwargs: target,
    )

    result = executor.execute_decision(decision, dry_run=False)

    assert result.status == executor.ExecutionStatus.SUCCESS
    assert result.target_path == target


def test_execute_decision_delete_returns_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.tmp"
    decision = DeleteDecision(
        source_path=source,
        file_type=FileType.MISC,
        reason="cleanup",
    )
    monkeypatch.setattr(
        executor,
        "delete_file_if_exists",
        lambda *_args, **_kwargs: None,
    )

    result = executor.execute_decision(decision, dry_run=False)

    assert result.status == executor.ExecutionStatus.SUCCESS
    assert result.source_path == source
