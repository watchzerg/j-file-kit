"""文件任务工具函数

提供文件任务domain专用的工具函数，如文件类型判断、路径冲突处理、目录扫描等。
这些函数是文件domain的业务逻辑，不属于通用工具。

设计意图：
- generate_alternative_filename：生成 -jfk-xxxx 格式的候选文件名
- move_file_with_conflict_resolution：移动文件并自动处理路径冲突
- scan_directory_items：自底向上扫描目录，用于文件任务处理流程
"""

import os
import re
import string
from collections.abc import Generator
from pathlib import Path
from random import choices as random_choices

from j_file_kit.app.file_task.domain.models import PathEntryType


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


def move_file_with_conflict_resolution(source: Path, target: Path) -> Path:
    """移动文件，自动处理路径冲突

    先尝试直接移动，如果目标路径已存在，自动生成唯一路径并重试。
    生成的路径使用 `-jfk-xxxx` 格式后缀（file_task domain 的业务约定）。
    最多重试 10 次，超过后抛出异常。

    设计意图：
    - 使用 -jfk- 后缀是 file_task domain 的业务逻辑
    - 始终基于原始目标路径生成候选路径，避免文件名越来越长

    Args:
        source: 源文件路径
        target: 目标文件路径（可能已存在）

    Returns:
        实际移动到的目标路径（可能与输入的 target 不同）

    Raises:
        FileNotFoundError: 源文件不存在
        RuntimeError: 重试 10 次后仍无法找到唯一路径
        OSError: 其他移动操作失败
    """
    original_target = target
    current_target = target
    max_attempts = 10

    for attempt in range(max_attempts):
        try:
            source.rename(current_target)
            return current_target
        except FileExistsError:
            if attempt == max_attempts - 1:
                raise RuntimeError(
                    f"无法为 {original_target} 生成唯一路径，已尝试 {max_attempts} 次",
                ) from None
            current_target = generate_alternative_filename(original_target)
        except OSError:
            raise

    # 理论上不会执行到这里，但为了满足类型检查
    raise RuntimeError(
        f"无法为 {original_target} 生成唯一路径，已尝试 {max_attempts} 次",
    )


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
