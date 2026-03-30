"""项目级系统常量。

定义与 Docker 部署环境相关的系统级常量，供各业务域共用。
"""

from pathlib import Path

# 容器内媒体挂载根目录，所有媒体路径必须在此目录下
MEDIA_ROOT = Path("/media")
