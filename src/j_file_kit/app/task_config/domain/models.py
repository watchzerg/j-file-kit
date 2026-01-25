"""任务配置领域模型

定义任务配置的通用基础设施模型。
TaskConfig 是通用任务配置容器，被所有 task app 依赖。
"""

from typing import Any, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T", bound=BaseModel)


class TaskConfig(BaseModel):
    """任务配置

    定义单个任务的配置，包括任务类型、启用状态和任务特定配置。

    这是通用的任务配置容器，被所有 task app（如 file_task）依赖。
    config 字段是一个字典，存储任务特定的配置数据。

    设计意图：
    - 提供统一的任务配置结构
    - 通过 get_config() 方法提供类型安全的配置访问
    - 使用 dict 字段实现配置的灵活性，支持不同任务类型的特定配置
    """

    type: str = Field(..., description="任务类型（如 jav_video_organizer）")
    enabled: bool = Field(True, description="是否启用")
    config: dict[str, Any] = Field(..., description="任务特定配置")

    # TODO: 未来将 config 替换为判别联合配置模型，消除 Any 与 type ignore
    # 方向：为不同任务类型定义显式 Pydantic 配置模型并统一解析入口
    def get_config(self, config_type: type[T]) -> T:  # type: ignore[valid-type]
        """获取类型化的配置对象

        将字典配置转换为具体的 Pydantic 模型，提供类型安全。

        Args:
            config_type: 目标配置模型类型

        Returns:
            类型化的配置对象
        """
        return config_type.model_validate(self.config)  # type: ignore[no-any-return, attr-defined]
