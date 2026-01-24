from pathlib import Path

import pytest

from j_file_kit.app.file_task.application import file_ops
from j_file_kit.app.file_task.domain.models import PathEntryType

pytestmark = pytest.mark.unit


def test_generate_alternative_filename_uses_original_stem(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        file_ops,
        "random_choices",
        lambda *_args, **_kwargs: ["a", "1", "b", "2"],
    )

    original = tmp_path / "sample.mp4"
    alternative = file_ops.generate_alternative_filename(original)

    assert alternative.parent == original.parent
    assert alternative.name == "sample-jfk-a1b2.mp4"


def test_generate_alternative_filename_strips_existing_suffix(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        file_ops,
        "random_choices",
        lambda *_args, **_kwargs: ["z", "9", "y", "0"],
    )

    original = tmp_path / "sample-jfk-a1b2.mp4"
    alternative = file_ops.generate_alternative_filename(original)

    assert alternative.name == "sample-jfk-z9y0.mp4"


def test_generate_alternative_filename_handles_hidden_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        file_ops,
        "random_choices",
        lambda *_args, **_kwargs: ["x", "1", "y", "2"],
    )

    original = tmp_path / ".hidden"
    alternative = file_ops.generate_alternative_filename(original)

    assert alternative.name == ".hidden-jfk-x1y2"


def test_move_file_with_conflict_resolution_retries_on_conflict(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.mp4"
    target = tmp_path / "target.mp4"
    alternative = tmp_path / "target-jfk-a1b2.mp4"
    calls: list[Path] = []

    def _rename_stub(self: Path, new_target: Path) -> Path:
        calls.append(new_target)
        if new_target == target:
            raise FileExistsError
        return new_target

    monkeypatch.setattr(
        file_ops,
        "generate_alternative_filename",
        lambda *_args, **_kwargs: alternative,
    )
    monkeypatch.setattr(Path, "rename", _rename_stub)

    result = file_ops.move_file_with_conflict_resolution(source, target)

    assert result == alternative
    assert calls == [target, alternative]


def test_scan_directory_items_returns_files_before_dir(tmp_path: Path) -> None:
    root = tmp_path / "root"
    nested = root / "nested"
    nested.mkdir(parents=True)
    file_path = nested / "file.txt"
    file_path.write_text("content")

    items = list(file_ops.scan_directory_items(root))
    file_index = items.index((file_path, PathEntryType.FILE))
    dir_index = items.index((nested, PathEntryType.DIRECTORY))

    assert file_index < dir_index


def test_scan_directory_items_raises_for_missing_root(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        list(file_ops.scan_directory_items(tmp_path / "missing"))


def test_scan_directory_items_raises_for_non_directory(tmp_path: Path) -> None:
    file_path = tmp_path / "file.txt"
    file_path.write_text("content")

    with pytest.raises(NotADirectoryError):
        list(file_ops.scan_directory_items(file_path))
