"""日志路由：分页列出执行实例的结构化日志。"""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import TypeGuard

from fastapi import APIRouter, Query, Request

from j_file_kit.api.app_state import AppState
from j_file_kit.app.file_task.api._helpers import _parse_run_id, _task_log_file_path
from j_file_kit.app.file_task.application.schemas import (
    FileTaskRunLogLine,
    FileTaskRunLogsResponse,
)

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def _is_string_key_mapping(value: object) -> TypeGuard[Mapping[str, object]]:
    return isinstance(value, Mapping) and all(
        isinstance(key, str) for key in value.keys()
    )


def _stringify_log_time(value: object) -> str | None:
    if _is_string_key_mapping(value):
        repr_value = value.get("repr")
        if repr_value is not None:
            return str(repr_value)
    if value is None:
        return None
    return str(value)


def _extract_log_level(value: object) -> str | None:
    if _is_string_key_mapping(value):
        name = value.get("name")
        if name is not None:
            return str(name)
    if value is None:
        return None
    return str(value)


def _parse_log_line(line_no: int, raw_line: str) -> FileTaskRunLogLine:
    try:
        payload = json.loads(raw_line)
    except json.JSONDecodeError:
        return FileTaskRunLogLine(
            line_no=line_no, ts=None, level=None, msg=raw_line, fields={}
        )

    if not _is_string_key_mapping(payload):
        return FileTaskRunLogLine(
            line_no=line_no, ts=None, level=None, msg=raw_line, fields={}
        )

    record = payload.get("record")
    if not _is_string_key_mapping(record):
        return FileTaskRunLogLine(
            line_no=line_no, ts=None, level=None, msg=raw_line, fields={}
        )

    level = record.get("level")
    time_value = record.get("time")
    extra = record.get("extra")
    return FileTaskRunLogLine(
        line_no=line_no,
        ts=_stringify_log_time(time_value),
        level=_extract_log_level(level),
        msg=str(record.get("message") or ""),
        fields=dict(extra) if _is_string_key_mapping(extra) else {},
    )


def _read_log_lines(
    log_file: Path,
    offset: int,
    limit: int,
) -> tuple[int, list[FileTaskRunLogLine]]:
    if not log_file.exists():
        return 0, []

    raw_lines = log_file.read_text(encoding="utf-8").splitlines()
    selected_lines = raw_lines[offset : offset + limit]
    lines = [
        _parse_log_line(line_no=offset + index + 1, raw_line=raw_line)
        for index, raw_line in enumerate(selected_lines)
    ]
    return len(raw_lines), lines


@router.get("/{run_id}/logs", response_model=FileTaskRunLogsResponse)
async def list_run_logs(
    run_id: str,
    request: Request,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> FileTaskRunLogsResponse:
    """分页列出执行实例日志。"""
    app_state: AppState = request.app.state.app_state
    run_id_int = _parse_run_id(run_id)
    run = app_state.file_task_run_manager.get_run(run_id_int)
    log_file = _task_log_file_path(app_state.log_dir, run)
    total_lines, lines = _read_log_lines(log_file, offset, limit)

    return FileTaskRunLogsResponse(
        total_lines=total_lines,
        offset=offset,
        limit=limit,
        lines=lines,
    )
