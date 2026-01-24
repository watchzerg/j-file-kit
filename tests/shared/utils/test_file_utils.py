from pathlib import Path

import pytest

from j_file_kit.shared.utils.file_utils import (
    delete_directory_if_empty,
    delete_file_if_exists,
    ensure_directory,
)

pytestmark = pytest.mark.unit


def test_delete_file_if_exists_removes_file(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.txt"
    file_path.write_text("content")

    delete_file_if_exists(file_path)

    assert not file_path.exists()


def test_delete_file_if_exists_missing_file_is_noop(tmp_path: Path) -> None:
    file_path = tmp_path / "missing.txt"

    delete_file_if_exists(file_path)

    assert not file_path.exists()


def test_ensure_directory_creates_missing_directory(tmp_path: Path) -> None:
    target_dir = tmp_path / "nested" / "dir"

    ensure_directory(target_dir)

    assert target_dir.is_dir()


def test_ensure_directory_noop_when_directory_exists(tmp_path: Path) -> None:
    target_dir = tmp_path / "existing"
    target_dir.mkdir()

    ensure_directory(target_dir)

    assert target_dir.is_dir()


def test_ensure_directory_raises_when_path_is_file(tmp_path: Path) -> None:
    target_path = tmp_path / "not-a-dir"
    target_path.write_text("content")

    with pytest.raises(FileExistsError):
        ensure_directory(target_path)


def test_delete_directory_if_empty_removes_empty_dir(tmp_path: Path) -> None:
    target_dir = tmp_path / "empty"
    target_dir.mkdir()

    deleted = delete_directory_if_empty(target_dir)

    assert deleted is True
    assert not target_dir.exists()


def test_delete_directory_if_empty_skips_non_empty_dir(tmp_path: Path) -> None:
    target_dir = tmp_path / "non-empty"
    target_dir.mkdir()
    (target_dir / "file.txt").write_text("content")

    deleted = delete_directory_if_empty(target_dir)

    assert deleted is False
    assert target_dir.exists()


def test_delete_directory_if_empty_skips_non_dir_path(tmp_path: Path) -> None:
    target_path = tmp_path / "file.txt"
    target_path.write_text("content")

    deleted = delete_directory_if_empty(target_path)

    assert deleted is False
