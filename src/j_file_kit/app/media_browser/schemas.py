"""Media browser API schemas。

定义媒体目录浏览相关的 HTTP API 响应数据结构。
"""

from pydantic import BaseModel, Field


class DirectoryItem(BaseModel):
    """单个目录条目"""

    name: str = Field(..., description="目录名（不含父路径）")
    path: str = Field(..., description="完整绝对路径字符串")


class ListDirectoriesResponse(BaseModel):
    """列出子目录响应"""

    path: str = Field(..., description="当前列出的父路径")
    children: list[DirectoryItem] = Field(
        ...,
        description="一级子目录列表，按名称字典序排序",
    )
