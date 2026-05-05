"""Raw 收件箱整理管道包。

职责按阶段与共享组件拆分：
- `pipeline.py`: 三阶段编排入口
- `phase1.py` / `phase3.py`: 单文件阶段实现
- `phase2.py`: 阶段 2 编排入口；规则在 `phase2_preflight.py`、`phase2_delete_move.py`、
  `phase2_clean.py`、`phase2_collapse.py`、`phase2_classify.py`
- `context.py` / `counters.py`: 阶段共享上下文与计数
- `keywords.py`: 关键字策略

业务符号建议按子模块显式导入，避免包级隐式 re-export。
"""
