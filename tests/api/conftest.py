"""API 集成测试 fixtures

提供 test_app、client fixtures，用于 API 层 HTTP 集成测试。
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from j_file_kit.api.app import create_app


@pytest.fixture
def test_app(tmp_path: Path):
    """创建使用临时目录的 FastAPI 应用实例"""
    return create_app(base_dir=tmp_path)


@pytest.fixture
def client(test_app):
    """TestClient 上下文管理器，确保 lifespan 正确启停"""
    with TestClient(test_app) as c:
        yield c
