"""file_task 配置的公共基元：媒体根路径、路径字段清单与 JAV 收件箱预删子模型。

将这些符号独立出来，是为了让 `jav_task_config` / `raw_task_config` 与分析侧 DTO 单向依赖公共层，
避免 JAV 与 Raw 拆开后出现互相 import 或把“测试可 patch 的根路径”绑死在某一任务模块上。
"""

from pydantic import BaseModel, Field, model_validator

from j_file_kit.shared.constants import MEDIA_ROOT

# JAV 整理任务的媒体子根目录；测试可 monkeypatch 此模块变量
JAV_MEDIA_ROOT = MEDIA_ROOT / "jav_workspace"

# Raw 整理任务的媒体子根目录；测试可 monkeypatch 此模块变量
RAW_MEDIA_ROOT = MEDIA_ROOT / "raw_workspace"


class InboxDeleteRules(BaseModel):
    """收件箱预删除规则：在 `analyze_jav_file` 里先于扩展名分类求值，命中则直接 `DeleteDecision`（条件 OR）。

    用于删掉广告壳、过小占位文件等；空 token 在 `drop_empty_strings` 中剔除。
    """

    exact_stems: set[str] = Field(
        default_factory=set,
        description="stem 完全等于其中任一则删除（大小写敏感）",
    )
    max_size_bytes: int | None = Field(
        default=None,
        description="若设置则删除体积不超过该值的文件（含 0 表示仅空文件）；None 表示不启用",
    )

    @model_validator(mode="after")
    def drop_empty_strings(self) -> InboxDeleteRules:
        self.exact_stems = {s for s in self.exact_stems if s != ""}
        return self


RAW_FILE_ORGANIZE_PATH_FIELD_NAMES: tuple[str, ...] = (
    "inbox_dir",
    "folders_to_delete",
    "folders_video",
    "folders_compressed",
    "folders_pic",
    "folders_audio",
    "folders_misc",
    "files_video_to_delete",
    "files_video_jav",
    "files_video_us",
    "files_video_jav_vr",
    "files_video_us_vr",
    "files_video_movie",
    "files_video_misc",
    "files_compressed",
    "files_pic",
    "files_audio",
    "files_misc",
)
