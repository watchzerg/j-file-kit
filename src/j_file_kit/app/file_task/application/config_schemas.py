"""File task 配置 API schemas。

定义 file task 配置管理相关的 HTTP API 请求和响应数据结构。
"""

from typing import Any

from pydantic import BaseModel, Field


class GetFileTaskConfigResponse(BaseModel):
    """获取 file task 配置响应

    `config` 为仓储中的原始 dict：不含应由代码注入的分析字段（扩展名集、`jav_filename_strip_substrings`、
    misc 删除 `extensions`）；GET 仍可能返回旧 YAML 里遗留的键直至某次 PATCH 重写。
    """

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
