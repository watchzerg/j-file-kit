"""主入口文件

启动HTTP服务，提供文件管理任务的RESTful API接口。
"""

from __future__ import annotations

import argparse

import uvicorn

from .api.app import app


def main() -> None:
    """主函数"""
    parser = argparse.ArgumentParser(description="j-file-kit HTTP服务")
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",  # noqa: S104
        help="监听地址（默认: 0.0.0.0）",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="监听端口（默认: 8000）",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="启用自动重载（开发模式）",
    )

    args = parser.parse_args()

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
