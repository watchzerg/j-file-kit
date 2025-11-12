"""配置模型

处理 YAML 配置文件的解析和验证。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, TypeVar

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

T = TypeVar("T", bound=BaseModel)


class GlobalConfig(BaseModel):
    """全局配置"""

    scan_roots: list[Path] = Field(..., description="扫描根目录列表")
    log_dir: Path = Field(Path("./logs"), description="日志目录")
    report_dir: Path = Field(Path("./reports"), description="报告目录")
    db_path: Path = Field(Path("./data/j_file_kit.db"), description="数据库文件路径")

    @model_validator(mode="after")
    def validate_paths(self) -> GlobalConfig:
        """验证路径配置"""
        # 验证扫描根目录（仅在非测试环境中）
        import os

        if not os.environ.get("PYTEST_CURRENT_TEST"):
            for scan_root in self.scan_roots:
                if not scan_root.exists():
                    raise ValueError(f"扫描根目录不存在: {scan_root}")
                if not scan_root.is_dir():
                    raise ValueError(f"扫描根目录不是目录: {scan_root}")

        return self

    @property
    def scan_root(self) -> Path:
        """向后兼容：返回第一个扫描根目录"""
        if not self.scan_roots:
            raise ValueError("没有配置扫描根目录")
        return self.scan_roots[0]


class FileOrganizeConfig(BaseModel):
    """文件整理任务配置"""

    organized_dir: Path = Field(..., description="整理后的视频图片存储目录（B类）")
    unorganized_dir: Path = Field(..., description="无番号视频图片存储目录（C类）")
    archive_dir: Path = Field(..., description="压缩文件存储目录")
    misc_dir: Path = Field(..., description="其他文件存储目录（D类）")
    video_extensions: set[str] = Field(..., description="视频文件扩展名")
    image_extensions: set[str] = Field(..., description="图片文件扩展名")
    archive_extensions: set[str] = Field(..., description="压缩文件扩展名")
    delete_rules: dict[str, Any] = Field(
        default_factory=dict,
        description="删除规则配置（keywords, extensions, max_size）",
    )

    @model_validator(mode="after")
    def validate_extensions(self) -> FileOrganizeConfig:
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


class TaskDefinition(BaseModel):
    """任务定义"""

    name: str = Field(..., description="任务名称")
    type: Literal["file_organize", "db_update"] = Field(..., description="任务类型")
    enabled: bool = Field(True, description="是否启用")
    config: dict[str, Any] = Field(..., description="任务特定配置")

    def get_config(self, config_type: type[T]) -> T:  # type: ignore[valid-type]
        """获取类型化的配置对象"""
        return config_type.model_validate(self.config)  # type: ignore[no-any-return, attr-defined]


class TaskConfig(BaseModel):
    """完整任务配置"""

    model_config = ConfigDict(populate_by_name=True)

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

    with open(config_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return TaskConfig.model_validate(data)


def save_config(config: TaskConfig, config_path: str | Path) -> None:
    """保存配置文件

    Args:
        config: 配置对象
        config_path: 保存路径
    """
    config_path = Path(config_path)

    # 确保配置文件所在目录存在
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # 转换为字典并处理别名
    data = config.model_dump(by_alias=True)

    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, indent=2)


def ensure_directories_exist(config: TaskConfig) -> None:
    """确保配置中的所有目录存在

    直接创建目录，不检查是否已存在。如果目录已存在，则继续执行。
    如果创建失败，则抛出异常。

    Args:
        config: 配置对象

    Raises:
        OSError: 如果目录创建失败
    """
    # 创建全局配置中的目录
    try:
        config.global_.log_dir.mkdir(parents=True, exist_ok=True)
        config.global_.report_dir.mkdir(parents=True, exist_ok=True)
        config.global_.db_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise OSError(f"创建全局目录失败: {e}") from e

    # 创建任务配置中的目录
    for task in config.tasks:
        if task.type == "file_organize":
            try:
                task_config: FileOrganizeConfig = task.get_config(FileOrganizeConfig)
                task_config.organized_dir.mkdir(parents=True, exist_ok=True)
                task_config.unorganized_dir.mkdir(parents=True, exist_ok=True)
                task_config.archive_dir.mkdir(parents=True, exist_ok=True)
                task_config.misc_dir.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                raise OSError(f"创建任务 '{task.name}' 的目录失败: {e}") from e


def create_default_config() -> TaskConfig:
    """创建默认配置"""
    return TaskConfig(
        global_=GlobalConfig(  # type: ignore[call-arg]
            scan_roots=[Path("./scan")],
            log_dir=Path("./logs"),
            report_dir=Path("./reports"),
            db_path=Path("./data/j_file_kit.db"),
        ),
        tasks=[
            TaskDefinition(
                name="video_file_organizer",
                type="file_organize",
                enabled=True,
                config={
                    "organized_dir": "./organized",
                    "unorganized_dir": "./unorganized",
                    "archive_dir": "./archives",
                    "misc_dir": "./misc",
                    "video_extensions": [
                        ".mp4",
                        ".avi",
                        ".mkv",
                        ".mov",
                        ".wmv",
                        ".flv",
                        ".webm",
                    ],
                    "image_extensions": [
                        ".jpg",
                        ".jpeg",
                        ".png",
                        ".webp",
                        ".bmp",
                        ".gif",
                        ".tiff",
                    ],
                    "archive_extensions": [
                        ".zip",
                        ".rar",
                        ".7z",
                        ".tar",
                        ".gz",
                        ".bz2",
                        ".xz",
                    ],
                    "delete_rules": {
                        "keywords": [".tmp", ".temp", ".bak", ".old"],
                        "extensions": [".tmp", ".temp", ".bak", ".old"],
                        "max_size": 1048576,
                    },
                },
            )
        ],
    )
