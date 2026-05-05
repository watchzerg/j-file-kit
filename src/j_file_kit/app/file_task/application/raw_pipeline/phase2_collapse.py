"""Raw 阶段 2.3：第一层起点下连续单链子目录折叠为单层目录名。

通过 staging 整目录搬迁再删旧链，避免部分迁移后误删数据；失败/取消时非空 staging 隔离而非静默删除。
"""

import secrets
import threading
from pathlib import Path

from loguru import logger

from j_file_kit.app.file_task.application.file_ops import (
    MAX_FILENAME_BYTES,
    move_directory_with_conflict_resolution,
    move_path_with_conflict_resolution,
    truncate_utf8_to_max_bytes,
)
from j_file_kit.app.file_task.application.raw_pipeline.context import PhaseContext
from j_file_kit.app.file_task.application.raw_pipeline.counters import RawPhaseCounters
from j_file_kit.shared.utils.file_utils import ensure_directory, sanitize_surrogate_str

CHAIN_SEGMENT_SHORT_CHARS = 10


def _quarantine_failed_collapse_staging_if_needed(
    scan_root: Path,
    work: Path,
    ctx: PhaseContext,
    *,
    reason: str,
) -> Path | None:
    """折叠未完成且 ``work`` 仍在磁盘上时：空 staging 直接删掉；非空则改名隔离，禁止静默删数据。

    Returns:
        隔离后的路径；若已清空或无 staging 则 ``None``；改名屡次失败时亦返回 ``None``（此时 ``work`` 原名保留）。
    """
    try:
        if not work.exists() or not work.is_dir():
            return None
        if not any(work.iterdir()):
            work.rmdir()
            return None
    except OSError:
        return None

    for _ in range(12):
        dest = (
            scan_root / f"raw-chain-quarantine-run{ctx.run_id}-{secrets.token_hex(8)}"
        )
        if dest.exists():
            continue
        try:
            work.rename(dest)
            return dest
        except OSError:
            continue

    logger.bind(
        run_id=str(ctx.run_id),
        run_name=ctx.run_name,
        level="RAW_PHASE",
        phase=2,
        subphase="collapse_chain_quarantine_failed",
        reason=reason,
        path=str(work),
    ).error(
        "阶段2.3：隔离 staging 失败，数据仍在原 staging 路径（通常为 inbox 下点目录），请人工处理",
    )
    return None


def collect_single_chain_segments(root_dir: Path) -> tuple[list[str], Path]:
    """自第一层目录起点向下收集连续「仅单子目录、无文件」链路的各层目录名。

    在遇到文件、遇到分叉或遇到空目录终点时停止；最后一层目录名始终计入 ``segments``。
    返回 (各层目录名片段, 链末端目录路径)。
    """
    segments: list[str] = []
    current = root_dir
    while True:
        if not current.exists() or not current.is_dir():
            break
        entries = list(current.iterdir())
        dirs = sorted((p for p in entries if p.is_dir()), key=lambda p: p.name)
        files = [p for p in entries if p.is_file()]
        segments.append(current.name)
        if files:
            break
        if len(dirs) != 1:
            break
        current = dirs[0]
    return segments, current


def merge_chain_segments_to_basename(segments: list[str]) -> str | None:
    """将链路段名以下划线合并为单一目录名；总 UTF-8 字节长度不超过 ``MAX_FILENAME_BYTES``。

    - 整体未超长：直接 ``"_".join``。
    - 超长：长度 ``>= CHAIN_SEGMENT_SHORT_CHARS`` 的段可按原 UTF-8 字节长度占比分配预算并截断；
      短段（``< CHAIN_SEGMENT_SHORT_CHARS`` 字符）永不截断。
    - 若短段占用后剩余预算不足以容纳各长段的至少前 ``CHAIN_SEGMENT_SHORT_CHARS`` 个字符：返回 ``None``（调用方跳过折叠）。
    """
    n = len(segments)
    sep_bytes = max(0, n - 1)
    enc_lens = [len(s.encode()) for s in segments]
    total_raw = sum(enc_lens) + sep_bytes
    if total_raw <= MAX_FILENAME_BYTES:
        return "_".join(segments)
    return _merge_oversized_chain_segments(
        segments,
        enc_lens=enc_lens,
        sep_bytes=sep_bytes,
    )


def _merge_oversized_chain_segments(
    segments: list[str],
    *,
    enc_lens: list[int],
    sep_bytes: int,
) -> str | None:
    long_indices = [
        i for i, s in enumerate(segments) if len(s) >= CHAIN_SEGMENT_SHORT_CHARS
    ]
    short_indices = [
        i for i, s in enumerate(segments) if len(s) < CHAIN_SEGMENT_SHORT_CHARS
    ]
    if not long_indices:
        return None

    fixed_short_bytes = sum(enc_lens[i] for i in short_indices)
    available_for_long = MAX_FILENAME_BYTES - sep_bytes - fixed_short_bytes
    if available_for_long <= 0:
        return None

    min_preserves: list[int] = []
    for i in long_indices:
        prefix = segments[i][:CHAIN_SEGMENT_SHORT_CHARS]
        min_preserves.append(len(prefix.encode()))
    sum_min = sum(min_preserves)
    if sum_min > available_for_long:
        return None

    slack = available_for_long - sum_min
    sum_long_orig = sum(enc_lens[i] for i in long_indices)
    if sum_long_orig <= 0:
        return None

    shares: list[int] = []
    for i in long_indices:
        shares.append((slack * enc_lens[i]) // sum_long_orig)
    distributed = sum(shares)
    remainder = slack - distributed

    targets: list[int] = [
        min_preserves[k] + shares[k] for k in range(len(long_indices))
    ]
    for k in range(remainder):
        targets[k % len(targets)] += 1

    parts = list(segments)
    for k, seg_idx in enumerate(long_indices):
        parts[seg_idx] = truncate_utf8_to_max_bytes(segments[seg_idx], targets[k])

    merged = "_".join(parts)
    if len(merged.encode()) > MAX_FILENAME_BYTES:
        return None
    return merged


def _remove_collapsed_chain_dirs(leaf_path: Path, root_chain: Path) -> None:
    chain: list[Path] = []
    cur: Path = leaf_path
    while True:
        chain.append(cur)
        if cur == root_chain:
            break
        parent = cur.parent
        if parent == cur:
            break
        cur = parent

    for p in chain:
        if not p.exists() or not p.is_dir():
            continue
        try:
            if not any(p.iterdir()):
                p.rmdir()
        except OSError:
            return


def collapse_level1_single_chain(
    ctx: PhaseContext,
    root_dir: Path,
    phases: RawPhaseCounters,
    *,
    scan_root: Path,
    dry_run: bool,
    cancellation_event: threading.Event | None,
) -> tuple[Path, bool]:
    """单链折叠；返回 (后续 2.4 使用的目录路径, 是否在折叠中途被取消)。"""
    segments, leaf_path = collect_single_chain_segments(root_dir)
    if len(segments) < 2:
        return root_dir, False

    merged_name = merge_chain_segments_to_basename(segments)
    if merged_name is None:
        phases.phase2_skipped_collapse_dirs += 1
        logger.bind(
            run_id=str(ctx.run_id),
            run_name=ctx.run_name,
            level="RAW_PHASE",
            phase=2,
            subphase="collapse_chain_skip",
            reason="basename_budget",
            root=str(root_dir),
        ).info("阶段2.3：跳过单链折叠（合并目录名字节预算不足）")
        return root_dir, False

    safe_root = sanitize_surrogate_str(str(root_dir))

    if dry_run:
        phases.phase2_collapsed_chain_dirs += 1
        logger.bind(
            run_id=str(ctx.run_id),
            run_name=ctx.run_name,
            level="RAW_PHASE",
            phase=2,
            subphase="collapse_chain_preview",
            source=safe_root,
            merged_name=merged_name,
            segments="/".join(segments),
        ).info("阶段2.3（dry_run）：预览单链折叠")
        return root_dir, False

    work = scan_root / f".raw-chain-collapse-{secrets.token_hex(8)}"
    try:
        ensure_directory(work, parents=True)
        for child in sorted(leaf_path.iterdir(), key=lambda p: p.name):
            if cancellation_event and cancellation_event.is_set():
                preserved = _quarantine_failed_collapse_staging_if_needed(
                    scan_root,
                    work,
                    ctx,
                    reason="cancelled_during_child_moves",
                )
                logger.bind(
                    run_id=str(ctx.run_id),
                    run_name=ctx.run_name,
                    level="RAW_PHASE",
                    phase=2,
                    subphase="collapse_chain_cancelled",
                    quarantine=str(preserved) if preserved else "",
                    staging=str(work),
                ).info(
                    "任务已被取消（阶段2 折叠迁移子项时）；已迁入 staging 的数据未删除，必要时见隔离目录",
                )
                return root_dir, True
            move_path_with_conflict_resolution(child, work / child.name)

        if cancellation_event and cancellation_event.is_set():
            preserved = _quarantine_failed_collapse_staging_if_needed(
                scan_root,
                work,
                ctx,
                reason="cancelled_after_child_moves",
            )
            logger.bind(
                run_id=str(ctx.run_id),
                run_name=ctx.run_name,
                level="RAW_PHASE",
                phase=2,
                subphase="collapse_chain_cancelled",
                quarantine=str(preserved) if preserved else "",
                staging=str(work),
            ).info(
                "任务已被取消（阶段2 折叠即将落名前）；staging 内数据未删除",
            )
            return root_dir, True

        dest_initial = scan_root / merged_name
        final_dir = move_directory_with_conflict_resolution(work, dest_initial)

        _remove_collapsed_chain_dirs(leaf_path, root_dir)

        phases.phase2_collapsed_chain_dirs += 1
        logger.bind(
            run_id=str(ctx.run_id),
            run_name=ctx.run_name,
            level="RAW_PHASE",
            phase=2,
            subphase="collapse_chain",
            source=safe_root,
            target=str(final_dir),
            merged_name=merged_name,
        ).info("阶段2.3：单链目录已折叠")
        return final_dir, False
    except Exception as e:
        phases.phase2_skipped_collapse_dirs += 1
        preserved = _quarantine_failed_collapse_staging_if_needed(
            scan_root,
            work,
            ctx,
            reason="exception",
        )
        logger.bind(
            run_id=str(ctx.run_id),
            run_name=ctx.run_name,
            error=str(e),
            source=safe_root,
            merged_name=merged_name,
            quarantine=str(preserved) if preserved else "",
            staging=str(work),
            level="RAW_PHASE",
            phase=2,
            subphase="collapse_chain_failed",
        ).error(
            "阶段2.3：单链折叠失败（staging 未静默删除；非空则已迁至 raw-chain-quarantine-* 或仍位于原 staging）",
        )
        return root_dir, False
