"""Raw 阶段 2 前置：第一层目录枚举、关键字归一化、路径就绪检查。

编排层在 `run_phase2` 开头调用本模块；归宿路径均由 ``workspace_root`` 派生，此处仅做语义校验钩子占位。
"""

from pathlib import Path

from j_file_kit.app.file_task.application.raw_analyze_config import RawAnalyzeConfig
from j_file_kit.app.file_task.domain.organizer_defaults import DEFAULT_RAW_JUNK_KEYWORDS
from j_file_kit.shared.utils.name_keyword_match import (
    normalize_keyword_tokens,
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
    """返回 `(第一层目录 basename tokens, junk stem tokens)`——本期共用 ``DEFAULT_RAW_JUNK_KEYWORDS``。"""
    norm = normalize_keyword_tokens(DEFAULT_RAW_JUNK_KEYWORDS)
    return norm, norm


def validate_phase2_preflight_paths(
    dirs: list[Path],
    cfg: RawAnalyzeConfig,
    *,
    dir_keywords_norm: tuple[str, ...],
) -> Path:
    """确认阶段 2 所需路径可用；返回 ``folders_to_delete`` 路径。

    当前所有归宿目录均由代码从 workspace 派生，无需「半套配置」检测；保留本函数以便日后扩展预检。
    """
    _ = dirs
    _ = dir_keywords_norm
    return cfg.folders_to_delete
