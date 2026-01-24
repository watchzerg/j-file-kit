"""j-file-kit: 基于 Python 的文件管理工具

一个灵活的文件管理工具，支持自定义规则的文件操作。
采用分层架构设计，使用管道/过滤器模式，支持文件分类、重命名、移动等操作。

架构分层：
- models/: 数据模型层（领域模型）
- interfaces/: 接口层（协议定义）
- services/: 服务层（业务编排）
- infrastructure/: 基础设施层（I/O操作）
- api/: HTTP接口层
- utils/: 工具函数
"""
