"""结果路由：分页列出执行实例的文件处理结果。"""

from fastapi import APIRouter, HTTPException, Query, Request, status

from j_file_kit.api.app_state import AppState
from j_file_kit.app.file_task.api._helpers import _parse_run_id
from j_file_kit.app.file_task.application.schemas import (
    FileTaskRunResultItem,
    FileTaskRunResultsResponse,
)

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

VALID_DECISION_TYPES = {"move", "delete", "skip"}


def _parse_decision_type_filter(decision_type: str | None) -> str | None:
    if decision_type is None:
        return None
    if decision_type in VALID_DECISION_TYPES:
        return decision_type
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"无效的处理决策类型: {decision_type}",
    )


@router.get("/{run_id}/results", response_model=FileTaskRunResultsResponse)
async def list_run_results(
    run_id: str,
    request: Request,
    decision_type: str | None = Query(None),
    success: bool | None = Query(None),
    q: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> FileTaskRunResultsResponse:
    """分页列出执行实例的文件处理结果。"""
    app_state: AppState = request.app.state.app_state
    run_id_int = _parse_run_id(run_id)
    app_state.file_task_run_manager.get_run(run_id_int)
    parsed_decision_type = _parse_decision_type_filter(decision_type)
    normalized_q = q.strip() if q else None
    offset = (page - 1) * page_size

    result_rows = app_state.file_result_repository.list_results(
        run_id=run_id_int,
        decision_type=parsed_decision_type,
        success=success,
        q=normalized_q,
        limit=page_size,
        offset=offset,
    )
    total = app_state.file_result_repository.count_results(
        run_id=run_id_int,
        decision_type=parsed_decision_type,
        success=success,
        q=normalized_q,
    )

    return FileTaskRunResultsResponse(
        results=[FileTaskRunResultItem.model_validate(row) for row in result_rows],
        total=total,
        page=page,
        page_size=page_size,
    )
