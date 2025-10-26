"""配置模型

处理 YAML 配置文件的解析和验证。
"""

from __future__ import annotations

import yaml
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class GlobalConfig(BaseModel):
    """全局配置"""
    scan_root: Path = Field(..., description="扫描根目录")
    log_dir: Path = Field(Path("./logs"), description="日志目录")
    report_dir: Path = Field(Path("./reports"), description="报告目录")
    
    @model_validator(mode="after")
    def validate_paths(self) -> GlobalConfig:
        """验证路径配置"""
        # 确保目录存在
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.report_dir.mkdir(parents=True, exist_ok=True)
        return self


class FileOrganizeConfig(BaseModel):
    """文件整理任务配置"""
    todo_non_vidpic_dir: Path = Field(..., description="非视频图片文件目录")
    todo_vidpic_dir: Path = Field(..., description="无番号视频图片文件目录")
    video_extensions: set[str] = Field(..., description="视频文件扩展名")
    image_extensions: set[str] = Field(..., description="图片文件扩展名")
    serial_id_pattern: str = Field(
        r"[A-Za-z]{2,5}-\d+", 
        description="番号正则表达式"
    )
    
    @model_validator(mode="after")
    def validate_extensions(self) -> FileOrganizeConfig:
        """验证扩展名格式"""
        # 确保扩展名以点号开头
        self.video_extensions = {
            ext if ext.startswith('.') else f'.{ext}' 
            for ext in self.video_extensions
        }
        self.image_extensions = {
            ext if ext.startswith('.') else f'.{ext}' 
            for ext in self.image_extensions
        }
        return self


class TaskDefinition(BaseModel):
    """任务定义"""
    name: str = Field(..., description="任务名称")
    type: Literal["file_organize", "db_update"] = Field(..., description="任务类型")
    enabled: bool = Field(True, description="是否启用")
    config: dict[str, Any] = Field(..., description="任务特定配置")
    
    def get_config(self, config_type: type[BaseModel]) -> BaseModel:
        """获取类型化的配置对象"""
        return config_type.model_validate(self.config)


class TaskConfig(BaseModel):
    """完整任务配置"""
    global_: GlobalConfig = Field(alias="global", description="全局配置")
    tasks: list[TaskDefinition] = Field(..., description="任务列表")
    
    @property
    def enabled_tasks(self) -> list[TaskDefinition]:
        """获取启用的任务"""
        return [task for task in self.tasks if task.enabled]
    
    def get_task(self, name: str) -> TaskDefinition | None:
        """根据名称获取任务"""
        for task in self.tasks:
            if task.name == name:
                return task
        return None


def load_config(config_path: str | Path) -> TaskConfig:
    """加载配置文件
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        解析后的配置对象
        
    Raises:
        FileNotFoundError: 配置文件不存在
        yaml.YAMLError: YAML 解析错误
        ValidationError: 配置验证失败
    """
    config_path = Path(config_path)
    
    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    return TaskConfig.model_validate(data)


def save_config(config: TaskConfig, config_path: str | Path) -> None:
    """保存配置文件
    
    Args:
        config: 配置对象
        config_path: 保存路径
    """
    config_path = Path(config_path)
    
    # 转换为字典并处理别名
    data = config.model_dump(by_alias=True)
    
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, indent=2)


def create_default_config() -> TaskConfig:
    """创建默认配置"""
    return TaskConfig(
        global_=GlobalConfig(
            scan_root=Path("/path/to/scan"),
            log_dir=Path("./logs"),
            report_dir=Path("./reports")
        ),
        tasks=[
            TaskDefinition(
                name="video_file_organizer",
                type="file_organize",
                enabled=True,
                config={
                    "todo_non_vidpic_dir": "/path/to/todo-non-vidpic",
                    "todo_vidpic_dir": "/path/to/todo-vidpic",
                    "video_extensions": [".mp4", ".avi", ".mkv", ".mov"],
                    "image_extensions": [".jpg", ".jpeg", ".png", ".webp"],
                    "serial_id_pattern": r"[A-Za-z]{2,5}-\d+"
                }
            )
        ]
    )
