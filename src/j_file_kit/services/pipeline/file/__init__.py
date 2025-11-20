"""文件处理管道实现

文件处理管道（流程协调层），协调文件处理流程：扫描 → 分析 → 执行 → 终结。
主要处理文件，目录清理是辅助功能。
"""

from .pipeline import FilePipeline
