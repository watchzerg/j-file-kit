"""接口层

定义所有协议和抽象接口，包括处理器协议和任务协议。

组织方式：
- 根目录包含抽象接口（processors/, task.py, repositories.py），使用通用的 item 概念，不依赖特定领域
- 领域专用接口位于子目录下（如 interfaces/file/），包含特定领域的协议定义
- 这种组织方式与 services 层的领域组织保持一致，便于理解和维护
"""
