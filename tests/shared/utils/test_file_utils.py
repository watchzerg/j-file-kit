from pathlib import Path

import pytest

from j_file_kit.shared.utils.file_utils import (
    delete_directory_if_empty,
    delete_file_if_exists,
    ensure_directory,
    sanitize_surrogate_str,
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


class TestSanitizeSurrogateStr:
    """sanitize_surrogate_str 单元测试"""

    def test_clean_utf8_string_unchanged(self) -> None:
        assert sanitize_surrogate_str("hello.jpg") == "hello.jpg"

    def test_surrogate_bytes_replaced_with_replacement_char(self) -> None:
        # \udcfe 代表原始字节 0xFE，无法以 UTF-8 解码，应替换为 \ufffd
        result = sanitize_surrogate_str("file\udcfe\udca6.jpg")
        assert "\udcfe" not in result
        assert "\udca6" not in result
        # 不可解码字节被替换为 U+FFFD
        assert "\ufffd" in result
        assert result.endswith(".jpg")

    def test_result_is_encodable_as_utf8(self) -> None:
        s = "+\udcfe\udca6+\udccb+\udca5.jpg"
        result = sanitize_surrogate_str(s)
        # 不再抛出 UnicodeEncodeError
        encoded = result.encode("utf-8")
        assert len(encoded) > 0

    def test_mixed_ascii_and_surrogates(self) -> None:
        result = sanitize_surrogate_str("ABC-123\udcfe.mp4")
        assert result.startswith("ABC-123")
        assert result.endswith(".mp4")
