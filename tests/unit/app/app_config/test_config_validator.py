"""配置验证工具函数单元测试

测试 app_config/service/config_validator.py 中的所有函数，包括配置验证和目录冲突检查。
"""

from pathlib import Path

import pytest

from j_file_kit.app.app_config.domain import GlobalConfig
from j_file_kit.app.app_config.service.config_validator import (
    check_dir_conflicts,
    validate_global_config,
    validate_inbox_dir,
)


def create_global_config(
    inbox_dir: Path | None = None,
    sorted_dir: Path | None = None,
    unsorted_dir: Path | None = None,
    archive_dir: Path | None = None,
    misc_dir: Path | None = None,
    starred_dir: Path | None = None,
) -> GlobalConfig:
    """创建 GlobalConfig 测试对象

    Args:
        inbox_dir: 待处理目录
        sorted_dir: 已整理目录
        unsorted_dir: 未整理目录
        archive_dir: 归档目录
        misc_dir: 杂项目录
        starred_dir: 精选目录

    Returns:
        GlobalConfig 对象
    """
    return GlobalConfig(
        inbox_dir=inbox_dir,
        sorted_dir=sorted_dir,
        unsorted_dir=unsorted_dir,
        archive_dir=archive_dir,
        misc_dir=misc_dir,
        starred_dir=starred_dir,
    )


@pytest.mark.unit
class TestValidateInboxDir:
    """测试 validate_inbox_dir 函数"""

    def test_inbox_dir_set(self) -> None:
        """测试 inbox_dir 已设置的情况"""
        config = create_global_config(inbox_dir=Path("/tmp/inbox"))  # noqa: S108
        errors = validate_inbox_dir(config)
        assert errors == []

    def test_inbox_dir_not_set(self) -> None:
        """测试 inbox_dir 未设置的情况"""
        config = create_global_config(inbox_dir=None)
        errors = validate_inbox_dir(config)
        assert len(errors) == 1
        assert "待处理目录（inbox_dir）未设置" in errors[0]

    def test_inbox_dir_none_with_other_dirs_set(self) -> None:
        """测试 inbox_dir 为 None 但其他目录已设置的情况"""
        config = create_global_config(
            inbox_dir=None,
            sorted_dir=Path("/tmp/sorted"),  # noqa: S108
            unsorted_dir=Path("/tmp/unsorted"),  # noqa: S108
        )
        errors = validate_inbox_dir(config)
        assert len(errors) == 1
        assert "待处理目录（inbox_dir）未设置" in errors[0]


@pytest.mark.unit
class TestCheckDirConflicts:
    """测试 check_dir_conflicts 函数"""

    def test_no_conflicts(self) -> None:
        """测试无冲突的正常情况"""
        config = create_global_config(
            inbox_dir=Path("/tmp/inbox"),  # noqa: S108
            sorted_dir=Path("/tmp/sorted"),  # noqa: S108
            unsorted_dir=Path("/tmp/unsorted"),  # noqa: S108
            archive_dir=Path("/tmp/archive"),  # noqa: S108
        )
        errors = check_dir_conflicts(config)
        assert errors == []

    def test_same_path_conflict(self) -> None:
        """测试多个目录指向同一路径"""
        same_path = Path("/tmp/shared")  # noqa: S108
        config = create_global_config(
            inbox_dir=same_path,
            sorted_dir=same_path,
            unsorted_dir=Path("/tmp/unsorted"),  # noqa: S108
        )
        errors = check_dir_conflicts(config)
        assert len(errors) == 1
        assert "目录路径冲突" in errors[0]
        assert "inbox_dir" in errors[0]
        assert "sorted_dir" in errors[0]
        assert str(same_path) in errors[0]

    def test_three_dirs_same_path(self) -> None:
        """测试三个目录指向同一路径"""
        same_path = Path("/tmp/shared")  # noqa: S108
        config = create_global_config(
            inbox_dir=same_path,
            sorted_dir=same_path,
            unsorted_dir=same_path,
        )
        errors = check_dir_conflicts(config)
        assert len(errors) == 1
        assert "目录路径冲突" in errors[0]
        assert "inbox_dir" in errors[0]
        assert "sorted_dir" in errors[0]
        assert "unsorted_dir" in errors[0]

    def test_parent_child_relationship(self) -> None:
        """测试目录之间存在父子关系"""
        parent = Path("/tmp/parent")  # noqa: S108
        child = Path("/tmp/parent/child")  # noqa: S108
        config = create_global_config(
            inbox_dir=parent,
            sorted_dir=child,
        )
        errors = check_dir_conflicts(config)
        assert len(errors) == 1
        assert "目录路径冲突" in errors[0]
        assert "inbox_dir" in errors[0]
        assert "sorted_dir" in errors[0]
        assert "父目录" in errors[0]

    def test_reverse_parent_child_relationship(self) -> None:
        """测试反向父子关系（child 在前，parent 在后）"""
        parent = Path("/tmp/parent")  # noqa: S108
        child = Path("/tmp/parent/child")  # noqa: S108
        config = create_global_config(
            inbox_dir=child,
            sorted_dir=parent,
        )
        errors = check_dir_conflicts(config)
        assert len(errors) == 1
        assert "目录路径冲突" in errors[0]
        assert "sorted_dir" in errors[0]
        assert "inbox_dir" in errors[0]
        assert "父目录" in errors[0]

    def test_nested_parent_child_relationship(self) -> None:
        """测试多级嵌套的父子关系"""
        grandparent = Path("/tmp/grandparent")  # noqa: S108
        parent = Path("/tmp/grandparent/parent")  # noqa: S108
        child = Path("/tmp/grandparent/parent/child")  # noqa: S108
        config = create_global_config(
            inbox_dir=grandparent,
            sorted_dir=parent,
            unsorted_dir=child,
        )
        errors = check_dir_conflicts(config)
        assert len(errors) >= 2  # 至少有两个冲突
        error_messages = " ".join(errors)
        assert "grandparent" in error_messages or "inbox_dir" in error_messages
        assert "parent" in error_messages or "sorted_dir" in error_messages
        assert "child" in error_messages or "unsorted_dir" in error_messages

    def test_multiple_conflicts(self) -> None:
        """测试多种冲突同时存在"""
        same_path = Path("/tmp/shared")  # noqa: S108
        parent = Path("/tmp/parent")  # noqa: S108
        child = Path("/tmp/parent/child")  # noqa: S108
        config = create_global_config(
            inbox_dir=same_path,
            sorted_dir=same_path,  # 同一路径冲突
            unsorted_dir=parent,
            archive_dir=child,  # 父子关系冲突
        )
        errors = check_dir_conflicts(config)
        assert len(errors) >= 2  # 至少有两个冲突

    def test_all_none(self) -> None:
        """测试所有目录都为 None"""
        config = create_global_config()
        errors = check_dir_conflicts(config)
        assert errors == []

    def test_some_none(self) -> None:
        """测试部分目录为 None"""
        config = create_global_config(
            inbox_dir=Path("/tmp/inbox"),  # noqa: S108
            sorted_dir=None,
            unsorted_dir=Path("/tmp/unsorted"),  # noqa: S108
        )
        errors = check_dir_conflicts(config)
        assert errors == []

    def test_relative_paths(self) -> None:
        """测试相对路径（应通过 resolve 转换为绝对路径后比较）"""
        # 使用相对路径，resolve 后会转换为绝对路径
        config = create_global_config(
            inbox_dir=Path("./inbox"),
            sorted_dir=Path("./sorted"),
        )
        errors = check_dir_conflicts(config)
        # 相对路径在 resolve 后应该不会冲突（除非它们指向同一位置）
        # 这里主要测试函数不会因为相对路径而崩溃
        assert isinstance(errors, list)

    def test_symlink_handling(self, tmp_path: Path) -> None:
        """测试符号链接处理（resolve 会解析符号链接）"""
        # 创建实际目录
        real_dir = tmp_path / "real"
        real_dir.mkdir()

        # 创建符号链接指向同一目录
        link1 = tmp_path / "link1"
        link2 = tmp_path / "link2"
        try:
            link1.symlink_to(real_dir)
            link2.symlink_to(real_dir)

            config = create_global_config(
                inbox_dir=link1,
                sorted_dir=link2,
            )
            errors = check_dir_conflicts(config)
            # resolve 会解析符号链接，应该检测到冲突
            assert len(errors) == 1
            assert "目录路径冲突" in errors[0]
        except OSError:
            # 如果系统不支持符号链接（如某些 Windows 环境），跳过测试
            pytest.skip("系统不支持符号链接")


@pytest.mark.unit
class TestValidateGlobalConfig:
    """测试 validate_global_config 函数"""

    def test_valid_config(self) -> None:
        """测试有效配置"""
        config = create_global_config(
            inbox_dir=Path("/tmp/inbox"),  # noqa: S108
            sorted_dir=Path("/tmp/sorted"),  # noqa: S108
            unsorted_dir=Path("/tmp/unsorted"),  # noqa: S108
        )
        errors = validate_global_config(config)
        assert errors == []

    def test_missing_inbox_dir(self) -> None:
        """测试缺少 inbox_dir"""
        config = create_global_config(
            inbox_dir=None,
            sorted_dir=Path("/tmp/sorted"),  # noqa: S108
        )
        errors = validate_global_config(config)
        assert len(errors) == 1
        assert "待处理目录（inbox_dir）未设置" in errors[0]

    def test_dir_conflicts(self) -> None:
        """测试目录冲突"""
        same_path = Path("/tmp/shared")  # noqa: S108
        config = create_global_config(
            inbox_dir=same_path,
            sorted_dir=same_path,
        )
        errors = validate_global_config(config)
        assert len(errors) == 1
        assert "目录路径冲突" in errors[0]

    def test_multiple_errors(self) -> None:
        """测试多个错误同时存在"""
        same_path = Path("/tmp/shared")  # noqa: S108
        config = create_global_config(
            inbox_dir=None,  # 缺少必需字段
            sorted_dir=same_path,
            unsorted_dir=same_path,  # 目录冲突
        )
        errors = validate_global_config(config)
        assert len(errors) >= 2
        error_messages = " ".join(errors)
        assert "待处理目录（inbox_dir）未设置" in error_messages
        assert "目录路径冲突" in error_messages

    def test_all_none_except_inbox(self) -> None:
        """测试只有 inbox_dir 设置，其他都为 None"""
        config = create_global_config(
            inbox_dir=Path("/tmp/inbox"),  # noqa: S108
            sorted_dir=None,
            unsorted_dir=None,
            archive_dir=None,
            misc_dir=None,
            starred_dir=None,
        )
        errors = validate_global_config(config)
        assert errors == []

    def test_empty_config(self) -> None:
        """测试空配置（所有字段为 None）"""
        config = create_global_config()
        errors = validate_global_config(config)
        assert len(errors) == 1
        assert "待处理目录（inbox_dir）未设置" in errors[0]
