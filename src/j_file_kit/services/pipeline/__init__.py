"""路径项处理管道

协调整个路径项（文件和目录）处理流程：扫描 → 分析 → 执行 → 终结。
负责路径项扫描、处理器链执行和结果汇总。
"""

from .core import PathEntryPipeline

__all__ = ["PathEntryPipeline"]
