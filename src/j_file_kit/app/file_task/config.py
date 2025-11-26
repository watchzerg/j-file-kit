"""文件任务配置模型

定义文件任务相关的配置模型。
"""

from typing import Any

from pydantic import BaseModel, Field, model_validator


class JavVideoOrganizeConfig(BaseModel):
    """JAV视频文件整理任务配置"""

    video_extensions: set[str] = Field(..., description="视频文件扩展名")
    image_extensions: set[str] = Field(..., description="图片文件扩展名")
    archive_extensions: set[str] = Field(..., description="压缩文件扩展名")
    misc_file_delete_rules: dict[str, Any] = Field(
        default_factory=dict,
        description="Misc文件删除规则配置（keywords, extensions, max_size）",
    )

    @model_validator(mode="after")
    def validate_extensions(self) -> JavVideoOrganizeConfig:
        """验证扩展名格式"""
        # 确保扩展名以点号开头
        self.video_extensions = {
            ext if ext.startswith(".") else f".{ext}" for ext in self.video_extensions
        }
        self.image_extensions = {
            ext if ext.startswith(".") else f".{ext}" for ext in self.image_extensions
        }
        self.archive_extensions = {
            ext if ext.startswith(".") else f".{ext}" for ext in self.archive_extensions
        }
        return self
