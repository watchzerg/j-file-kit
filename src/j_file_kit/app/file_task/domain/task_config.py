"""磁盘任务配置外壳（TaskConfig）

对应 `task_config.yaml` 中按 `type` 分块的一条记录；业务通过 `get_config` 转为各任务强类型配置模型。
"""

from typing import Any, TypeVar

from pydantic import BaseModel, Field

_T = TypeVar("_T", bound=BaseModel)


class TaskConfig(BaseModel):
    """磁盘上一条任务配置的通用外壳（`task_config.yaml` 内按类型分块）。

    `config` 为 JSON 可序列化的 dict，业务侧通过 `get_config(具体Pydantic模型)` 得到强类型
    配置（例如 `JavVideoOrganizeConfig`），避免 analyzer/管道直接依赖裸 dict。

    TODO: 将 `config` 演进为按 `type` 区分的判别联合，去掉 `Any` 与 `get_config` 上的类型忽略。
    """

    type: str = Field(..., description="任务类型（如 jav_video_organizer）")
    enabled: bool = Field(True, description="是否启用")
    config: dict[str, Any] = Field(..., description="任务特定配置")

    def get_config(self, config_type: type[_T]) -> _T:  # ty: ignore[invalid-type-form]
        """将本记录的 `config` dict 校验并转换为指定 Pydantic 模型（如 `JavVideoOrganizeConfig`）。

        典型调用点：`JavVideoOrganizer.__init__` 中完成一次反序列化，整次 run 共用 `self.file_config`。
        """
        return config_type.model_validate(self.config)
