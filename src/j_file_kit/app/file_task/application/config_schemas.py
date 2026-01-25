"""File task 配置 API schemas。

定义 file task 配置管理相关的 HTTP API 请求和响应数据结构。
"""

from typing import Any

from pydantic import BaseModel, Field


class GetFileTaskConfigResponse(BaseModel):
    """获取 file task 配置响应"""

    type: str = Field(..., description="任务类型")
    enabled: bool = Field(..., description="是否启用")
    config: dict[str, Any] = Field(..., description="任务配置")


class UpdateFileTaskConfigRequest(BaseModel):
    """更新 file task 配置请求（部分更新）"""

    enabled: bool | None = Field(None, description="是否启用")
    config: dict[str, Any] | None = Field(None, description="任务配置（部分更新）")


class UpdateFileTaskConfigResponse(BaseModel):
    """更新 file task 配置响应"""

    message: str = Field(..., description="成功消息")
    code: str = Field("SUCCESS", description="响应代码")
