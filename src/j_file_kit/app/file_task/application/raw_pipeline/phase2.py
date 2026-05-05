"""Raw 管道阶段 2：inbox 第一层目录（关键字迁出 / 清洗 / 单链折叠 / 分类占位）。

迁出前预先判断是否存在「待删除关键字」目录：若存在则必须配置 `folders_to_delete`，
避免半套配置在 run 中途才失败。行为见仓库根目录 `docs/RAW_FILE_PROCESSING_PIPELINE.md`。"""

import secrets
import threading
from pathlib import Path

from loguru import logger

from j_file_kit.app.file_task.application.file_ops import (
    MAX_FILENAME_BYTES,
    move_directory_with_conflict_resolution,
    move_path_with_conflict_resolution,
    scan_directory_items,
    truncate_utf8_to_max_bytes,
)
from j_file_kit.app.file_task.application.raw_pipeline.context import PhaseContext
from j_file_kit.app.file_task.application.raw_pipeline.counters import RawPhaseCounters
from j_file_kit.app.file_task.application.raw_pipeline.keywords import (
    dir_name_matches,
    normalize_for_match,
    normalize_keyword_tokens,
)
from j_file_kit.app.file_task.domain.file_types import PathEntryType
from j_file_kit.app.file_task.domain.organizer_defaults import (
    DEFAULT_MISC_FILE_DELETE_EXTENSIONS,
    DEFAULT_PROBABLE_JUNK_MEDIA_KEYWORDS,
    DEFAULT_RAW_DIR_TO_DELETE_KEYWORDS,
)
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
    """对超长合并名按比例截断各「长段」；约束见 ``merge_chain_segments_to_basename`` docstring。"""
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
    """自链末端向第一层起点删除已搬空的中间目录（含起点目录本身若已空）。

    ``chain`` 按「叶 → 根」顺序遍历，确保先删内层目录。"""
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


def _collapse_level1_single_chain(
    ctx: PhaseContext,
    root_dir: Path,
    phases: RawPhaseCounters,
    *,
    scan_root: Path,
    dry_run: bool,
    cancellation_event: threading.Event | None,
) -> tuple[Path, bool]:
    """阶段 2.3：将第一层起点下的连续单链子目录折叠为单层目录名。

    先将链末端目录内的条目迁入临时 staging，再将 staging **整块**迁至 ``scan_root`` 下合并名（成功后才删旧链），
    避免「先拆链、后改名失败」导致仅剩 staging 又被误删。异常或取消时 staging 非空则改名为隔离目录。
    目标已存在时使用 ``-jfk-xxxx`` 冲突消解（与 ``move_directory_with_conflict_resolution`` 一致）。

    Returns:
        (后续 2.4 使用的目录路径, 是否在折叠中途被取消)。
    """
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


def _list_inbox_level1_dirs(scan_root: Path) -> list[Path]:
    """第一层子目录，确定性排序；与旧 `RawFilePipeline.list_inbox_level1_dirs` 前置条件一致。"""
    if not scan_root.exists():
        raise FileNotFoundError(f"扫描目录不存在: {scan_root}")
    if not scan_root.is_dir():
        raise NotADirectoryError(f"路径不是目录: {scan_root}")
    return sorted(p for p in scan_root.iterdir() if p.is_dir())


def _should_delete_clean_file(
    path: Path,
    *,
    misc_delete_ext: frozenset[str],
    junk_keywords_norm: tuple[str, ...],
) -> bool:
    """阶段 2.2：是否应删除该文件（扩展名 / stem 关键字 / 0 字节）。"""
    ext = path.suffix.lower()
    if ext in misc_delete_ext:
        return True
    stem_norm = normalize_for_match(path.stem)
    if any(k in stem_norm for k in junk_keywords_norm if k):
        return True
    try:
        if path.is_file() and path.stat().st_size == 0:
            return True
    except OSError:
        return False
    return False


def _move_dir_to_delete(
    ctx: PhaseContext,
    dir_path: Path,
    phases: RawPhaseCounters,
    *,
    dest_delete: Path,
    dry_run: bool,
) -> None:
    """阶段 2.1：整目录迁入 `folders_to_delete`（目录级冲突消解）。"""
    target = dest_delete / dir_path.name
    safe = sanitize_surrogate_str(str(dir_path))
    if dry_run:
        phases.phase2_moved_to_delete_dirs += 1
        logger.bind(
            run_id=str(ctx.run_id),
            run_name=ctx.run_name,
            level="RAW_PHASE",
            phase=2,
            subphase="to_delete_preview",
            source=safe,
            target=str(target),
        ).info("阶段2.1（dry_run）：预览整目录迁出到 folders_to_delete")
        return

    try:
        ensure_directory(dest_delete, parents=True)
        final = move_directory_with_conflict_resolution(dir_path, target)
        phases.phase2_moved_to_delete_dirs += 1
        logger.bind(
            run_id=str(ctx.run_id),
            run_name=ctx.run_name,
            level="RAW_PHASE",
            phase=2,
            subphase="to_delete",
            source=safe,
            target=str(final),
        ).info("阶段2.1：整目录已迁入 folders_to_delete")
    except Exception as e:
        logger.bind(
            run_id=str(ctx.run_id),
            run_name=ctx.run_name,
            error=str(e),
            source=safe,
        ).error("阶段2.1：整目录迁出失败")


def _maybe_delete_candidate_file(
    ctx: PhaseContext,
    path: Path,
    phases: RawPhaseCounters,
    *,
    misc_ext: frozenset[str],
    junk_keywords_norm: tuple[str, ...],
    dry_run: bool,
) -> None:
    """删除符合 2.2 规则的单个文件。"""
    if not _should_delete_clean_file(
        path,
        misc_delete_ext=misc_ext,
        junk_keywords_norm=junk_keywords_norm,
    ):
        return
    if dry_run:
        phases.phase2_cleaned_deleted_files += 1
        return
    try:
        path.unlink()
        phases.phase2_cleaned_deleted_files += 1
    except OSError as e:
        logger.bind(
            run_id=str(ctx.run_id),
            run_name=ctx.run_name,
            error=str(e),
        ).warning(f"阶段2.2：删除文件失败 {path}")


def _maybe_rmdir_below_root(
    ctx: PhaseContext,
    path: Path,
    root_resolved: Path,
    phases: RawPhaseCounters,
    *,
    dry_run: bool,
) -> None:
    """删空第一层目录下的空子目录；不在此处删 root 本体。"""
    if path.resolve(strict=False) == root_resolved:
        return
    if not path.exists() or not path.is_dir():
        return
    if any(path.iterdir()):
        return
    if dry_run:
        phases.phase2_cleaned_deleted_empty_dirs += 1
        return
    try:
        path.rmdir()
        phases.phase2_cleaned_deleted_empty_dirs += 1
    except OSError as e:
        logger.bind(
            run_id=str(ctx.run_id),
            run_name=ctx.run_name,
            error=str(e),
        ).warning(f"阶段2.2：删除空目录失败 {path}")


def _maybe_rmdir_root(
    ctx: PhaseContext,
    root_dir: Path,
    phases: RawPhaseCounters,
    *,
    dry_run: bool,
) -> None:
    """若第一层目录在清洗后已空则移除（不触碰 inbox）。"""
    if not root_dir.exists() or not root_dir.is_dir():
        return
    if any(root_dir.iterdir()):
        return
    if dry_run:
        phases.phase2_cleaned_deleted_empty_dirs += 1
        return
    try:
        root_dir.rmdir()
        phases.phase2_cleaned_deleted_empty_dirs += 1
    except OSError as e:
        logger.bind(
            run_id=str(ctx.run_id),
            run_name=ctx.run_name,
            error=str(e),
        ).warning(f"阶段2.2：删除空的第一层目录失败 {root_dir}")


def _clean_level1_dir(
    ctx: PhaseContext,
    root_dir: Path,
    phases: RawPhaseCounters,
    *,
    junk_keywords_norm: tuple[str, ...],
    dry_run: bool,
    cancellation_event: threading.Event | None,
) -> bool:
    """阶段 2.2：遍历目录删除垃圾文件与空子目录；返回 True 表示已请求取消。"""
    misc_ext = DEFAULT_MISC_FILE_DELETE_EXTENSIONS
    root_resolved = root_dir.resolve(strict=False)

    try:
        for path, kind in scan_directory_items(root_dir):
            if cancellation_event and cancellation_event.is_set():
                return True
            if kind == PathEntryType.FILE:
                _maybe_delete_candidate_file(
                    ctx,
                    path,
                    phases,
                    misc_ext=misc_ext,
                    junk_keywords_norm=junk_keywords_norm,
                    dry_run=dry_run,
                )
            elif kind == PathEntryType.DIRECTORY:
                _maybe_rmdir_below_root(
                    ctx,
                    path,
                    root_resolved,
                    phases,
                    dry_run=dry_run,
                )

        _maybe_rmdir_root(ctx, root_dir, phases, dry_run=dry_run)
    except FileNotFoundError:
        pass
    except NotADirectoryError:
        pass

    return False


def _classification_placeholder(
    ctx: PhaseContext,
    dir_path: Path,
    phases: RawPhaseCounters,
) -> None:
    """阶段 2.4：分类策略占位 — 打点 + 日志；目录仍保留于 inbox。"""
    phases.phase2_deferred_classification_dirs += 1
    logger.bind(
        run_id=str(ctx.run_id),
        run_name=ctx.run_name,
        level="RAW_PHASE",
        phase=2,
        subphase="classify_deferred",
        dir=str(dir_path),
    ).info("阶段2.4（占位）：第一层目录保留，后续分类逻辑待补充")


def _phase2_process_one_level1_dir(
    ctx: PhaseContext,
    dir_path: Path,
    phases: RawPhaseCounters,
    *,
    dir_keywords_norm: tuple[str, ...],
    junk_keywords_norm: tuple[str, ...],
    dest_delete: Path | None,
    dry_run: bool,
    cancellation_event: threading.Event | None,
) -> bool:
    """处理 inbox 下单个第一层目录（2.1 / 2.2 / 2.3 / 2.4）。

    Returns:
        ``True`` 表示应终止阶段 2（取消）。
    """
    if dir_name_matches(dir_path, dir_keywords_norm):
        if dest_delete is None:
            msg = "folders_to_delete 未设置"
            raise ValueError(msg)
        _move_dir_to_delete(
            ctx,
            dir_path,
            phases,
            dest_delete=dest_delete,
            dry_run=dry_run,
        )
        return False

    cancelled_inside = _clean_level1_dir(
        ctx,
        dir_path,
        phases,
        junk_keywords_norm=junk_keywords_norm,
        dry_run=dry_run,
        cancellation_event=cancellation_event,
    )
    if cancelled_inside:
        logger.bind(
            run_id=str(ctx.run_id),
            run_name=ctx.run_name,
        ).info("任务已被取消（阶段2 清洗循环内）")
        return True

    if not dir_path.exists():
        phases.phase2_removed_dirs += 1
        return False

    dir_for_classify, cancelled_collapse = _collapse_level1_single_chain(
        ctx,
        dir_path,
        phases,
        scan_root=ctx.scan_root,
        dry_run=dry_run,
        cancellation_event=cancellation_event,
    )
    if cancelled_collapse:
        return True

    if not dir_for_classify.exists():
        phases.phase2_removed_dirs += 1
        return False

    _classification_placeholder(ctx, dir_for_classify, phases)
    return False


def run_phase2(
    ctx: PhaseContext,
    phases: RawPhaseCounters,
    *,
    dry_run: bool,
    cancellation_event: threading.Event | None,
) -> bool:
    """阶段 2：第一层目录 — 迁出 / 清洗 / 单链折叠 / 分类占位；返回 True 表示已请求取消。"""
    if cancellation_event and cancellation_event.is_set():
        logger.bind(
            run_id=str(ctx.run_id),
            run_name=ctx.run_name,
        ).info("任务已被取消（阶段2 前）")
        return True

    dirs = _list_inbox_level1_dirs(ctx.scan_root)
    phases.phase2_seen_dirs = len(dirs)

    dir_keywords_norm = normalize_keyword_tokens(
        DEFAULT_RAW_DIR_TO_DELETE_KEYWORDS,
    )
    junk_keywords_norm = normalize_keyword_tokens(
        DEFAULT_PROBABLE_JUNK_MEDIA_KEYWORDS,
    )

    needs_delete_dest = any(
        dir_name_matches(dir_path, dir_keywords_norm) for dir_path in dirs
    )
    dest_delete = ctx.analyze_config.folders_to_delete
    if needs_delete_dest and dest_delete is None:
        raise ValueError("folders_to_delete 未设置（存在待迁出的关键字目录）")

    logger.bind(
        run_id=str(ctx.run_id),
        run_name=ctx.run_name,
        level="RAW_PHASE",
        phase=2,
    ).info(f"阶段2：处理 inbox 第一层目录 {len(dirs)} 个")

    for dir_path in dirs:
        if cancellation_event and cancellation_event.is_set():
            logger.bind(
                run_id=str(ctx.run_id),
                run_name=ctx.run_name,
            ).info("任务已被取消（阶段2）")
            return True

        stop = _phase2_process_one_level1_dir(
            ctx,
            dir_path,
            phases,
            dir_keywords_norm=dir_keywords_norm,
            junk_keywords_norm=junk_keywords_norm,
            dest_delete=dest_delete,
            dry_run=dry_run,
            cancellation_event=cancellation_event,
        )
        if stop:
            return True

    return False
