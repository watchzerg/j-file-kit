## 任务目标
根据最新代码现状，更新并优化项目文档（`README.md`、`docs/ARCHITECTURE.md`、`docs/JAV_VIDEO_PROCESSING_PIPELINE.md`、`docs/RAW_FILE_PROCESSING_PIPELINE.md`），使其准确反映当前架构与核心流程。

## 文档更新原则

1. **描述现状**：只写「现在是什么 / 为什么这样设计」，不做增量式变更记录，不重复代码注释已有的步骤细节。
2. **代码链接替代代码片段**：关键模块和说明处直接链接源码文件，不粘贴代码。
3. **宏观优先**：让用户快速理解整体设计；让 AI 快速定位「改 X 该找哪个文件」。
4. **主从关系**：`ARCHITECTURE.md` 是入口，两个 pipeline 文档是专项补充，均须反向链接到 `ARCHITECTURE.md`。

## 执行步骤

1. **阅读现有文档**（`README.md`、三份 `docs/*.md`）与关键源码（目录结构、各模块 docstring），了解文档与代码现状的差距。
2. **识别需更新的内容**，重点检查：
   - 目录结构、模块职责是否与源码一致
   - 是否有代码级细节（常量列表、硬编码枚举值等）应改为链接
   - 是否有新模块/新机制未被文档覆盖
   - 三文档的交叉链接是否完整
3. **按顺序更新**：先 `ARCHITECTURE.md`，再两份 pipeline 文档，最后 `README.md`。
4. **执行 `just pre-commit` 并确保通过**。

## 输出质量标准

- `README.md`：项目定位 + 主业务管线一句话 + 快速上手命令 + 部署说明；不罗列业务子目录细节。
- `ARCHITECTURE.md`：分层依赖、目录结构、任务执行全链路（含双管线流程图）、核心类型速查、AI 快速定位表；Section 保持精简，避免重复 docstring。
- 两份 pipeline 文档：mermaid 总览图 + 各阶段/步骤的「触发条件、决策、计数」；常量/关键字列表改为链接 `organizer_defaults.py`；末尾有 `ARCHITECTURE.md` 反向链接。
