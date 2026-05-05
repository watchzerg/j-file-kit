"""Raw 收件箱整理任务：YAML / 存储层的强类型 `config` 模型。

路径字段名与磁盘约定一致，便于 `config_validator` 做冲突检测；与 `RawAnalyzeConfig` 分离是因为分析阶段
不含 `inbox_dir` 且携带扩展名集合，避免组织器与管线互相拖拽完整任务配置。
"""

from pathlib import Path

from pydantic import BaseModel, Field, model_validator

import j_file_kit.app.file_task.application.config_common as _config_common


class RawFileOrganizeConfig(BaseModel):
    """Raw 收件箱整理任务强类型配置（YAML `config` 字典对应物）。

    字段名与业务目录名一致（`folders_*` / `files_*`）。`inbox_dir` 为扫描根；其余目录为分类归宿。
    不变量：凡非 None 的路径必须为 `RAW_MEDIA_ROOT`（`/media/raw_workspace`）子目录。
    """

    inbox_dir: Path | None = Field(default=None, description="inbox：BT 下载初始目录")
    folders_to_delete: Path | None = Field(
        default=None,
        description="待人工确认的疑似删除目录（Raw 阶段 2.1 命中关键字时整目录迁入）",
    )
    folders_video: Path | None = Field(default=None, description="视频目录")
    folders_compressed: Path | None = Field(default=None, description="压缩文件目录")
    folders_pic: Path | None = Field(default=None, description="图片目录")
    folders_audio: Path | None = Field(default=None, description="音频目录")
    folders_misc: Path | None = Field(
        default=None,
        description="无法自动分类的杂项目录",
    )
    files_video_to_delete: Path | None = Field(
        default=None,
        description="待人工确认后删除的视频文件目录",
    )
    files_video_jav: Path | None = Field(default=None, description="JAV 视频文件目录")
    files_video_us: Path | None = Field(default=None, description="US 视频文件目录")
    files_video_jav_vr: Path | None = Field(
        default=None,
        description="JAV VR 视频文件目录",
    )
    files_video_us_vr: Path | None = Field(
        default=None,
        description="US VR 视频文件目录",
    )
    files_video_movie: Path | None = Field(default=None, description="电影文件目录")
    files_video_misc: Path | None = Field(default=None, description="杂项视频文件目录")
    files_compressed: Path | None = Field(default=None, description="压缩文件目录")
    files_pic: Path | None = Field(default=None, description="图片文件目录")
    files_audio: Path | None = Field(default=None, description="音频文件目录")
    files_misc: Path | None = Field(
        default=None,
        description="无法自动分类的杂项文件目录",
    )

    @model_validator(mode="after")
    def validate_dir_paths_under_raw_media_root(self) -> RawFileOrganizeConfig:
        """所有非 None 目录路径必须位于 RAW_MEDIA_ROOT 下（运行时读 `config_common.RAW_MEDIA_ROOT`，便于测试 monkeypatch）。"""
        raw_root = _config_common.RAW_MEDIA_ROOT.resolve(strict=False)
        errors: list[str] = []
        for field_name in _config_common.RAW_FILE_ORGANIZE_PATH_FIELD_NAMES:
            dir_path: Path | None = getattr(self, field_name)
            if (
                dir_path is not None
                and raw_root not in dir_path.resolve(strict=False).parents
            ):
                errors.append(
                    f"{field_name}（{dir_path}）必须是 {raw_root} 的子目录",
                )
        if errors:
            raise ValueError(
                "目录路径不符合 RAW_MEDIA_ROOT 约束：\n"
                + "\n".join(f"  - {e}" for e in errors),
            )
        return self
