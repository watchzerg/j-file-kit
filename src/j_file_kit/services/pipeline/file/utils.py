"""Pipeline 模块特定的工具函数

提供 Pipeline 处理流程中的错误处理和上下文创建工具函数。
这些函数是 pipeline 模块内部实现细节，专门用于路径项处理流程。
"""

from ....models import (
    FileItemResult,
    PathEntryContext,
    PathEntryInfo,
    PathEntryType,
    ProcessorResult,
    ProcessorStatus,
)


def create_initial_context(item_info: PathEntryInfo) -> PathEntryContext:
    """创建初始处理上下文

    将字符串类型的 item_type 转换为枚举类型，构建 PathEntryContext 对象。
    这是 pipeline 处理流程中的内部步骤，用于统一路径项的处理上下文。

    设计意图：
    - 统一上下文创建逻辑，避免重复代码
    - 确保 item_type 类型转换的一致性

    Args:
        item_info: 路径项信息

    Returns:
        初始化的处理上下文
    """
    # 将字符串类型的 item_type 转换为枚举类型
    item_type_enum = PathEntryType(item_info.item_type)
    return PathEntryContext.model_construct(
        item_info=item_info, item_type=item_type_enum
    )


def extract_error_message(
    processor_results: list[ProcessorResult],
) -> str | None:
    """从处理器结果中提取错误消息

    从处理器结果列表中提取第一个错误消息，用于错误结果构建。
    专门用于 pipeline 的错误处理流程。

    设计意图：
    - 统一错误消息提取逻辑
    - 简化错误结果构建过程

    Args:
        processor_results: 处理器结果列表

    Returns:
        错误消息，如果没有错误则返回 None
    """
    return next(
        (r.message for r in processor_results if r.status == ProcessorStatus.ERROR),
        None,
    )


def create_error_result(item_info: PathEntryInfo, error: Exception) -> FileItemResult:
    """创建错误结果对象

    创建错误结果对象，用于异常情况下的结果记录和持久化。
    pipeline 特定的错误结果构建逻辑，确保错误信息能够正确保存到数据库。

    设计意图：
    - 统一错误结果构建逻辑
    - 确保错误信息能够正确记录和持久化

    Args:
        item_info: 路径项信息
        error: 异常对象

    Returns:
        错误文件结果
    """
    return FileItemResult(
        item_info=item_info,
        context=create_initial_context(item_info),
        success=False,
        error_message=str(error),
        total_duration_ms=0.0,
    )
