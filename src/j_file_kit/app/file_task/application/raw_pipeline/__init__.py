"""Raw 收件箱整理管道包。

职责按阶段与共享组件拆分：
- `pipeline.py`: 三阶段编排入口
- `phase1.py` / `phase2.py` / `phase3.py`: 各阶段实现
- `context.py` / `counters.py`: 阶段共享上下文与计数
- `keywords.py`: 关键字策略

业务符号建议按子模块显式导入，避免包级隐式 re-export。
"""
