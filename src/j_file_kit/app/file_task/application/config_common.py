"""file_task 配置的公共基元：媒体根、workspace 子目录约定与 JAV 收件箱预删子模型。

任务 YAML 仅保存各任务的 ``workspace_root``；``inbox``、``sorted``、``folders_video`` 等子目录名
在此模块集中定义，并由 ``jav_workspace_paths`` / ``raw_workspace_paths`` 从 root 派生，
避免目录名散落在 validator、organizer 与管线中。

测试可通过 monkeypatch 本模块的 ``JAV_MEDIA_ROOT`` / ``RAW_MEDIA_ROOT`` 调整默认媒体子根。
"""

from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, Field, model_validator

from j_file_kit.shared.constants import MEDIA_ROOT

# JAV 整理任务的默认媒体子根（与默认 ``workspace_root`` 对齐）；测试可 monkeypatch
JAV_MEDIA_ROOT = MEDIA_ROOT / "jav_workspace"

# Raw 整理任务的默认媒体子根；测试可 monkeypatch
RAW_MEDIA_ROOT = MEDIA_ROOT / "raw_workspace"


# --- 共享 workspace 子目录名 ---

WORKSPACE_SUBDIR_INBOX = "inbox"


# --- JAV：相对 workspace_root 的一级子目录名（磁盘约定，非配置项） ---

JAV_SUBDIR_INBOX = WORKSPACE_SUBDIR_INBOX
JAV_SUBDIR_SORTED = "sorted"
JAV_SUBDIR_UNSORTED = "unsorted"
JAV_SUBDIR_ARCHIVE = "archive"
JAV_SUBDIR_MISC = "misc"


@dataclass(frozen=True, slots=True)
class JavWorkspacePaths:
    """从 ``workspace_root`` 派生的 JAV 任务路径快照（字段名为语义别名，非 YAML 键）。"""

    root: Path
    inbox: Path
    sorted_dir: Path
    unsorted_dir: Path
    archive_dir: Path
    misc_dir: Path


def jav_workspace_paths(workspace_root: Path) -> JavWorkspacePaths:
    """将配置的 workspace 根解析为各阶段所需目录（子目录名由本模块常量决定）。"""
    r = workspace_root.expanduser().resolve(strict=False)
    return JavWorkspacePaths(
        root=r,
        inbox=r / JAV_SUBDIR_INBOX,
        sorted_dir=r / JAV_SUBDIR_SORTED,
        unsorted_dir=r / JAV_SUBDIR_UNSORTED,
        archive_dir=r / JAV_SUBDIR_ARCHIVE,
        misc_dir=r / JAV_SUBDIR_MISC,
    )


# --- Raw：相对 workspace_root 的一级子目录名 ---

RAW_SUBDIR_INBOX = WORKSPACE_SUBDIR_INBOX
RAW_SUBDIR_FOLDERS_TO_DELETE = "folders_to_delete"
RAW_SUBDIR_FOLDERS_VIDEO = "folders_video"
RAW_SUBDIR_FOLDERS_COMPRESSED = "folders_compressed"
RAW_SUBDIR_FOLDERS_PIC = "folders_pic"
RAW_SUBDIR_FOLDERS_AUDIO = "folders_audio"
RAW_SUBDIR_FOLDERS_MISC = "folders_misc"
RAW_SUBDIR_FILES_TO_DELETE = "files_to_delete"
RAW_SUBDIR_FILES_VIDEO_JAV = "files_video_jav"
RAW_SUBDIR_FILES_VIDEO_US = "files_video_us"
RAW_SUBDIR_FILES_VIDEO_JAV_VR = "files_video_jav_vr"
RAW_SUBDIR_FILES_VIDEO_US_VR = "files_video_us_vr"
RAW_SUBDIR_FILES_VIDEO_MOVIE = "files_video_movie"
RAW_SUBDIR_FILES_VIDEO_MISC = "files_video_misc"
RAW_SUBDIR_FILES_COMPRESSED = "files_compressed"
RAW_SUBDIR_FILES_PIC = "files_pic"
RAW_SUBDIR_FILES_AUDIO = "files_audio"
RAW_SUBDIR_FILES_MISC = "files_misc"


@dataclass(frozen=True, slots=True)
class RawWorkspacePaths:
    """从 ``workspace_root`` 派生的 Raw 任务路径快照（与旧 YAML 字段名语义对齐）。"""

    root: Path
    inbox: Path
    folders_to_delete: Path
    folders_video: Path
    folders_compressed: Path
    folders_pic: Path
    folders_audio: Path
    folders_misc: Path
    files_to_delete: Path
    files_video_jav: Path
    files_video_us: Path
    files_video_jav_vr: Path
    files_video_us_vr: Path
    files_video_movie: Path
    files_video_misc: Path
    files_compressed: Path
    files_pic: Path
    files_audio: Path
    files_misc: Path


def raw_workspace_paths(workspace_root: Path) -> RawWorkspacePaths:
    """将配置的 workspace 根解析为 Raw 三阶段所需目录。"""
    r = workspace_root.expanduser().resolve(strict=False)
    return RawWorkspacePaths(
        root=r,
        inbox=r / RAW_SUBDIR_INBOX,
        folders_to_delete=r / RAW_SUBDIR_FOLDERS_TO_DELETE,
        folders_video=r / RAW_SUBDIR_FOLDERS_VIDEO,
        folders_compressed=r / RAW_SUBDIR_FOLDERS_COMPRESSED,
        folders_pic=r / RAW_SUBDIR_FOLDERS_PIC,
        folders_audio=r / RAW_SUBDIR_FOLDERS_AUDIO,
        folders_misc=r / RAW_SUBDIR_FOLDERS_MISC,
        files_to_delete=r / RAW_SUBDIR_FILES_TO_DELETE,
        files_video_jav=r / RAW_SUBDIR_FILES_VIDEO_JAV,
        files_video_us=r / RAW_SUBDIR_FILES_VIDEO_US,
        files_video_jav_vr=r / RAW_SUBDIR_FILES_VIDEO_JAV_VR,
        files_video_us_vr=r / RAW_SUBDIR_FILES_VIDEO_US_VR,
        files_video_movie=r / RAW_SUBDIR_FILES_VIDEO_MOVIE,
        files_video_misc=r / RAW_SUBDIR_FILES_VIDEO_MISC,
        files_compressed=r / RAW_SUBDIR_FILES_COMPRESSED,
        files_pic=r / RAW_SUBDIR_FILES_PIC,
        files_audio=r / RAW_SUBDIR_FILES_AUDIO,
        files_misc=r / RAW_SUBDIR_FILES_MISC,
    )


def path_is_descendant_of(candidate: Path, ancestor: Path) -> bool:
    """candidate 解析后与 ancestor 相同或其下级目录。"""
    cand = candidate.expanduser().resolve(strict=False)
    anc = ancestor.expanduser().resolve(strict=False)
    return cand == anc or anc in cand.parents


def ensure_workspace_root_and_inbox(workspace_root: Path) -> None:
    """在持久化任务配置前创建 workspace 根目录与其 ``inbox`` 子目录。

    JAV 与 Raw 的一级收件箱目录名共享同一磁盘约定。
    失败时抛出 ``OSError``，由上层转为对用户可读的错误。
    """
    root = workspace_root.expanduser()
    root.mkdir(parents=True, exist_ok=True)
    (root / WORKSPACE_SUBDIR_INBOX).mkdir(parents=True, exist_ok=True)


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
