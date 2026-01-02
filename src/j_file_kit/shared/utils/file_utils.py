"""文件系统工具函数

提供纯 I/O 文件操作的通用工具函数，无业务逻辑。

设计意图：
- 封装底层文件系统操作，提供统一的接口
- 所有函数都是无状态的纯工具函数
- 业务相关的文件操作（如带 -jfk- 后缀的冲突处理）应放在对应 domain 中
"""

from pathlib import Path

# ============================================================================
# 文件操作
# ============================================================================


def move_file(source: Path, target: Path) -> None:
    """移动文件

    Args:
        source: 源文件路径
        target: 目标文件路径

    Raises:
        FileNotFoundError: 源文件不存在
        FileExistsError: 目标文件已存在
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


# ============================================================================
# 目录操作
# ============================================================================


def ensure_directory(path: Path, parents: bool = True) -> None:
    """创建目录

    静默成功：目录已存在时不抛出异常，其他异常正常抛出。
    如果路径已存在但不是目录（如普通文件），抛出 FileExistsError。

    Args:
        path: 目录路径
        parents: 是否创建父目录

    Raises:
        FileExistsError: 路径已存在但不是目录
        OSError: 其他创建目录失败的情况
    """
    if path.exists() and not path.is_dir():
        raise FileExistsError(f"路径已存在但不是目录: {path}")
    path.mkdir(parents=parents, exist_ok=True)


def delete_directory(path: Path) -> None:
    """删除空目录

    静默成功：目录不存在时不抛出异常，其他异常正常抛出。
    与 delete_file 保持接口一致性。

    Args:
        path: 目录路径

    Raises:
        OSError: 删除操作失败（目录不存在时不会抛出）
    """
    try:
        path.rmdir()
    except FileNotFoundError:
        pass


def is_directory_empty(path: Path) -> bool:
    """检查目录是否为空

    判断目录是否为空（无文件和子目录），用于决定是否可以安全删除。

    Args:
        path: 目录路径

    Returns:
        目录是否为空。如果目录不存在或无法访问，返回 False。
    """
    try:
        return next(path.iterdir(), None) is None
    except (OSError, FileNotFoundError):
        return False


# ============================================================================
# 路径检查
# ============================================================================


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
