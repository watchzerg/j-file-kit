"""文件任务 API 路由注册表。

各子模块各自持有完整的 prefix=/api/tasks，此处汇总供 app.py 统一注册。
"""

from fastapi import APIRouter

from j_file_kit.app.file_task.api import logs, results, runs

routers: tuple[APIRouter, ...] = (runs.router, results.router, logs.router)
