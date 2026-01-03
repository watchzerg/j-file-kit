"""文件系统工具函数

提供有业务价值的文件操作工具函数，无业务逻辑。

设计意图：
- 只封装需要额外处理（如幂等语义、边界检查）的操作
- 简单的 pathlib.Path 方法调用（如 exists(), is_dir(), rename()）应直接使用，不封装
- 所有函数都是无状态的纯工具函数
"""

from pathlib import Path

# ============================================================================
# 文件操作
# ============================================================================


def delete_file_if_exists(path: Path) -> None:
    """删除文件（幂等）

    文件不存在时静默成功，其他异常正常抛出。

    Args:
        path: 文件路径

    Raises:
        OSError: 删除操作失败（文件不存在时不会抛出）
    """
    path.unlink(missing_ok=True)


# ============================================================================
# 目录操作
# ============================================================================


def ensure_directory(path: Path, parents: bool = True) -> None:
    """创建目录（幂等，带类型检查）

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


def delete_directory_if_empty(path: Path) -> bool:
    """删除空目录（幂等）

    目录非空或不存在时静默跳过，不抛出异常。

    Args:
        path: 目录路径

    Returns:
        是否实际执行了删除
    """
    if not path.is_dir():
        return False
    try:
        path.rmdir()
        return True
    except OSError:
        return False
