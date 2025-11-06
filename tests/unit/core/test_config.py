"""配置模型单元测试

测试配置模型的验证和解析。
"""

import pytest
from pathlib import Path
import tempfile
import yaml

from jfk.core.config import (
    GlobalConfig, FileOrganizeConfig, TaskDefinition, TaskConfig,
    load_config, save_config, create_default_config
)


class TestGlobalConfig:
    """测试 GlobalConfig 模型"""
    
    def test_global_config_creation(self):
        """测试 GlobalConfig 创建"""
        config = GlobalConfig(scan_roots=[Path("/test")])
        
        assert config.scan_roots == [Path("/test")]
        assert config.scan_root == Path("/test")  # 向后兼容
        assert config.log_dir == Path("./logs")
        assert config.report_dir == Path("./reports")
    
    def test_global_config_multiple_scan_roots(self):
        """测试多个扫描根目录"""
        config = GlobalConfig(scan_roots=[Path("/test1"), Path("/test2"), Path("/test3")])
        
        assert len(config.scan_roots) == 3
        assert config.scan_roots[0] == Path("/test1")
        assert config.scan_roots[1] == Path("/test2")
        assert config.scan_roots[2] == Path("/test3")
        assert config.scan_root == Path("/test1")  # 向后兼容
    
    def test_global_config_custom_paths(self):
        """测试自定义路径"""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = GlobalConfig(
                scan_roots=[Path("/test")],
                log_dir=Path(tmp_dir) / "logs",
                report_dir=Path(tmp_dir) / "reports"
            )
            
            assert config.log_dir == Path(tmp_dir) / "logs"
            assert config.report_dir == Path(tmp_dir) / "reports"
    
    def test_global_config_validation(self):
        """测试 GlobalConfig 验证"""
        # 测试空列表（在非测试环境中会失败）
        import os
        original_env = os.environ.get("PYTEST_CURRENT_TEST")
        try:
            # 模拟非测试环境
            if "PYTEST_CURRENT_TEST" in os.environ:
                del os.environ["PYTEST_CURRENT_TEST"]
            
            with pytest.raises(ValueError):
                GlobalConfig(scan_roots=[])
        finally:
            # 恢复环境
            if original_env:
                os.environ["PYTEST_CURRENT_TEST"] = original_env


class TestFileOrganizeConfig:
    """测试 FileOrganizeConfig 模型"""
    
    def test_file_organize_config_creation(self):
        """测试 FileOrganizeConfig 创建"""
        config = FileOrganizeConfig(
            todo_non_vidpic_dir=Path("/todo/non-vidpic"),
            todo_vidpic_dir=Path("/todo/vidpic"),
            video_extensions={".mp4", ".avi"},
            image_extensions={".jpg", ".png"}
        )
        
        assert config.todo_non_vidpic_dir == Path("/todo/non-vidpic")
        assert config.todo_vidpic_dir == Path("/todo/vidpic")
        assert config.video_extensions == {".mp4", ".avi"}
        assert config.image_extensions == {".jpg", ".png"}
    
    def test_file_organize_config_extension_validation(self):
        """测试扩展名验证"""
        config = FileOrganizeConfig(
            todo_non_vidpic_dir=Path("/todo/non-vidpic"),
            todo_vidpic_dir=Path("/todo/vidpic"),
            video_extensions={"mp4", "avi"},  # 没有点号
            image_extensions={"jpg", "png"}   # 没有点号
        )
        
        # 应该自动添加点号
        assert config.video_extensions == {".mp4", ".avi"}
        assert config.image_extensions == {".jpg", ".png"}


class TestTaskDefinition:
    """测试 TaskDefinition 模型"""
    
    def test_task_definition_creation(self):
        """测试 TaskDefinition 创建"""
        task = TaskDefinition(
            name="test_task",
            type="file_organize",
            enabled=True,
            config={"key": "value"}
        )
        
        assert task.name == "test_task"
        assert task.type == "file_organize"
        assert task.enabled is True
        assert task.config == {"key": "value"}
    
    def test_task_definition_defaults(self):
        """测试 TaskDefinition 默认值"""
        task = TaskDefinition(
            name="test_task",
            type="file_organize",
            config={}
        )
        
        assert task.enabled is True
    
    def test_task_definition_get_config(self):
        """测试获取类型化配置"""
        from jfk.core.config import FileOrganizeConfig
        
        task = TaskDefinition(
            name="test_task",
            type="file_organize",
            config={
                "todo_non_vidpic_dir": "/todo/non-vidpic",
                "todo_vidpic_dir": "/todo/vidpic",
                "video_extensions": [".mp4", ".avi"],
                "image_extensions": [".jpg", ".png"]
            }
        )
        
        # 使用具体的配置类型
        config = task.get_config(FileOrganizeConfig)
        assert isinstance(config, FileOrganizeConfig)
        assert config.todo_non_vidpic_dir == Path("/todo/non-vidpic")


class TestTaskConfig:
    """测试 TaskConfig 模型"""
    
    def test_task_config_creation(self):
        """测试 TaskConfig 创建"""
        global_config = GlobalConfig(scan_roots=[Path("/test")])
        task = TaskDefinition(
            name="test_task",
            type="file_organize",
            config={}
        )
        
        config = TaskConfig(
            global_=global_config,
            tasks=[task]
        )
        
        assert config.global_ == global_config
        assert config.tasks == [task]
    
    def test_task_config_enabled_tasks(self):
        """测试获取启用的任务"""
        global_config = GlobalConfig(scan_roots=[Path("/test")])
        
        enabled_task = TaskDefinition(
            name="enabled_task",
            type="file_organize",
            enabled=True,
            config={}
        )
        
        disabled_task = TaskDefinition(
            name="disabled_task",
            type="file_organize",
            enabled=False,
            config={}
        )
        
        config = TaskConfig(
            global_=global_config,
            tasks=[enabled_task, disabled_task]
        )
        
        enabled_tasks = config.enabled_tasks
        assert len(enabled_tasks) == 1
        assert enabled_tasks[0].name == "enabled_task"
    
    def test_task_config_get_task(self):
        """测试根据名称获取任务"""
        global_config = GlobalConfig(scan_roots=[Path("/test")])
        
        task1 = TaskDefinition(
            name="task1",
            type="file_organize",
            config={}
        )
        
        task2 = TaskDefinition(
            name="task2",
            type="file_organize",
            config={}
        )
        
        config = TaskConfig(
            global_=global_config,
            tasks=[task1, task2]
        )
        
        # 测试获取存在的任务
        found_task = config.get_task("task1")
        assert found_task == task1
        
        # 测试获取不存在的任务
        not_found = config.get_task("nonexistent")
        assert not_found is None


class TestConfigIO:
    """测试配置文件 I/O"""
    
    def test_load_config(self):
        """测试加载配置文件"""
        # 创建临时配置文件
        config_data = {
            "global": {
                "scan_roots": ["/test/scan1", "/test/scan2"],
                "log_dir": "./logs",
                "report_dir": "./reports"
            },
            "tasks": [
                {
                    "name": "test_task",
                    "type": "file_organize",
                    "enabled": True,
                    "config": {
                        "todo_non_vidpic_dir": "/todo/non-vidpic",
                        "todo_vidpic_dir": "/todo/vidpic",
                        "video_extensions": [".mp4", ".avi"],
                        "image_extensions": [".jpg", ".png"]
                    }
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            config = load_config(config_path)
            
            assert len(config.global_.scan_roots) == 2
            assert config.global_.scan_roots[0] == Path("/test/scan1")
            assert config.global_.scan_roots[1] == Path("/test/scan2")
            assert config.global_.scan_root == Path("/test/scan1")  # 向后兼容
            assert config.global_.log_dir == Path("./logs")
            assert config.global_.report_dir == Path("./reports")
            assert len(config.tasks) == 1
            assert config.tasks[0].name == "test_task"
            
        finally:
            Path(config_path).unlink()
    
    def test_save_config(self):
        """测试保存配置文件"""
        config = create_default_config()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_path = f.name
        
        try:
            save_config(config, config_path)
            
            # 验证文件被创建
            assert Path(config_path).exists()
            
            # 验证可以重新加载
            loaded_config = load_config(config_path)
            assert loaded_config.global_.scan_roots == config.global_.scan_roots
            assert loaded_config.global_.scan_root == config.global_.scan_root  # 向后兼容
            
        finally:
            Path(config_path).unlink()
    
    def test_create_default_config(self):
        """测试创建默认配置"""
        config = create_default_config()
        
        assert len(config.global_.scan_roots) == 1
        assert config.global_.scan_roots[0] == Path("/path/to/scan")
        assert config.global_.scan_root == Path("/path/to/scan")  # 向后兼容
        assert config.global_.log_dir == Path("./logs")
        assert config.global_.report_dir == Path("./reports")
        assert len(config.tasks) == 1
        assert config.tasks[0].name == "video_file_organizer"
        assert config.tasks[0].type == "file_organize"
        assert config.tasks[0].enabled is True
    
    def test_load_config_file_not_found(self):
        """测试加载不存在的配置文件"""
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/config.yaml")
    
    def test_load_config_invalid_yaml(self):
        """测试加载无效的 YAML 文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            config_path = f.name
        
        try:
            with pytest.raises(yaml.YAMLError):
                load_config(config_path)
        finally:
            Path(config_path).unlink()
    
    def test_load_config_validation_error(self):
        """测试配置验证错误"""
        # 创建无效的配置文件
        config_data = {
            "global": {
                "scan_roots": [],  # 空列表，无效
                "log_dir": "./logs",
                "report_dir": "./reports"
            },
            "tasks": []
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            import os
            original_env = os.environ.get("PYTEST_CURRENT_TEST")
            try:
                # 模拟非测试环境
                if "PYTEST_CURRENT_TEST" in os.environ:
                    del os.environ["PYTEST_CURRENT_TEST"]
                
                with pytest.raises(ValueError):
                    load_config(config_path)
            finally:
                # 恢复环境
                if original_env:
                    os.environ["PYTEST_CURRENT_TEST"] = original_env
        finally:
            Path(config_path).unlink()
