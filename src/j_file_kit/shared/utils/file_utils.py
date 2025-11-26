"""文件工具函数

提供文件操作相关的纯函数工具。
不包含I/O操作，所有文件系统操作应使用infrastructure/filesystem/operations。
不包含业务逻辑，所有函数都是通用的文件工具函数。

注意：文件任务相关的工具函数（如 generate_alternative_filename）已迁移到
app/file_task/utils.py，属于 file_task domain 的业务逻辑。
"""
