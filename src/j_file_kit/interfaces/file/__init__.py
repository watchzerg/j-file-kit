"""file 领域接口

file 领域的专用接口定义。

组织方式：
- 与 services 层的领域组织方式保持一致
- 领域专用接口位于 interfaces/{domain}/ 目录下
- 抽象接口位于 interfaces/ 根目录下

此模块导出 file 领域的所有专用接口。
"""

from .repositories import FileItemRepository, FileProcessorRepository

__all__ = [
    "FileItemRepository",
    "FileProcessorRepository",
]
