"""Raw 阶段 2 前置：第一层目录枚举、关键字归一化、必须配置的路径校验。

编排层在 `run_phase2` 开头调用本模块，保证「半套配置」在阶段开始前失败，而非中途抛错。
"""

from pathlib import Path

from j_file_kit.app.file_task.application.raw_analyze_config import RawAnalyzeConfig
from j_file_kit.app.file_task.application.raw_pipeline.keywords import (
    dir_name_matches,
    normalize_keyword_tokens,
)
from j_file_kit.app.file_task.domain.organizer_defaults import (
    DEFAULT_PROBABLE_JUNK_MEDIA_KEYWORDS,
    DEFAULT_RAW_DIR_TO_DELETE_KEYWORDS,
)


def list_inbox_level1_dirs(scan_root: Path) -> list[Path]:
    """第一层子目录，确定性排序；与旧 `RawFilePipeline.list_inbox_level1_dirs` 前置条件一致。"""
    if not scan_root.exists():
        msg = f"扫描目录不存在: {scan_root}"
        raise FileNotFoundError(msg)
    if not scan_root.is_dir():
        msg = f"路径不是目录: {scan_root}"
        raise NotADirectoryError(msg)
    return sorted(p for p in scan_root.iterdir() if p.is_dir())


def build_phase2_normalized_keywords() -> tuple[tuple[str, ...], tuple[str, ...]]:
    """返回 `(待删目录关键字 tokens, 垃圾 stem 关键字 tokens)`，用于 2.1 / 2.2 匹配。"""
    dir_keywords_norm = normalize_keyword_tokens(DEFAULT_RAW_DIR_TO_DELETE_KEYWORDS)
    junk_keywords_norm = normalize_keyword_tokens(DEFAULT_PROBABLE_JUNK_MEDIA_KEYWORDS)
    return dir_keywords_norm, junk_keywords_norm


def ensure_phase2_classification_targets(cfg: RawAnalyzeConfig) -> None:
    """当 inbox 存在待 2.4 分类的第一层目录时，要求归宿路径齐备。"""
    pairs = [
        ("files_misc", cfg.files_misc),
        ("folders_pic", cfg.folders_pic),
        ("folders_audio", cfg.folders_audio),
        ("folders_compressed", cfg.folders_compressed),
        ("folders_video", cfg.folders_video),
        ("folders_misc", cfg.folders_misc),
    ]
    missing = [name for name, p in pairs if p is None]
    if missing:
        msg = "Raw 阶段2.4 需要配置归宿目录（存在待分类的第一层目录）：" + ", ".join(
            missing
        )
        raise ValueError(msg)


def validate_phase2_preflight_paths(
    dirs: list[Path],
    cfg: RawAnalyzeConfig,
    *,
    dir_keywords_norm: tuple[str, ...],
) -> Path | None:
    """校验阶段 2 所需路径配置；通过则返回 ``folders_to_delete``（可为 ``None``）。

    Raises:
        ValueError: 存在待迁出关键字目录但 ``folders_to_delete`` 未配置。
    """
    needs_delete_dest = any(
        dir_name_matches(dir_path, dir_keywords_norm) for dir_path in dirs
    )
    dest_delete = cfg.folders_to_delete
    if needs_delete_dest and dest_delete is None:
        msg = "folders_to_delete 未设置（存在待迁出的关键字目录）"
        raise ValueError(msg)

    needs_classification_targets = any(
        not dir_name_matches(dir_path, dir_keywords_norm) for dir_path in dirs
    )
    if needs_classification_targets:
        ensure_phase2_classification_targets(cfg)

    return dest_delete
