"""文件操作工具单元测试

覆盖 generate_alternative_filename、move_file_with_conflict_resolution、scan_directory_items。
"""

import re
from pathlib import Path

import pytest

from j_file_kit.app.file_task.application.file_ops import (
    generate_alternative_filename,
    move_file_with_conflict_resolution,
    scan_directory_items,
)
from j_file_kit.app.file_task.domain.models import PathEntryType

pytestmark = pytest.mark.unit


class TestGenerateAlternativeFilename:
    """generate_alternative_filename 候选路径生成"""

    def test_output_format(self, tmp_path: Path) -> None:
        target = tmp_path / "test.mp4"
        result = generate_alternative_filename(target)
        assert result.parent == tmp_path
        assert result.suffix == ".mp4"
        assert re.match(r"^test-jfk-[a-z0-9]{4}\.mp4$", result.name)

    def test_already_has_jfk_suffix_uses_original_stem(self, tmp_path: Path) -> None:
        target = tmp_path / "test-jfk-ab12.mp4"
        result = generate_alternative_filename(target)
        assert re.match(r"^test-jfk-[a-z0-9]{4}\.mp4$", result.name)
        assert result.name != "test-jfk-ab12.mp4"

    def test_empty_stem_uses_full_name(self, tmp_path: Path) -> None:
        target = tmp_path / ".hidden"
        result = generate_alternative_filename(target)
        assert re.match(r"^\.hidden-jfk-[a-z0-9]{4}$", result.name)

    def test_parent_preserved(self, tmp_path: Path) -> None:
        target = tmp_path / "sub" / "file.txt"
        result = generate_alternative_filename(target)
        assert result.parent == tmp_path / "sub"


class TestMoveFileWithConflictResolution:
    """move_file_with_conflict_resolution 移动与冲突消解"""

    def test_simple_move(self, tmp_path: Path) -> None:
        source = tmp_path / "a.txt"
        source.write_text("content")
        target = tmp_path / "b.txt"
        result = move_file_with_conflict_resolution(source, target)
        assert result == target
        assert target.exists()
        assert not source.exists()

    def test_conflict_resolution(self, tmp_path: Path) -> None:
        source = tmp_path / "a.txt"
        source.write_text("content")
        target = tmp_path / "b.txt"
        target.write_text("existing")
        result = move_file_with_conflict_resolution(source, target)
        assert result.exists()
        assert result.read_text() == "content"
        assert not source.exists()
        assert result.parent == tmp_path
        assert result.suffix == ".txt"

    def test_source_not_found_raises(self, tmp_path: Path) -> None:
        source = tmp_path / "missing.txt"
        target = tmp_path / "b.txt"
        with pytest.raises(FileNotFoundError):
            move_file_with_conflict_resolution(source, target)


class TestScanDirectoryItems:
    """scan_directory_items 目录扫描"""

    def test_bottom_up_order(self, tmp_path: Path) -> None:
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "file.txt").write_text("x")
        (tmp_path / "root.txt").write_text("x")
        items = list(scan_directory_items(tmp_path))
        file_paths = [p for p, t in items if t == PathEntryType.FILE]
        dir_paths = [p for p, t in items if t == PathEntryType.DIRECTORY]
        assert tmp_path / "sub" / "file.txt" in file_paths
        assert tmp_path / "root.txt" in file_paths
        assert tmp_path / "sub" in dir_paths
        assert tmp_path in dir_paths
        sub_idx = dir_paths.index(tmp_path / "sub")
        root_idx = dir_paths.index(tmp_path)
        assert sub_idx < root_idx

    def test_nonexistent_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="扫描目录不存在"):
            list(scan_directory_items(tmp_path / "missing"))

    def test_not_directory_raises(self, tmp_path: Path) -> None:
        (tmp_path / "file.txt").write_text("x")
        with pytest.raises(NotADirectoryError, match="路径不是目录"):
            list(scan_directory_items(tmp_path / "file.txt"))
