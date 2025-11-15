"""文件系统操作

封装文件系统相关的操作，如文件移动、删除、创建目录等。
所有文件系统I/O操作都通过此模块统一管理，便于测试和未来扩展。
"""

from __future__ import annotations

from pathlib import Path


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


def delete_file(path: Path, missing_ok: bool = True) -> None:
    """删除文件

    Args:
        path: 文件路径
        missing_ok: 如果文件不存在是否静默成功

    Raises:
        OSError: 删除操作失败（当missing_ok=False时）
    """
    path.unlink(missing_ok=missing_ok)


def create_directory(path: Path, parents: bool = True, exist_ok: bool = True) -> None:
    """创建目录

    Args:
        path: 目录路径
        parents: 是否创建父目录
        exist_ok: 如果目录已存在是否静默成功

    Raises:
        OSError: 创建目录失败
    """
    path.mkdir(parents=parents, exist_ok=exist_ok)


def read_text_file(path: Path, encoding: str = "utf-8") -> str:
    """读取文本文件

    Args:
        path: 文件路径
        encoding: 文件编码

    Returns:
        文件内容

    Raises:
        FileNotFoundError: 文件不存在
        UnicodeDecodeError: 解码失败
    """
    with open(path, encoding=encoding) as f:
        return f.read()


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


def is_file(path: Path) -> bool:
    """检查路径是否为文件

    Args:
        path: 路径

    Returns:
        是否为文件
    """
    return path.is_file()


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


def delete_directory(path: Path, missing_ok: bool = True) -> None:
    """删除目录

    删除空目录，与delete_file保持接口一致性。
    设计意图：提供统一的目录删除接口，支持missing_ok参数以保持与delete_file的一致性。

    Args:
        path: 目录路径
        missing_ok: 如果目录不存在是否静默成功

    Raises:
        OSError: 删除操作失败（当missing_ok=False时）
        OSError: 目录不为空时删除失败
    """
    try:
        path.rmdir()
    except FileNotFoundError:
        if not missing_ok:
            raise
