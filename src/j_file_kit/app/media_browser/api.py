"""Media browser API 路由。

提供媒体目录浏览端点，用于按层级懒加载枚举 /media 下的子目录。
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException, status

from j_file_kit.app.media_browser.schemas import DirectoryItem, ListDirectoriesResponse

# 所有路径必须在此根目录下，测试可通过 monkeypatch 覆盖
MEDIA_ROOT = Path("/media")

router = APIRouter(prefix="/api/media", tags=["media"])


def list_subdirectories(
    path: Path,
    *,
    media_root: Path = MEDIA_ROOT,
) -> ListDirectoriesResponse:
    """枚举 path 下的一级子目录。

    纯函数，便于单元测试直接调用。

    Args:
        path: 要列出子目录的目标路径，必须等于 media_root 或是其子路径。
        media_root: 允许的根目录，默认为模块级 MEDIA_ROOT。

    Returns:
        包含当前路径和一级子目录列表（按名称字典序排序）的响应对象。

    Raises:
        ValueError: path 不在 media_root 下、路径不存在或路径不是目录。
        PermissionError: 无权限访问该路径。
    """
    resolved = path.resolve(strict=False)
    resolved_root = media_root.resolve(strict=False)

    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise ValueError(f"路径 {path} 不在允许的根目录 {media_root} 下")

    if not resolved.exists():
        raise ValueError(f"路径不存在：{path}")

    if not resolved.is_dir():
        raise ValueError(f"路径不是目录：{path}")

    children = sorted(
        (
            DirectoryItem(name=entry.name, path=str(entry))
            for entry in resolved.iterdir()
            if entry.is_dir()
        ),
        key=lambda item: item.name,
    )

    return ListDirectoriesResponse(path=str(resolved), children=children)


@router.get("/directories", response_model=ListDirectoriesResponse)
async def list_directories(path: str | None = None) -> ListDirectoriesResponse:
    """列出指定路径下的一级子目录。

    用于前端目录选择树的懒加载展开，每次只返回一级子目录。

    Args:
        path: 目标路径字符串，缺省时默认为 /media。

    Returns:
        当前路径及其一级子目录列表（按名称字典序排序）。

    Raises:
        HTTPException 400: 路径不在 /media 下、路径不存在或路径不是目录。
        HTTPException 403: 无权限访问该路径。
    """
    target = Path(path) if path is not None else MEDIA_ROOT
    try:
        return list_subdirectories(target, media_root=MEDIA_ROOT)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_PATH", "message": str(e)},
        ) from e
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "PERMISSION_DENIED", "message": str(e)},
        ) from e
