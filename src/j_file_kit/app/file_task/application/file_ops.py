"""文件任务工具函数

提供文件任务domain专用的工具函数，如文件类型判断、路径冲突处理、目录扫描等。
这些函数是文件domain的业务逻辑，不属于通用工具。

设计意图：
- generate_alternative_filename：生成 -jfk-xxxx 格式的候选文件名
- move_file_with_conflict_resolution / move_directory_with_conflict_resolution：移动文件或目录并处理路径冲突（复用同一套候选名规则）
- truncate_utf8_to_max_bytes / normalize_move_basename：文件名 UTF-8 字节上限与冲突后缀预留
- scan_directory_items：自底向上扫描目录，用于文件任务处理流程
"""

import os
import re
import string
from collections.abc import Generator
from pathlib import Path
from random import choices as random_choices

from j_file_kit.app.file_task.domain.file_types import PathEntryType

# 与常见文件系统文件名上限一致（ext4 / APFS 等）
MAX_FILENAME_BYTES = 255
# `generate_alternative_filename` 在 stem 与扩展名之间插入的 ASCII 后缀长度（`-jfk-xxxx`）
JFK_CONFLICT_STEM_SUFFIX_BYTES = len(b"-jfk-xxxx")


def truncate_utf8_to_max_bytes(text: str, max_bytes: int) -> str:
    """将字符串截断到 UTF-8 编码长度不超过 max_bytes（在完整码点边界截断）。"""
    if max_bytes <= 0:
        return ""
    encoded = text.encode()
    if len(encoded) <= max_bytes:
        return text
    return encoded[:max_bytes].decode(errors="ignore")


def normalize_move_basename(
    filename: str,
    *,
    max_filename_bytes: int = MAX_FILENAME_BYTES,
    reserve_conflict_suffix_bytes: int = JFK_CONFLICT_STEM_SUFFIX_BYTES,
) -> str:
    """将「仅文件名」规范化到文件系统上限内，并为 `-jfk-xxxx` 冲突后缀预留 stem 空间。

    `move_file_with_conflict_resolution` 在冲突时会在 stem 与扩展名之间插入 ASCII 后缀；
    若初始目标名已占满 255 字节，冲突重试会导致超长文件名。因此在裁剪时默认预留后缀字节。

    Args:
        filename: 原始文件名（可含扩展名），应为 basename 而非完整路径。
        max_filename_bytes: 允许的文件名最大 UTF-8 字节数。
        reserve_conflict_suffix_bytes: 为冲突消解预留的字节数（默认匹配 `-jfk-xxxx`）。
    """
    if not filename:
        return filename
    path = Path(filename)
    ext_part = path.suffix
    stem = path.stem if ext_part else path.name
    ext_len = len(ext_part.encode())
    budget_stem = max_filename_bytes - reserve_conflict_suffix_bytes - ext_len
    if budget_stem <= 0:
        stem_trunc = truncate_utf8_to_max_bytes(
            path.name,
            max_filename_bytes - reserve_conflict_suffix_bytes,
        )
        if ext_part and not stem_trunc:
            stem_trunc = "_"
        out = f"{stem_trunc}{ext_part}" if ext_part else stem_trunc
        cap = max_filename_bytes - reserve_conflict_suffix_bytes
        if len(out.encode()) > cap:
            return truncate_utf8_to_max_bytes(out, cap)
        return out
    stem_trunc = truncate_utf8_to_max_bytes(stem, budget_stem)
    if not stem_trunc:
        stem_trunc = "_"
    return f"{stem_trunc}{ext_part}"


def generate_alternative_filename(target_path: Path) -> Path:
    """生成候选文件名路径，用于处理文件移动时的路径冲突

    如果输入路径已带 `-jfk-xxxx` 后缀，会提取原始文件名并基于原始文件名生成新候选文件名。
    始终基于原始文件名生成，避免文件名越来越长。
    目录部分保持不变，仅修改文件名部分。
    这是纯函数，不执行任何 I/O 操作。

    Args:
        target_path: 目标路径（可能已带 `-jfk-xxxx` 后缀）

    Returns:
        新的候选路径，格式为 `{原始stem}-jfk-{4个随机字符}{suffix}`（目录保持不变）

    Examples:
        >>> generate_alternative_filename(Path("test.mp4"))
        Path("test-jfk-a3b2.mp4")

        >>> generate_alternative_filename(Path("test-jfk-a3b2.mp4"))
        Path("test-jfk-xyz1.mp4")  # 基于原始文件名 test.mp4 生成

        >>> generate_alternative_filename(Path(".hidden"))
        Path(".hidden-jfk-a3b2")  # 空 stem 时使用完整文件名
    """
    stem = target_path.stem
    suffix = target_path.suffix
    parent = target_path.parent

    # 处理空 stem 的情况（如 .hidden 文件或只有扩展名的文件）
    # 如果 stem 为空，使用完整文件名作为基础进行匹配
    base_name = stem if stem else target_path.name

    # 尝试提取原始路径（如果已带 -jfk-xxxx 后缀）
    pattern = r"^(.+)-jfk-[a-z0-9]{4}$"
    match = re.match(pattern, base_name)
    if match:
        original_stem = match.group(1)
    else:
        original_stem = base_name

    # 生成新的候选路径
    chars = string.ascii_lowercase + string.digits
    # 非安全随机即可满足“文件名冲突消解”，不涉及密钥/令牌
    random_suffix = "-jfk-" + "".join(random_choices(chars, k=4))  # noqa: S311
    new_name = f"{original_stem}{random_suffix}{suffix}"
    return parent / new_name


def move_path_with_conflict_resolution(source: Path, target: Path) -> Path:
    """在同卷上移动任意路径条目（常规文件或目录），目标已存在则用 `-jfk-xxxx` 重试 basename。

    与 `generate_alternative_filename` 的规则一致：`move_file_with_conflict_resolution` 与本函数
    共享实现，便于 Raw 等环节整目录迁入归宿时复用同一种冲突消解语义。

    Raises:
        FileExistsError / OSError：源不存在或 `rename` 失败时由系统抛出。
    """
    original_target = target
    current_target = target
    max_attempts = 10

    for attempt in range(max_attempts):
        if current_target.exists():
            if attempt == max_attempts - 1:
                raise RuntimeError(
                    f"无法为 {original_target} 生成唯一路径，已尝试 {max_attempts} 次",
                ) from None
            current_target = generate_alternative_filename(original_target)
            continue

        try:
            source.rename(current_target)
            return current_target
        except OSError:
            raise

    raise RuntimeError(
        f"无法为 {original_target} 生成唯一路径，已尝试 {max_attempts} 次",
    )


def move_file_with_conflict_resolution(source: Path, target: Path) -> Path:
    """移动文件，自动处理路径冲突（实现见 `move_path_with_conflict_resolution`）。"""
    return move_path_with_conflict_resolution(source, target)


def move_directory_with_conflict_resolution(source: Path, target: Path) -> Path:
    """整目录移动；`-jfk-xxxx` basename 消解与 `move_file_with_conflict_resolution` 一致。"""
    if not source.is_dir():
        msg = f"源路径不是目录: {source}"
        raise NotADirectoryError(msg)
    return move_path_with_conflict_resolution(source, target)


def scan_directory_items(root: Path) -> Generator[tuple[Path, PathEntryType]]:
    """扫描目录下的所有文件和目录（自底向上遍历）

    自底向上遍历确保子目录先于父目录被处理，这样当子目录被删除后，
    父目录可能变为空目录，可以在后续遍历中被清理。
    先返回文件再返回目录，确保同一目录下的文件先处理，文件移动后目录可能变空。

    Args:
        root: 根目录路径

    Yields:
        (路径, 路径项类型) 元组

    Raises:
        FileNotFoundError: 目录不存在
        NotADirectoryError: 路径不是目录
    """
    if not root.exists():
        raise FileNotFoundError(f"扫描目录不存在: {root}")

    if not root.is_dir():
        raise NotADirectoryError(f"路径不是目录: {root}")

    # 使用 os.walk 实现自底向上遍历（topdown=False）
    for dirpath, _dirnames, filenames in os.walk(root, topdown=False):
        dir_path = Path(dirpath)

        # 先 yield 所有文件
        for filename in filenames:
            file_path = dir_path / filename
            yield (file_path, PathEntryType.FILE)

        # 再 yield 当前目录
        yield (dir_path, PathEntryType.DIRECTORY)
