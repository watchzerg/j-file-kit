"""文件系统操作

封装文件系统相关的操作，如文件移动、删除、创建目录等。
所有文件系统I/O操作都通过此模块统一管理，便于测试和未来扩展。
"""

from pathlib import Path

from j_file_kit.utils.file_utils import generate_alternative_filename


def move_file(source: Path, target: Path) -> None:
    """移动文件

    Args:
        source: 源文件路径
        target: 目标文件路径

    Raises:
        FileNotFoundError: 源文件不存在
        OSError: 移动操作失败
    """
    source.rename(target)


def delete_file(path: Path) -> None:
    """删除文件

    静默成功：文件不存在时不抛出异常，其他异常正常抛出。

    Args:
        path: 文件路径

    Raises:
        OSError: 删除操作失败（文件不存在时不会抛出）
    """
    try:
        path.unlink(missing_ok=True)
    except FileNotFoundError:
        pass


def create_directory(path: Path, parents: bool = True) -> None:
    """创建目录

    静默成功：目录已存在时不抛出异常，其他异常正常抛出。

    Args:
        path: 目录路径
        parents: 是否创建父目录

    Raises:
        OSError: 创建目录失败（目录已存在时不会抛出）
    """
    try:
        path.mkdir(parents=parents, exist_ok=True)
    except FileExistsError:
        pass


def write_text_file(path: Path, content: str, encoding: str = "utf-8") -> None:
    """写入文本文件

    Args:
        path: 文件路径
        content: 文件内容
        encoding: 文件编码

    Raises:
        OSError: 写入操作失败
    """
    with open(path, "w", encoding=encoding) as f:
        f.write(content)


def append_text_file(path: Path, content: str, encoding: str = "utf-8") -> None:
    """追加文本到文件

    Args:
        path: 文件路径
        content: 要追加的内容
        encoding: 文件编码

    Raises:
        OSError: 写入操作失败
    """
    with open(path, "a", encoding=encoding) as f:
        f.write(content)


def path_exists(path: Path) -> bool:
    """检查路径是否存在

    Args:
        path: 路径

    Returns:
        路径是否存在
    """
    return path.exists()


def is_directory(path: Path) -> bool:
    """检查路径是否为目录

    Args:
        path: 路径

    Returns:
        是否为目录
    """
    return path.is_dir()


def is_directory_empty(path: Path) -> bool:
    """检查目录是否为空

    判断目录是否为空（无文件和子目录），用于决定是否可以安全删除。
    设计意图：在清理空文件夹时，需要先判断目录是否为空，避免误删非空目录。

    Args:
        path: 目录路径

    Returns:
        目录是否为空。如果目录不存在，返回False。

    Note:
        使用`next(path.iterdir(), None) is None`判断，高效且Pythonic。
    """
    try:
        return next(path.iterdir(), None) is None
    except (OSError, FileNotFoundError):
        # 目录不存在或无法访问时返回False
        return False


def delete_directory(path: Path) -> None:
    """删除目录

    静默成功：目录不存在时不抛出异常，其他异常正常抛出。
    删除空目录，与delete_file保持接口一致性。

    Args:
        path: 目录路径

    Raises:
        OSError: 删除操作失败（目录不存在时不会抛出）
    """
    try:
        path.rmdir()
    except FileNotFoundError:
        pass


def move_file_with_conflict_resolution(source: Path, target: Path) -> Path:
    """移动文件，自动处理路径冲突

    先尝试直接移动，如果目标路径已存在，自动生成唯一路径并重试。
    生成的路径使用 `-jfk-xxxx` 格式后缀。
    最多重试10次，超过10次抛出异常。
    始终基于原始目标路径生成候选路径，避免路径越来越长。

    Args:
        source: 源文件路径
        target: 目标文件路径（可能已存在）

    Returns:
        实际移动到的目标路径（可能与输入的target不同）

    Raises:
        FileNotFoundError: 源文件不存在
        RuntimeError: 重试10次后仍无法找到唯一路径
        OSError: 其他移动操作失败

    Examples:
        >>> move_file_with_conflict_resolution(Path("a.mp4"), Path("b.mp4"))
        Path("b.mp4")  # 如果 b.mp4 不存在

        >>> move_file_with_conflict_resolution(Path("a.mp4"), Path("b.mp4"))
        Path("b-jfk-a3b2.mp4")  # 如果 b.mp4 已存在
    """
    # 保存原始目标路径，确保始终基于原始路径生成候选路径
    original_target = target
    current_target = target
    max_attempts = 10

    for attempt in range(max_attempts):
        try:
            move_file(source, current_target)
            return current_target
        except FileExistsError:
            # 目标路径已存在，生成新的候选路径
            if attempt == max_attempts - 1:
                raise RuntimeError(
                    f"无法为 {original_target} 生成唯一路径，已尝试 {max_attempts} 次",
                ) from None
            # 始终基于原始路径生成候选文件名
            current_target = generate_alternative_filename(original_target)
        except OSError:
            # 其他错误（如源文件不存在）直接抛出
            raise

    # 理论上不会执行到这里（循环内会返回或抛出异常），但为了满足类型检查
    raise RuntimeError(
        f"无法为 {original_target} 生成唯一路径，已尝试 {max_attempts} 次",
    )
