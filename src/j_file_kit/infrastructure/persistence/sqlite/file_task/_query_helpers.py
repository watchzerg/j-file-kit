"""file_task_runs 表的 SQL 查询构建辅助

该模块集中管理 list/count 查询的 SQL 模板与过滤参数构建逻辑，与
FileTaskRunRepositoryImpl 中的 CRUD 方法保持分离，便于独立测试和扩展。
"""

from typing import Literal

from j_file_kit.app.file_task.domain.task_run import FileTaskRunStatus

# 用于索引 LIST_RUN_QUERIES / COUNT_RUN_QUERIES 的过滤组合键
RunListFilterKey = Literal["all", "task_type", "status", "task_type_status"]

# list_runs 使用的带过滤条件 SQL 模板，参数顺序与 build_list_filters 返回值一致，
# 末尾两个占位符固定为 LIMIT、OFFSET
LIST_RUN_QUERIES: dict[RunListFilterKey, str] = {
    "all": """
        SELECT * FROM file_task_runs
        ORDER BY start_time DESC
        LIMIT ? OFFSET ?
    """,
    "task_type": """
        SELECT * FROM file_task_runs
        WHERE task_type = ?
        ORDER BY start_time DESC
        LIMIT ? OFFSET ?
    """,
    "status": """
        SELECT * FROM file_task_runs
        WHERE status = ?
        ORDER BY start_time DESC
        LIMIT ? OFFSET ?
    """,
    "task_type_status": """
        SELECT * FROM file_task_runs
        WHERE task_type = ? AND status = ?
        ORDER BY start_time DESC
        LIMIT ? OFFSET ?
    """,
}

# count_runs 使用的带过滤条件 SQL 模板，参数顺序与 build_list_filters 返回值一致
COUNT_RUN_QUERIES: dict[RunListFilterKey, str] = {
    "all": "SELECT COUNT(*) AS total FROM file_task_runs",
    "task_type": """
        SELECT COUNT(*) AS total FROM file_task_runs
        WHERE task_type = ?
    """,
    "status": """
        SELECT COUNT(*) AS total FROM file_task_runs
        WHERE status = ?
    """,
    "task_type_status": """
        SELECT COUNT(*) AS total FROM file_task_runs
        WHERE task_type = ? AND status = ?
    """,
}


def build_list_filters(
    task_type: str | None,
    status: FileTaskRunStatus | None,
) -> tuple[RunListFilterKey, list[str]]:
    """根据过滤条件推导查询键与位置参数列表。

    返回的 (key, params) 用于从 LIST_RUN_QUERIES / COUNT_RUN_QUERIES 取出对应 SQL，
    并将 params 作为 WHERE 子句的绑定参数（不含 LIMIT/OFFSET）传入。

    Args:
        task_type: 任务类型过滤值，None 表示不过滤
        status: 执行状态过滤值，None 表示不过滤

    Returns:
        (filter_key, params) 元组；params 元素顺序与 SQL 占位符一一对应
    """
    params: list[str] = []

    if task_type is None and status is None:
        return "all", params
    if task_type is not None and status is None:
        params.append(task_type)
        return "task_type", params
    if task_type is None and status is not None:
        params.append(status.value)
        return "status", params
    if task_type is not None and status is not None:
        params.extend([task_type, status.value])
        return "task_type_status", params

    raise AssertionError("unreachable filter combination")
