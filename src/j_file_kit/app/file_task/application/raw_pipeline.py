"""Raw 收件箱整理管道。

设计意图：与 `FilePipeline` 解耦，采用 inbox **第一层** 文件与目录的三阶段编排：
阶段 1 将散落文件收入 `files_misc`；阶段 2 处理第一层目录（关键字迁出 / 清洗 / 分类占位）；
阶段 3 占位，为后续 `files_misc` 分流预留钩子。
"""

import threading
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from j_file_kit.app.file_task.application.config import RawAnalyzeConfig
from j_file_kit.app.file_task.application.executor import (
    ExecutionResult,
    ExecutionStatus,
    execute_decision,
)
from j_file_kit.app.file_task.application.file_ops import (
    move_directory_with_conflict_resolution,
    normalize_move_basename,
    scan_directory_items,
)
from j_file_kit.app.file_task.domain.decisions import FileItemData, MoveDecision
from j_file_kit.app.file_task.domain.models import (
    FileTaskRunStatistics,
    FileType,
    PathEntryType,
)
from j_file_kit.app.file_task.domain.organizer_defaults import (
    DEFAULT_MISC_FILE_DELETE_EXTENSIONS,
    DEFAULT_PROBABLE_JUNK_MEDIA_KEYWORDS,
    DEFAULT_RAW_DIR_TO_DELETE_KEYWORDS,
)
from j_file_kit.app.file_task.domain.ports import FileResultRepository
from j_file_kit.shared.utils.file_utils import (
    ensure_directory,
    sanitize_surrogate_str,
)
from j_file_kit.shared.utils.logging import configure_task_logger, remove_task_logger


def _normalize_for_raw_keyword_match(text: str) -> str:
    """NFKC + casefold：用于目录名与子串关键字匹配的统一形态。"""
    return unicodedata.normalize("NFKC", text.casefold())


def _normalize_keyword_tokens(tokens: tuple[str, ...]) -> tuple[str, ...]:
    """预归一化配置中的 ASCII/中文关键字，避免热路径重复 NFKC。"""
    return tuple(_normalize_for_raw_keyword_match(t) for t in tokens if t != "")


def _should_delete_raw_clean_file(
    path: Path,
    *,
    misc_delete_ext: frozenset[str],
    junk_keywords_norm: tuple[str, ...],
) -> bool:
    """阶段 2.2：是否应删除该文件（扩展名 / stem 关键字 / 0 字节）。"""
    ext = path.suffix.lower()
    if ext in misc_delete_ext:
        return True
    stem_norm = _normalize_for_raw_keyword_match(path.stem)
    if any(k in stem_norm for k in junk_keywords_norm if k):
        return True
    try:
        if path.is_file() and path.stat().st_size == 0:
            return True
    except OSError:
        return False
    return False


@dataclass
class _RawPhaseCounters:
    """单次 run 内阶段计数（并入返回统计；不落目录明细表）。"""

    phase1_seen_files: int = 0
    phase1_moved_files: int = 0
    phase1_error_files: int = 0
    phase2_seen_dirs: int = 0
    phase2_moved_to_delete_dirs: int = 0
    phase2_cleaned_deleted_files: int = 0
    phase2_cleaned_deleted_empty_dirs: int = 0
    phase2_removed_dirs: int = 0
    phase2_deferred_classification_dirs: int = 0
    phase3_seen_files_misc: int = 0
    phase3_deferred_files_misc: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "phase1_seen_files": self.phase1_seen_files,
            "phase1_moved_files": self.phase1_moved_files,
            "phase1_error_files": self.phase1_error_files,
            "phase2_seen_dirs": self.phase2_seen_dirs,
            "phase2_moved_to_delete_dirs": self.phase2_moved_to_delete_dirs,
            "phase2_cleaned_deleted_files": self.phase2_cleaned_deleted_files,
            "phase2_cleaned_deleted_empty_dirs": self.phase2_cleaned_deleted_empty_dirs,
            "phase2_removed_dirs": self.phase2_removed_dirs,
            "phase2_deferred_classification_dirs": self.phase2_deferred_classification_dirs,
            "phase3_seen_files_misc": self.phase3_seen_files_misc,
            "phase3_deferred_files_misc": self.phase3_deferred_files_misc,
        }


class RawFilePipeline:
    """Raw 任务专用管道：只遍历 `scan_root` 第一层条目并按阶段编排。"""

    def __init__(
        self,
        run_id: int,
        run_name: str,
        scan_root: Path,
        analyze_config: RawAnalyzeConfig,
        log_dir: Path,
        file_result_repository: FileResultRepository,
    ) -> None:
        """绑定一次 run 的标识与依赖；参数形状与 `FilePipeline` 对齐。"""
        self.run_id = run_id
        self.run_name = run_name
        self.scan_root = scan_root
        self.analyze_config = analyze_config
        self.log_dir = log_dir
        self._file_result_repository = file_result_repository
        self._log_handler_id: int | None = None

    def list_inbox_level1_files(self) -> list[Path]:
        """返回 `scan_root` 下第一层普通文件（确定性排序）。"""
        if not self.scan_root.exists():
            raise FileNotFoundError(f"扫描目录不存在: {self.scan_root}")
        if not self.scan_root.is_dir():
            raise NotADirectoryError(f"路径不是目录: {self.scan_root}")
        return sorted(p for p in self.scan_root.iterdir() if p.is_file())

    def list_inbox_level1_dirs(self) -> list[Path]:
        """返回 `scan_root` 下第一层子目录（确定性排序）。"""
        if not self.scan_root.exists():
            raise FileNotFoundError(f"扫描目录不存在: {self.scan_root}")
        if not self.scan_root.is_dir():
            raise NotADirectoryError(f"路径不是目录: {self.scan_root}")
        return sorted(p for p in self.scan_root.iterdir() if p.is_dir())

    def run(
        self,
        dry_run: bool = False,
        cancellation_event: threading.Event | None = None,
    ) -> FileTaskRunStatistics:
        """执行三阶段编排；阶段 3 本期仅占位，阶段 1 将第一层文件移入 `files_misc`。"""
        phases = _RawPhaseCounters()
        try:
            self._start_task(dry_run)

            cancelled = self._phase1_level1_files_to_misc(
                phases,
                dry_run=dry_run,
                cancellation_event=cancellation_event,
            )
            if cancelled:
                return self._finish_task(dry_run, phases)

            cancelled = self._phase2_level1_dirs(
                phases,
                dry_run=dry_run,
                cancellation_event=cancellation_event,
            )
            if cancelled:
                return self._finish_task(dry_run, phases)

            self._phase3_files_misc_placeholder(phases)

            return self._finish_task(dry_run, phases)

        except Exception as e:
            logger.bind(
                run_id=str(self.run_id),
                run_name=self.run_name,
            ).error(f"Raw 管道执行失败: {e!s}")
            raise
        finally:
            if self._log_handler_id is not None:
                remove_task_logger(self._log_handler_id)

    def _start_task(self, dry_run: bool) -> None:
        """注册按 run 隔离的 loguru sink，并写 TASK_START。"""
        self._log_handler_id = configure_task_logger(
            self.log_dir,
            self.run_name,
            self.run_id,
        )

        scan_root_str = str(self.scan_root) if self.scan_root else "未设置"
        logger.bind(
            run_id=str(self.run_id),
            run_name=self.run_name,
            scan_root=scan_root_str,
            level="TASK_START",
        ).info(f"开始任务: {self.run_name}")

        if dry_run:
            logger.bind(
                run_id=str(self.run_id),
                run_name=self.run_name,
            ).info("运行在预览模式（dry_run）")

    def _finish_task(
        self,
        dry_run: bool,
        phases: _RawPhaseCounters,
    ) -> FileTaskRunStatistics:
        """合并仓储聚合与阶段计数，写 TASK_END。"""
        repo_stats = self._file_result_repository.get_statistics(self.run_id)
        merged = {**repo_stats, **phases.as_dict()}

        logger.bind(
            run_id=str(self.run_id),
            run_name=self.run_name,
            level="TASK_END",
            total_items=merged.get("total_items", 0),
            success_items=merged.get("success_items", 0),
            error_items=merged.get("error_items", 0),
            skipped_items=merged.get("skipped_items", 0),
            **phases.as_dict(),
        ).info(f"任务完成: {self.run_name}")

        if dry_run:
            logger.bind(
                run_id=str(self.run_id),
                run_name=self.run_name,
            ).info("预览模式执行完成")

        return FileTaskRunStatistics.model_validate(merged)

    def _phase1_level1_files_to_misc(
        self,
        phases: _RawPhaseCounters,
        *,
        dry_run: bool,
        cancellation_event: threading.Event | None,
    ) -> bool:
        """阶段 1：收件箱第一层文件 -> `files_misc`。"""
        dest = self.analyze_config.files_misc
        level1_files = self.list_inbox_level1_files()
        phases.phase1_seen_files = len(level1_files)

        if dest is None:
            if level1_files:
                raise ValueError("files_misc 未设置")
            return False

        logger.bind(
            run_id=str(self.run_id),
            run_name=self.run_name,
            level="RAW_PHASE",
            phase=1,
        ).info(f"阶段1：处理 inbox 第一层文件 {len(level1_files)} 个")

        for path in level1_files:
            if cancellation_event and cancellation_event.is_set():
                logger.bind(
                    run_id=str(self.run_id),
                    run_name=self.run_name,
                ).info("任务已被取消（阶段1）")
                return True

            start_time = time.time()
            try:
                basename = normalize_move_basename(sanitize_surrogate_str(path.name))
                target = dest / basename
                decision = MoveDecision(
                    source_path=path,
                    target_path=target,
                    file_type=FileType.MISC,
                    serial_id=None,
                )
                result = execute_decision(decision, dry_run=dry_run)
                duration_ms = (time.time() - start_time) * 1000

                item = self._item_data_from_move(path, decision, result, duration_ms)
                self._file_result_repository.save_result(self.run_id, item)

                if result.status in (
                    ExecutionStatus.SUCCESS,
                    ExecutionStatus.PREVIEW,
                ):
                    phases.phase1_moved_files += 1
                elif result.status == ExecutionStatus.ERROR:
                    phases.phase1_error_files += 1

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                safe_path = sanitize_surrogate_str(str(path))
                logger.bind(
                    run_id=str(self.run_id),
                    run_name=self.run_name,
                    error=str(e),
                ).error(f"阶段1 处理文件失败: {safe_path}")
                error_data = FileItemData(
                    path=path,
                    stem=path.stem,
                    file_type=FileType.MISC,
                    serial_id=None,
                    decision_type="error",
                    target_path=None,
                    success=False,
                    error_message=str(e),
                    duration_ms=duration_ms,
                )
                self._file_result_repository.save_result(self.run_id, error_data)
                phases.phase1_error_files += 1

        return False

    def _phase2_level1_dirs(
        self,
        phases: _RawPhaseCounters,
        *,
        dry_run: bool,
        cancellation_event: threading.Event | None,
    ) -> bool:
        """阶段 2：第一层目录 — 2.1 关键字整目录迁出 / 2.2 清洗 / 2.3 分类占位。"""
        if cancellation_event and cancellation_event.is_set():
            logger.bind(
                run_id=str(self.run_id),
                run_name=self.run_name,
            ).info("任务已被取消（阶段2 前）")
            return True

        dirs = self.list_inbox_level1_dirs()
        phases.phase2_seen_dirs = len(dirs)

        dir_keywords_norm = _normalize_keyword_tokens(
            DEFAULT_RAW_DIR_TO_DELETE_KEYWORDS,
        )
        junk_keywords_norm = _normalize_keyword_tokens(
            DEFAULT_PROBABLE_JUNK_MEDIA_KEYWORDS,
        )

        needs_delete_dest = any(
            self._level1_dir_name_matches(dir_path, dir_keywords_norm)
            for dir_path in dirs
        )
        dest_delete = self.analyze_config.folders_to_delete
        if needs_delete_dest and dest_delete is None:
            raise ValueError("folders_to_delete 未设置（存在待迁出的关键字目录）")

        logger.bind(
            run_id=str(self.run_id),
            run_name=self.run_name,
            level="RAW_PHASE",
            phase=2,
        ).info(f"阶段2：处理 inbox 第一层目录 {len(dirs)} 个")

        for dir_path in dirs:
            if cancellation_event and cancellation_event.is_set():
                logger.bind(
                    run_id=str(self.run_id),
                    run_name=self.run_name,
                ).info("任务已被取消（阶段2）")
                return True

            if self._level1_dir_name_matches(dir_path, dir_keywords_norm):
                if dest_delete is None:
                    msg = "folders_to_delete 未设置"
                    raise ValueError(msg)
                self._phase2_move_dir_to_delete(
                    dir_path,
                    phases,
                    dest_delete=dest_delete,
                    dry_run=dry_run,
                )
                continue

            cancelled_inside = self._phase2_clean_level1_dir(
                dir_path,
                phases,
                junk_keywords_norm=junk_keywords_norm,
                dry_run=dry_run,
                cancellation_event=cancellation_event,
            )
            if cancelled_inside:
                logger.bind(
                    run_id=str(self.run_id),
                    run_name=self.run_name,
                ).info("任务已被取消（阶段2 清洗循环内）")
                return True

            if not dir_path.exists():
                phases.phase2_removed_dirs += 1
                continue

            self._phase2_classification_placeholder(dir_path, phases)

        return False

    def _level1_dir_name_matches(
        self,
        dir_path: Path,
        keywords_norm: tuple[str, ...],
    ) -> bool:
        name = sanitize_surrogate_str(dir_path.name)
        hay = _normalize_for_raw_keyword_match(name)
        return any(k in hay for k in keywords_norm if k)

    def _phase2_move_dir_to_delete(
        self,
        dir_path: Path,
        phases: _RawPhaseCounters,
        *,
        dest_delete: Path,
        dry_run: bool,
    ) -> None:
        """阶段 2.1：整目录迁入 `folders_to_delete`（目录级 `-jfk-xxxx` 冲突消解）。"""
        target = dest_delete / dir_path.name
        safe = sanitize_surrogate_str(str(dir_path))
        if dry_run:
            phases.phase2_moved_to_delete_dirs += 1
            logger.bind(
                run_id=str(self.run_id),
                run_name=self.run_name,
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
                run_id=str(self.run_id),
                run_name=self.run_name,
                level="RAW_PHASE",
                phase=2,
                subphase="to_delete",
                source=safe,
                target=str(final),
            ).info("阶段2.1：整目录已迁入 folders_to_delete")
        except Exception as e:
            logger.bind(
                run_id=str(self.run_id),
                run_name=self.run_name,
                error=str(e),
                source=safe,
            ).error("阶段2.1：整目录迁出失败")

    def _phase2_clean_level1_dir(
        self,
        root_dir: Path,
        phases: _RawPhaseCounters,
        *,
        junk_keywords_norm: tuple[str, ...],
        dry_run: bool,
        cancellation_event: threading.Event | None,
    ) -> bool:
        """阶段 2.2：自底向上删除垃圾文件与空子目录；不删除 inbox 本身。返回 True 表示已请求取消。"""
        misc_ext = DEFAULT_MISC_FILE_DELETE_EXTENSIONS
        root_resolved = root_dir.resolve(strict=False)

        try:
            for path, kind in scan_directory_items(root_dir):
                if cancellation_event and cancellation_event.is_set():
                    return True
                if kind == PathEntryType.FILE:
                    self._phase2_maybe_delete_clean_candidate_file(
                        path,
                        phases,
                        misc_ext=misc_ext,
                        junk_keywords_norm=junk_keywords_norm,
                        dry_run=dry_run,
                    )
                elif kind == PathEntryType.DIRECTORY:
                    self._phase2_maybe_rmdir_clean_empty_below_root(
                        path,
                        root_resolved,
                        phases,
                        dry_run=dry_run,
                    )

            self._phase2_maybe_rmdir_clean_empty_root(root_dir, phases, dry_run=dry_run)
        except FileNotFoundError, NotADirectoryError:
            pass

        return False

    def _phase2_maybe_delete_clean_candidate_file(
        self,
        path: Path,
        phases: _RawPhaseCounters,
        *,
        misc_ext: frozenset[str],
        junk_keywords_norm: tuple[str, ...],
        dry_run: bool,
    ) -> None:
        """删除符合 2.2 规则的单个文件。"""
        if not _should_delete_raw_clean_file(
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
                run_id=str(self.run_id),
                run_name=self.run_name,
                error=str(e),
            ).warning(f"阶段2.2：删除文件失败 {path}")

    def _phase2_maybe_rmdir_clean_empty_below_root(
        self,
        path: Path,
        root_resolved: Path,
        phases: _RawPhaseCounters,
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
                run_id=str(self.run_id),
                run_name=self.run_name,
                error=str(e),
            ).warning(f"阶段2.2：删除空目录失败 {path}")

    def _phase2_maybe_rmdir_clean_empty_root(
        self,
        root_dir: Path,
        phases: _RawPhaseCounters,
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
                run_id=str(self.run_id),
                run_name=self.run_name,
                error=str(e),
            ).warning(f"阶段2.2：删除空的第一层目录失败 {root_dir}")

    def _phase2_classification_placeholder(
        self,
        dir_path: Path,
        phases: _RawPhaseCounters,
    ) -> None:
        """阶段 2.3：分类策略占位 — 打点 + 日志；目录仍保留于 inbox。"""
        phases.phase2_deferred_classification_dirs += 1
        logger.bind(
            run_id=str(self.run_id),
            run_name=self.run_name,
            level="RAW_PHASE",
            phase=2,
            subphase="classify_deferred",
            dir=str(dir_path),
        ).info("阶段2.3（占位）：第一层目录保留，后续分类逻辑待补充")

    def _phase3_files_misc_placeholder(self, phases: _RawPhaseCounters) -> None:
        """阶段 3 占位：统计 `files_misc` 第一层文件数，分流规则后续迭代。"""
        misc = self.analyze_config.files_misc
        if misc is None or not misc.exists() or not misc.is_dir():
            phases.phase3_seen_files_misc = 0
            phases.phase3_deferred_files_misc = 0
            logger.bind(
                run_id=str(self.run_id),
                run_name=self.run_name,
                level="RAW_PHASE",
                phase=3,
            ).info("阶段3（占位）：files_misc 不可用或不存在，跳过计数")
            return

        seen = sum(1 for p in misc.iterdir() if p.is_file())
        phases.phase3_seen_files_misc = seen
        phases.phase3_deferred_files_misc = seen

        logger.bind(
            run_id=str(self.run_id),
            run_name=self.run_name,
            level="RAW_PHASE",
            phase=3,
        ).info(
            f"阶段3（占位）：files_misc 第一层文件 {seen} 个，暂未分流到 files_*",
        )

    def _item_data_from_move(
        self,
        path: Path,
        decision: MoveDecision,
        result: ExecutionResult,
        duration_ms: float,
    ) -> FileItemData:
        """折叠 Move + ExecutionResult 为入库模型。"""
        success = result.status in (
            ExecutionStatus.SUCCESS,
            ExecutionStatus.PREVIEW,
        )
        err_msg = result.message if result.status == ExecutionStatus.ERROR else None
        return FileItemData(
            path=path,
            stem=path.stem,
            file_type=decision.file_type,
            serial_id=decision.serial_id,
            decision_type="move",
            target_path=result.target_path,
            success=success,
            error_message=err_msg,
            duration_ms=duration_ms,
        )
