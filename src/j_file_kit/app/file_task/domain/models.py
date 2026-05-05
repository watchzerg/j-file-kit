"""文件任务领域模型

定义文件任务 domain 的全部核心模型：

文件相关：
- PathEntryType：路径项类型（文件/目录）
- FileType：文件类型（视频/图片/压缩包/其他）
- SerialId：番号值对象

任务执行实例（Run）：
- FileTaskRunStatus：执行状态枚举
- FileTaskTriggerType：触发类型枚举
- FileTaskError / FileTaskNotFoundError / FileTaskAlreadyRunningError / FileTaskCancelledError：领域异常
- FileTaskRunReport：执行汇总报告（含成功率、耗时等派生属性）
- FileTaskRunStatistics：执行统计快照（由 FileTaskRunner.run() 返回）
- FileTaskRun：执行实例持久化记录（对应数据库行）
- FileTaskRunner：任务执行器协议（定义 run() 接口，所有具体任务须实现）

任务配置：
- TaskConfig：通用任务配置容器（type + enabled + config dict），被所有 file task 业务逻辑依赖
"""

import re
import threading
from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel, Field, field_validator, model_validator

# Pydantic model_validator 需要接受 Any 类型
# 这是框架接口边界：输入可能来自外部原始数据，无法提前类型化
# ruff: noqa: ANN401


# ============================================================================
# 文件相关枚举和值对象
# ============================================================================


class PathEntryType(StrEnum):
    """路径项类型枚举

    区分路径项是文件还是文件夹，用于目录扫描和遍历操作。
    """

    FILE = "file"
    DIRECTORY = "directory"


class FileType(StrEnum):
    """文件类型枚举

    用于区分不同类型的文件（视频、图片、字幕、压缩包、其他）。
    这是文件 domain 的核心概念，用于文件分类和处理决策。

    UNCLASSIFIED：尚未按扩展名分类时的占位（例如收件箱预删除命中后返回的 DeleteDecision），
    与扩展名归入的 MISC 区分。
    """

    VIDEO = "video"
    IMAGE = "image"
    SUBTITLE = "subtitle"
    ARCHIVE = "archive"
    MISC = "misc"
    UNCLASSIFIED = "unclassified"


# JAV 番号数字段：与 `jav_filename_util` 固定规则一致（文件名解析与领域对象同一语义）
SERIAL_DIGIT_CHARS_MIN = 3
SERIAL_DIGIT_CHARS_MAX = 5
SERIAL_EFFECTIVE_DIGITS_MIN = 1
SERIAL_EFFECTIVE_DIGITS_MAX = 4


def effective_serial_digit_len(raw: str) -> int | None:
    """文件名/番号中连续数字串的「有效位数」（与补零展示无关）。

    - 非全 ``0``：十进制数值的位数（如 ``00399`` -> 3）。
    - 全 ``0``：按占位长度计（如 ``000`` -> 3），避免 ``int`` 退化为单 0。
    """
    if not raw or not raw.isdigit():
        return None
    if set(raw) == {"0"}:
        return len(raw)
    return len(str(int(raw, 10)))


def serial_number_raw_is_valid(raw: str) -> bool:
    """原始数字串是否满足固定规则：仅数字、长度 3–5、有效位数 1–4。"""
    if not raw.isdigit():
        return False
    if not (SERIAL_DIGIT_CHARS_MIN <= len(raw) <= SERIAL_DIGIT_CHARS_MAX):
        return False
    eff = effective_serial_digit_len(raw)
    if eff is None:
        return False
    return SERIAL_EFFECTIVE_DIGITS_MIN <= eff <= SERIAL_EFFECTIVE_DIGITS_MAX


class SerialId(BaseModel):
    """番号值对象

    结构化表示番号，包含字母前缀和数字部分。
    支持从字符串解析（"ABC-123"、"ABC_123"、"ABC123"）和转换为字符串。
    这是文件 domain 的核心值对象，用于 JAV 视频文件的番号识别和整理。

    设计意图：
    - 封装番号的验证逻辑，确保番号格式的一致性
    - 提供统一的番号表示方式，便于文件名生成和目录组织
    - 原始 number 须为 3–5 位数字且有效位数 1–4（见 ``serial_number_raw_is_valid``），与文件名解析一致
    - 校验通过后自动规范化：先 zfill 至最少 3 位；若长度仍大于 3，则去掉前导 0 直至长度为 3
    """

    prefix: str = Field(..., description="字母前缀（2-6个大写字母）")
    number: str = Field(
        ...,
        description=(
            "数字部分（原始 3–5 位数字，有效位 1–4；"
            "规范化：先 zfill(3)，再对长度>3 去前导 0 直至 3 位）"
        ),
    )

    @field_validator("prefix")
    @classmethod
    def validate_prefix(cls, v: str) -> str:
        """验证字母前缀"""
        v_upper = v.upper()
        if not v_upper.isalpha():
            raise ValueError("前缀必须只包含字母")
        if not (2 <= len(v_upper) <= 6):
            raise ValueError("前缀长度必须在2-6个字符之间")
        return v_upper

    @field_validator("number")
    @classmethod
    def validate_number(cls, v: str) -> str:
        """验证并规范化数字部分。

        先按固定规则校验原始串，再 zfill 至最少 3 位；若长度仍大于 3，则反复去掉最左侧的 0，
        直到长度为 3（保留 3 位时的前导 0，如 012）。
        例如：'123'→'123'，'0123'→'123'，'01234'→'1234'。
        """
        if not v.isdigit():
            raise ValueError("数字部分必须只包含数字")
        if not serial_number_raw_is_valid(v):
            raise ValueError(
                "数字部分须为3-5位且有效位数在1-4之间（与番号匹配规则一致）",
            )
        s = v.zfill(3)
        while len(s) > 3 and s.startswith("0"):
            s = s[1:]
        return s

    @classmethod
    def from_string(cls, value: str) -> SerialId:
        """从字符串解析番号

        支持格式：
        - "ABC-123"（连字符分隔）
        - "ABC_123"（下划线分隔）
        - "ABC123"（无分隔符）

        Args:
            value: 番号字符串

        Returns:
            SerialId 对象

        Raises:
            ValueError: 如果字符串格式无效

        Examples:
            >>> SerialId.from_string("ABC-123")
            SerialId(prefix='ABC', number='123')
            >>> SerialId.from_string("ABC_123")
            SerialId(prefix='ABC', number='123')
            >>> SerialId.from_string("ABC123")
            SerialId(prefix='ABC', number='123')
        """
        pattern = r"^([A-Za-z]{2,6})[-_]?(\d{3,5})$"
        match = re.match(pattern, value)
        if not match:
            raise ValueError(f"无效的番号格式: {value}")
        prefix = match.group(1).upper()
        number = match.group(2)
        return cls(prefix=prefix, number=number)

    @model_validator(mode="before")
    @classmethod
    # 保持 Any 是框架要求；这里仅做字符串到结构化数据的桥接
    def parse_string_input(cls, data: Any) -> Any:  # noqa: ANN401
        """支持从字符串自动解析（向后兼容）"""
        if isinstance(data, str):
            return cls.from_string(data).model_dump()
        return data

    def __str__(self) -> str:
        """转换为字符串格式：PREFIX-NUMBER"""
        return f"{self.prefix}-{self.number}"


# ============================================================================
# 任务执行状态枚举
# ============================================================================


class FileTaskRunStatus(StrEnum):
    """文件任务执行状态枚举"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class FileTaskTriggerType(StrEnum):
    """文件任务触发类型枚举"""

    MANUAL = "manual"
    AUTO = "auto"


# ============================================================================
# 领域异常
# ============================================================================


class FileTaskError(Exception):
    """文件任务相关异常基类"""

    pass


class FileTaskNotFoundError(FileTaskError):
    """任务执行实例不存在异常"""

    def __init__(self, run_id: int) -> None:
        self.run_id = run_id
        super().__init__(f"任务执行实例不存在: {run_id}")


class FileTaskAlreadyRunningError(FileTaskError):
    """任务已在运行异常"""

    def __init__(self, running_run_id: int) -> None:
        self.running_run_id = running_run_id
        super().__init__(f"已有任务正在运行: {running_run_id}")


class FileTaskCancelledError(FileTaskError):
    """任务已取消异常"""

    def __init__(self, run_id: int) -> None:
        self.run_id = run_id
        super().__init__(f"任务已取消: {run_id}")


# ============================================================================
# 任务执行实例领域模型
# ============================================================================


class FileTaskRunReport(BaseModel):
    """文件任务执行汇总报告

    记录任务执行的完整统计结果，包含成功率、错误率、耗时等派生属性。
    通常在任务完成后由 Pipeline 构建，用于日志和展示。
    """

    run_name: str = Field(..., description="执行实例名称")
    start_time: datetime = Field(..., description="开始时间")
    end_time: datetime = Field(..., description="结束时间")
    total_items: int = Field(0, description="总item数")
    success_items: int = Field(0, description="成功item数")
    error_items: int = Field(0, description="失败item数")
    skipped_items: int = Field(0, description="跳过item数")
    warning_items: int = Field(0, description="警告item数")
    total_duration_ms: float = Field(0.0, description="总耗时（毫秒）")

    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_items == 0:
            return 0.0
        return self.success_items / self.total_items

    @property
    def error_rate(self) -> float:
        """错误率"""
        if self.total_items == 0:
            return 0.0
        return self.error_items / self.total_items

    @property
    def duration_seconds(self) -> float:
        """耗时（秒）"""
        return self.total_duration_ms / 1000.0

    def update_from_stats(self, stats: dict[str, Any]) -> None:
        """从统计信息字典更新报告字段

        Args:
            stats: 统计信息字典，包含 total_items, success_items, error_items,
                   skipped_items, warning_items, total_duration_ms
        """
        self.total_items = stats.get("total_items", 0)
        self.success_items = stats.get("success_items", 0)
        self.error_items = stats.get("error_items", 0)
        self.skipped_items = stats.get("skipped_items", 0)
        self.warning_items = stats.get("warning_items", 0)
        self.total_duration_ms = stats.get("total_duration_ms", 0.0)


class FileTaskRunStatistics(BaseModel):
    """单次任务 run 结束时的统计快照（返回给 `FileTaskRunManager` 写回 `file_task_runs`）。

    在 JAV 整理链路中：`FilePipeline._finish_task` 调用 `FileResultRepository.get_statistics(run_id)`，
    将聚合字典 `model_validate` 为本模型。语义上以仓储聚合为准，而非仅依赖管道内存计数。

    Raw 整理链路：`RawFilePipeline` 在上述聚合之上合并「阶段化」计数（仍不写目录明细表），
    键名见 `phase*` 字段。
    """

    total_items: int = Field(0, description="总item数")
    success_items: int = Field(0, description="成功item数")
    error_items: int = Field(0, description="失败item数")
    skipped_items: int = Field(0, description="跳过item数")
    warning_items: int = Field(0, description="警告item数")
    total_duration_ms: float = Field(0.0, description="总耗时（毫秒）")

    phase1_seen_files: int = Field(
        0,
        description="Raw：阶段1 见到的 inbox 第一层文件数",
    )
    phase1_moved_files: int = Field(
        0,
        description="Raw：阶段1 成功归入 files_misc 的文件数（含 dry_run 预览成功）",
    )
    phase1_error_files: int = Field(
        0,
        description="Raw：阶段1 处理失败的文件数",
    )
    phase2_seen_dirs: int = Field(
        0,
        description="Raw：阶段2 见到的 inbox 第一层目录数",
    )
    phase2_deferred_dirs: int = Field(
        0,
        description="Raw：阶段2 暂未处理的目录数（占位阶段与实际暂缓语义一致）",
    )
    phase3_seen_files_misc: int = Field(
        0,
        description="Raw：阶段3 开始时 files_misc 下第一层文件数",
    )
    phase3_deferred_files_misc: int = Field(
        0,
        description="Raw：阶段3 占位暂未分流处理的文件数",
    )


class FileTaskRun(BaseModel):
    """文件任务执行实例持久化记录

    对应数据库 file_task_runs 表中的一行，由 FileTaskRunRepository 读写。
    """

    run_id: int = Field(..., description="执行实例ID")
    run_name: str = Field(..., description="执行实例名称")
    task_type: str = Field(..., description="任务类型")
    trigger_type: FileTaskTriggerType = Field(..., description="触发类型")
    status: FileTaskRunStatus = Field(..., description="执行状态")
    start_time: datetime = Field(..., description="开始时间")
    end_time: datetime | None = Field(None, description="结束时间")
    error_message: str | None = Field(None, description="错误消息")


class FileTaskRunner(Protocol):
    """可执行任务用例的协议：具体任务类（如 `JavVideoOrganizer`）在构造期注入仓储与配置来源，`run` 仅收运行时参数。

    契约：
        - `task_type`：与 YAML / 常量 `TASK_TYPE_*` 一致，供并发调度按类型串行或查找实现类。
        - `run(run_id, dry_run, cancellation_event)`：执行一次完整用例并返回 `FileTaskRunStatistics`；
          实现通常委托 `FilePipeline`，但协议不强行规定。

    依赖注入：`run` 不再传 repository，改为实现类 `__init__` 已持有端口，便于测试替换实现。
    """

    @property
    def task_type(self) -> str:
        """与 `TaskConfig.type` 相同的任务 slug（如 `jav_video_organizer`）。"""
        ...

    def run(
        self,
        run_id: int,
        dry_run: bool = False,
        cancellation_event: threading.Event | None = None,
    ) -> FileTaskRunStatistics:
        """执行一次任务并得到统计；`dry_run` 时执行器只做分析与预览性的 Decision 落地，不写真实文件移动/删除。

        `cancellation_event` 由管理器创建，长任务应在循环中轮询以便提前退出（如 `FilePipeline.run`）。
        """
        ...


# ============================================================================
# 任务配置
# ============================================================================

_T = TypeVar("_T", bound=BaseModel)


class TaskConfig(BaseModel):
    """磁盘上一条任务配置的通用外壳（`task_config.yaml` 内按类型分块）。

    `config` 为 JSON 可序列化的 dict，业务侧通过 `get_config(具体Pydantic模型)` 得到强类型
    配置（例如 `JavVideoOrganizeConfig`），避免 analyzer/管道直接依赖裸 dict。

    TODO: 将 `config` 演进为按 `type` 区分的判别联合，去掉 `Any` 与 `get_config` 上的类型忽略。
    """

    type: str = Field(..., description="任务类型（如 jav_video_organizer）")
    enabled: bool = Field(True, description="是否启用")
    config: dict[str, Any] = Field(..., description="任务特定配置")

    def get_config(self, config_type: type[_T]) -> _T:  # ty: ignore[invalid-type-form]
        """将本记录的 `config` dict 校验并转换为指定 Pydantic 模型（如 `JavVideoOrganizeConfig`）。

        典型调用点：`JavVideoOrganizer.__init__` 中完成一次反序列化，整次 run 共用 `self.file_config`。
        """
        return config_type.model_validate(self.config)
