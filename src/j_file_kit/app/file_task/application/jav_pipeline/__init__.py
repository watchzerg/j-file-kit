"""JAV 收件箱扫描管线：编排、单文件处理、执行 Decision、观测与落库映射。

`pipeline.py` 专注扫描编排与生命周期；`item_processor.py` 负责单文件闭环；
`result_mapper.py` 负责结果映射；`observer.py` 负责日志与计数；
`directory_cleanup.py` 负责目录收缩；`executor.py` 负责 Decision 执行。

业务符号请从子模块显式导入（如 ``jav_pipeline.pipeline.FilePipeline``）；
本包 ``__init__`` 不聚合导出，避免隐式 re-export。
"""
