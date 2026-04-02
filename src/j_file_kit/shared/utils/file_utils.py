"""文件系统工具函数

提供有业务价值的文件操作工具函数，无业务逻辑。

设计意图：
- 只封装需要额外处理（如幂等语义、边界检查）的操作
- 简单的 pathlib.Path 方法调用（如 exists(), is_dir(), rename()）应直接使用，不封装
- 所有函数都是无状态的纯工具函数
"""

from pathlib import Path

# ============================================================================
# 路径/文件名编码工具
# ============================================================================


def sanitize_surrogate_str(s: str) -> str:
    """将含 surrogate escape 的字符串转为合法的 UTF-8 字符串。

    Linux 文件系统允许文件名含任意字节序列。Python 用 surrogateescape 错误处理器
    将不可解码字节映射为代理字符（U+DC80～U+DCFF）。此类字符串无法直接编码为 UTF-8，
    写入 SQLite、日志文件或作为目标路径时会触发 UnicodeEncodeError。

    处理逻辑：先用 surrogateescape 将代理字符还原为原始字节，再以 UTF-8 重新解码；
    对仍无法解码的字节替换为 U+FFFD（\ufffd）。

    Args:
        s: 可能含代理字符的字符串

    Returns:
        合法的 UTF-8 字符串，不可编码字节以 U+FFFD 占位
    """
    return s.encode("utf-8", errors="surrogateescape").decode("utf-8", errors="replace")


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
