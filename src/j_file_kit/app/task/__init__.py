"""任务管理 domain

定义任务管理领域的核心模型、协议和 API：
- domain.py: 领域模型（TaskRecord, TaskReport）、枚举（TaskStatus, TaskType, TriggerType）、协议（TaskRunner）
- ports.py: TaskRepository 协议
- api.py: 通用任务 API（列表、查询、取消）
- schemas.py: API 请求/响应模型

TaskManager 位于 infrastructure/task/ 层。
"""
