"""领域上下文模型

定义处理过程中的上下文对象，携带分析结果和中间状态。
"""

from typing import Any

from pydantic import BaseModel, Field


class ItemContext(BaseModel):
    """Item 处理上下文基类

    所有 item 处理上下文的基类，包含通用的处理状态和扩展字段。
    """

    skip_remaining: bool = Field(False, description="短路标记，跳过后续处理器")
    custom_data: dict[str, Any] = Field(default_factory=dict, description="自定义数据")
