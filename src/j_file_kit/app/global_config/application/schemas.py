"""全局配置 API 请求和响应模型

定义全局配置管理相关的 HTTP API 请求和响应数据结构。
"""

from pydantic import BaseModel, Field


class UpdateGlobalConfigRequest(BaseModel):
    """更新全局配置请求（部分更新）"""

    inbox_dir: str | None = Field(None, description="待处理目录")
    sorted_dir: str | None = Field(None, description="已整理目录（有番号）")
    unsorted_dir: str | None = Field(None, description="未整理目录（无番号）")
    archive_dir: str | None = Field(None, description="归档目录")
    misc_dir: str | None = Field(None, description="杂项目录")
    starred_dir: str | None = Field(None, description="精选/收藏目录")


class UpdateConfigResponse(BaseModel):
    """更新配置响应"""

    message: str = Field(..., description="成功消息")
    code: str = Field("SUCCESS", description="响应代码")
