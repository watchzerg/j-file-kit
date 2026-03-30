"""Media browser API 测试。

覆盖两类测试：
- 单元测试：直接调用纯函数 list_subdirectories，无需启动 HTTP 服务。
- 集成测试：通过 TestClient + monkeypatch 测试 GET /api/media/directories 端点。
"""

from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import j_file_kit.app.media_browser.api as media_browser_api
from j_file_kit.api.app import create_app
from j_file_kit.app.media_browser.api import list_subdirectories

# ── 单元测试 ───────────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestListSubdirectoriesFunction:
    """list_subdirectories 纯函数的单元测试。

    全部使用 tmp_path 作为 media_root，无需访问真实 /media。
    """

    def test_returns_immediate_children_only(self, tmp_path: Path) -> None:
        """只返回一级子目录，不递归展开"""
        (tmp_path / "a").mkdir()
        (tmp_path / "b").mkdir()
        (tmp_path / "a" / "nested").mkdir()

        result = list_subdirectories(tmp_path, media_root=tmp_path)

        assert result.path == str(tmp_path)
        assert [c.name for c in result.children] == ["a", "b"]

    def test_nested_dirs_not_included(self, tmp_path: Path) -> None:
        """嵌套目录不出现在结果中"""
        (tmp_path / "parent").mkdir()
        (tmp_path / "parent" / "child").mkdir()

        result = list_subdirectories(tmp_path, media_root=tmp_path)

        names = [c.name for c in result.children]
        assert "child" not in names
        assert "parent" in names

    def test_empty_dir_returns_empty_children(self, tmp_path: Path) -> None:
        """空目录返回空列表"""
        result = list_subdirectories(tmp_path, media_root=tmp_path)

        assert result.children == []

    def test_sorted_by_name(self, tmp_path: Path) -> None:
        """子目录按名称字典序排序"""
        for name in ("zebra", "apple", "mango"):
            (tmp_path / name).mkdir()

        result = list_subdirectories(tmp_path, media_root=tmp_path)

        assert [c.name for c in result.children] == ["apple", "mango", "zebra"]

    def test_files_excluded(self, tmp_path: Path) -> None:
        """普通文件不出现在结果中"""
        (tmp_path / "subdir").mkdir()
        (tmp_path / "file.txt").write_text("hello")

        result = list_subdirectories(tmp_path, media_root=tmp_path)

        assert len(result.children) == 1
        assert result.children[0].name == "subdir"

    def test_path_outside_media_root_raises(self, tmp_path: Path) -> None:
        """路径不在 media_root 下时抛出 ValueError"""
        outside = tmp_path.parent

        with pytest.raises(ValueError, match="不在允许的根目录"):
            list_subdirectories(outside, media_root=tmp_path)

    def test_path_not_exist_raises(self, tmp_path: Path) -> None:
        """路径不存在时抛出 ValueError"""
        nonexistent = tmp_path / "no_such_dir"

        with pytest.raises(ValueError, match="路径不存在"):
            list_subdirectories(nonexistent, media_root=tmp_path)

    def test_path_is_file_raises(self, tmp_path: Path) -> None:
        """路径是文件时抛出 ValueError"""
        file_path = tmp_path / "a_file.txt"
        file_path.write_text("content")

        with pytest.raises(ValueError, match="路径不是目录"):
            list_subdirectories(file_path, media_root=tmp_path)

    def test_children_path_is_absolute(self, tmp_path: Path) -> None:
        """返回的 children 中每项 path 均为绝对路径字符串"""
        (tmp_path / "sub").mkdir()

        result = list_subdirectories(tmp_path, media_root=tmp_path)

        assert result.children[0].path == str(tmp_path / "sub")


# ── 集成测试 ───────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestListDirectoriesEndpoint:
    """GET /api/media/directories 端点集成测试。

    通过 monkeypatch 将 MEDIA_ROOT 替换为 tmp_path，
    再用 TestClient 发起 HTTP 请求验证端点行为。
    """

    @pytest.fixture
    def media_root(self, tmp_path: Path) -> Path:
        """在 tmp_path 下创建模拟 media 根目录"""
        root = tmp_path / "media"
        root.mkdir()
        return root

    @pytest.fixture
    def client(
        self,
        tmp_path: Path,
        media_root: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> Generator[TestClient]:
        """创建 TestClient，并将 MEDIA_ROOT 指向 media_root"""
        monkeypatch.setattr(media_browser_api, "MEDIA_ROOT", media_root)
        app = create_app(base_dir=tmp_path)
        with TestClient(app) as c:
            yield c

    def test_default_path_uses_media_root(
        self,
        client: TestClient,
        media_root: Path,
    ) -> None:
        """不传 path 时，默认使用 monkeypatched MEDIA_ROOT"""
        (media_root / "inbox").mkdir()

        response = client.get("/api/media/directories")

        assert response.status_code == 200
        data = response.json()
        assert data["path"] == str(media_root)
        assert any(c["name"] == "inbox" for c in data["children"])

    def test_explicit_valid_path(
        self,
        client: TestClient,
        media_root: Path,
    ) -> None:
        """传入合法子路径时正常返回子目录列表"""
        sub = media_root / "inbox"
        sub.mkdir()
        (sub / "movies").mkdir()
        (sub / "series").mkdir()

        response = client.get(f"/api/media/directories?path={sub}")

        assert response.status_code == 200
        data = response.json()
        names = [c["name"] for c in data["children"]]
        assert names == ["movies", "series"]

    def test_path_outside_media_root_400(
        self,
        client: TestClient,
        media_root: Path,
    ) -> None:
        """路径不在 MEDIA_ROOT 下时返回 400 INVALID_PATH"""
        outside = media_root.parent

        response = client.get(f"/api/media/directories?path={outside}")

        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "INVALID_PATH"

    def test_nonexistent_path_400(
        self,
        client: TestClient,
        media_root: Path,
    ) -> None:
        """路径不存在时返回 400 INVALID_PATH"""
        nonexistent = media_root / "no_such_dir"

        response = client.get(f"/api/media/directories?path={nonexistent}")

        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "INVALID_PATH"

    def test_path_is_file_400(
        self,
        client: TestClient,
        media_root: Path,
    ) -> None:
        """路径是文件时返回 400 INVALID_PATH"""
        file_path = media_root / "not_a_dir.txt"
        file_path.write_text("content")

        response = client.get(f"/api/media/directories?path={file_path}")

        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "INVALID_PATH"
