"""统计信息跟踪器

管理 TaskReport 的统计信息更新，封装统计信息更新逻辑。
使 FilePipeline 主类更简洁，职责更清晰。
"""

from ....interfaces.file.repositories import FileItemRepository
from ....models import FileItemResult, TaskReport


class StatisticsTracker:
    """统计信息跟踪器

    负责管理 TaskReport 的统计信息更新，包括：
    - 根据文件处理结果更新统计信息（总数、成功数、错误数等）
    - 从数据库重新计算统计信息，确保准确性

    设计意图：
    - 封装统计信息更新逻辑，使 Pipeline 主类更简洁
    - 统一统计信息管理，避免逻辑分散
    - 支持内存统计和数据库统计的一致性
    """

    def __init__(self, report: TaskReport) -> None:
        """初始化统计信息跟踪器

        Args:
            report: 任务报告实例，用于更新统计信息
        """
        self.report = report

    def update(self, result: FileItemResult) -> None:
        """根据文件处理结果更新统计信息

        根据文件处理结果更新统计信息，包括：
        - 总item数
        - 成功/错误/跳过/警告item数
        - 总处理耗时

        设计意图：
        - 实时更新内存中的统计信息，用于日志记录
        - 支持增量更新，避免重复计算

        Args:
            result: 文件处理结果
        """
        self.report.total_items += 1

        if result.success:
            if result.was_skipped:
                self.report.skipped_items += 1
            elif result.has_warnings:
                self.report.warning_items += 1
            else:
                self.report.success_items += 1
        else:
            self.report.error_items += 1

        self.report.total_duration_ms += result.total_duration_ms

    def finalize(self, file_item_repository: FileItemRepository) -> None:
        """最终化统计信息

        从数据库重新计算统计信息，确保准确性。
        在任务结束时调用，确保统计信息与数据库中的数据一致。

        设计意图：
        - 确保统计信息的准确性，避免内存统计与数据库不一致
        - total_duration_ms 是所有item处理的总耗时，不是任务总耗时
        - 在任务结束时统一更新，避免中间状态不一致

        Args:
            file_item_repository: 文件处理结果仓储实例，用于查询统计信息
        """
        # 从数据库重新计算统计信息，确保准确性
        # total_duration_ms 是所有item处理的总耗时，不是任务总耗时
        stats = file_item_repository.get_statistics()
        self.report.update_from_stats(stats)
