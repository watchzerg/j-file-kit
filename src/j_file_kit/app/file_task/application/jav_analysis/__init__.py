"""JAV 收件箱单文件分析（纯函数）。

`runner.py` 负责分析编排；`classify` / `inbox` / `misc` / `archive` / `media`
分别承载分类、预删、杂项、压缩包、媒体文件规则域逻辑。

业务符号请从子模块显式导入，例如 ``jav_analysis.runner.analyze_jav_file``；
本包 ``__init__`` 不聚合导出，避免隐式 re-export。
"""
