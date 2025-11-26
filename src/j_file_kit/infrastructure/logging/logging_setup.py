"""日志配置模块

配置 loguru 日志系统，提供标准库 logging 桥接和任务级别日志文件配置。
"""

import logging
from pathlib import Path
from types import FrameType

from loguru import logger

from j_file_kit.infrastructure.filesystem.operations import create_directory


class InterceptHandler(logging.Handler):
    """拦截标准库 logging 的 handler

    将标准库 logging 的日志调用路由到 loguru。
    """

    def emit(self, record: logging.LogRecord) -> None:
        """发送日志记录到 loguru

        Args:
            record: 标准库 logging 的日志记录
        """
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = str(record.levelno)

        frame: FrameType | None = logging.currentframe()
        depth = 2
        while frame is not None and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level,
            record.getMessage(),
        )


def setup_logging() -> None:
    """初始化日志系统

    配置 loguru 的全局设置，并设置标准库 logging 桥接。
    移除 loguru 默认 handler，配置 InterceptHandler 拦截所有标准库 logging 调用。
    """
    # 移除 loguru 默认 handler
    logger.remove()

    # 配置标准库 logging 桥接
    logging.basicConfig(handlers=[InterceptHandler()], level=logging.INFO, force=True)

    # 设置根 logger 级别
    logging.root.setLevel(logging.INFO)


def configure_task_logger(log_dir: Path, task_name: str, task_id: int) -> int:
    """为特定任务配置独立的 JSON Lines 日志文件

    为任务创建独立的日志文件，使用 JSON Lines 格式。
    日志文件命名：{task_name}_{task_id}.jsonl

    设计意图：
    - 每个任务使用独立的日志文件，便于后续分析和处理
    - 使用 JSON Lines 格式，保持与原 StructuredLogger 兼容
    - task_id 和 task_name 需要通过 logger.bind() 在调用时添加

    Args:
        log_dir: 日志目录
        task_name: 任务名称
        task_id: 任务ID（数据库中的整数ID）

    Returns:
        handler_id，用于后续移除该 handler
    """
    # 确保日志目录存在
    create_directory(log_dir, parents=True)

    # 日志文件路径
    log_file = log_dir / f"{task_name}_{task_id}.jsonl"

    # 添加文件 handler，使用 JSON 格式
    # serialize=True 会输出 JSON Lines 格式
    # task_id 和 task_name 需要通过 logger.bind() 在调用时添加
    handler_id = logger.add(
        str(log_file),
        serialize=True,
        level="DEBUG",
        rotation=None,  # 不轮转
        retention=None,  # 不自动删除
        compression=None,  # 不压缩
    )

    return handler_id


def remove_task_logger(handler_id: int) -> None:
    """移除任务级别的日志 handler

    在任务结束时调用，移除任务级别的日志 handler，避免日志泄漏和资源占用。

    设计意图：
    - 任务结束后清理 handler，避免日志写入到其他任务
    - 释放资源，避免文件句柄泄漏

    Args:
        handler_id: 要移除的 handler ID（由 configure_task_logger 返回）
    """
    logger.remove(handler_id)
