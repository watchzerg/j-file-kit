"""JAV 领域工具函数模块

提供 JAV 文件处理相关的工具函数，包括番号匹配、文件名重构和目录生成。

业务规则：
1. 文件名分解为4部分：番号之前的内容、番号、番号之后的内容、扩展名
2. 对第1、3部分分别执行trim操作：去除前后的空格、连字符(-)、下划线(_)、@符号、#符号
3. 根据第1部分trim后是否为空判断番号是否在开头
4. 按不同规则拼接新文件名

拼接规则：
- 番号在开头（第1部分trim后为空）：
  - 标准番号 + [空格 + 第3部分trim后的内容] + 扩展名
  - 如果第3部分trim后为空，则只输出：标准番号 + 扩展名

- 番号不在开头（第1部分trim后不为空）：
  - 标准番号 + 空格 + 第1部分 + 占位符 + 扩展名
  - 占位符：第3部分trim后为空 → "-serialId"，否则 → "-serialId-" + 第3部分

番号规则（基于正则表达式：`(?<![a-zA-Z])([a-zA-Z]{2,5})[-_]?(\\d{2,5})(?![0-9])`）：
- 字母部分：2-5个英文字母（大小写都可以）
- 分隔符：可选，支持 `-`、`_` 或无分隔符
- 数字部分：2-5个数字
- 边界条件：番号前面不能紧挨着字母，番号后面不能紧挨着数字
- 输出格式：统一标准化为 `字母-数字` 格式（大写字母）

标准化番号格式：大写字母 + 连字符 + 数字（如 ABC-123）
"""

import re
from pathlib import Path

from j_file_kit.models.value_objects import SerialId

# 默认番号提取正则表达式模式
DEFAULT_SERIAL_PATTERN = r"(?<![a-zA-Z])([a-zA-Z]{2,5})[-_]?(\d{2,5})(?![0-9])"

# 文件名分隔符常量：用于 trim 操作时去除的字符
FILENAME_SEPARATORS = " -_@#"


def _match_serial_id(
    filename: str, pattern: str = DEFAULT_SERIAL_PATTERN
) -> tuple[SerialId | None, re.Match[str] | None]:
    """内部函数：匹配番号并返回 SerialId 和 Match 对象

    同时返回匹配结果和位置信息，避免重复正则匹配。

    Args:
        filename: 文件名
        pattern: 番号正则表达式

    Returns:
        元组：(SerialId 对象, Match 对象)。如果没有匹配到，返回 (None, None)
    """
    match = re.search(pattern, filename, re.IGNORECASE)
    if not match:
        return None, None

    # 获取匹配的字母和数字部分
    letters = match.group(1).upper()
    digits = match.group(2)

    # 构造 SerialId 对象
    serial_id = SerialId(prefix=letters, number=digits)
    return serial_id, match


def trim_separators(text: str) -> str:
    """去除字符串前后的分隔符

    去除前后的：空格、连字符(-)、下划线(_)、@符号、#符号
    注意：不处理点号(.)，因为点号可能是文件名内容的一部分

    Args:
        text: 要处理的字符串

    Returns:
        处理后的字符串

    Examples:
        >>> trim_separators("  _abc-123_  ")
        "abc-123"
        >>> trim_separators("@ABC-001#")
        "ABC-001"
        >>> trim_separators("...ABC-001...")
        "...ABC-001..."  # 点号不会被trim
        >>> trim_separators("")
        ""
    """
    return text.strip(FILENAME_SEPARATORS)


def generate_jav_filename(original_path: Path) -> tuple[Path, SerialId | None]:
    """根据番号生成新文件名

    使用内置的 DEFAULT_SERIAL_PATTERN 进行番号提取和文件名重构。

    Args:
        original_path: 原文件路径

    Returns:
        元组：(新文件路径, 提取到的番号)。如果没有找到番号，返回 (原路径, None)

    Examples:
        >>> new_path, serial_id = generate_jav_filename(Path("video_ABC-001_hd.mp4"))
        >>> new_path
        Path("ABC-001 video-serialId-hd.mp4")
        >>> serial_id
        SerialId(prefix='ABC', number='001')

        >>> new_path, serial_id = generate_jav_filename(Path("ABC-001_video.mp4"))
        >>> new_path
        Path("ABC-001 video.mp4")
        >>> serial_id
        SerialId(prefix='ABC', number='001')

        >>> new_path, serial_id = generate_jav_filename(Path("no_serial.mp4"))
        >>> new_path
        Path("no_serial.mp4")
        >>> serial_id
        None
    """
    filename = original_path.name
    suffix = original_path.suffix
    parent = original_path.parent

    # 匹配番号并获取位置信息（一次正则匹配同时获取 SerialId 和位置）
    serial_id, match = _match_serial_id(filename)
    if not serial_id or not match:
        # 未匹配到番号，保持原文件名
        return original_path, None

    # 分解文件名为4部分
    start, end = match.span()
    part1 = filename[:start]  # 番号之前的内容
    # 番号之后的内容（不含扩展名）：使用 removesuffix 安全移除扩展名
    part3_with_suffix = filename[end:]
    part3 = part3_with_suffix.removesuffix(suffix) if suffix else part3_with_suffix
    part4 = suffix  # 扩展名

    # 对第1、3部分执行trim操作
    trimmed_part1 = trim_separators(part1)
    trimmed_part3 = trim_separators(part3)

    # 将 serial_id 转换为字符串用于文件名拼接
    serial_id_str = str(serial_id)

    # 判断番号是否在开头（第1部分trim后为空）
    if not trimmed_part1:
        # 番号在开头，按照规则重构文件名
        if not trimmed_part3:
            # 第3部分trim后为空，只输出：标准番号 + 扩展名
            new_filename = f"{serial_id_str}{part4}"
        else:
            # 第3部分trim后不为空，输出：标准番号 + 空格 + 第3部分 + 扩展名
            new_filename = f"{serial_id_str} {trimmed_part3}{part4}"
    else:
        # 番号不在开头
        if not trimmed_part3:
            # 第3部分trim后为空，占位符为 "-serialId"
            placeholder = "-serialId"
        else:
            # 第3部分trim后不为空，占位符为 "-serialId-" + 第3部分
            placeholder = f"-serialId-{trimmed_part3}"

        # 拼接：标准番号 + 空格 + 第1部分 + 占位符 + 扩展名
        new_filename = f"{serial_id_str} {trimmed_part1}{placeholder}{part4}"

    return parent / new_filename, serial_id


def generate_sorted_dir(sorted_dir: Path, serial_id: SerialId) -> Path:
    """生成整理目录路径：A/AB/ABCD/

    根据番号生成整理目录路径，格式为：sorted_dir/首字母/前两字母/完整前缀/
    SerialId 已验证 prefix 长度在 2-5 之间，因此可以安全访问。

    Args:
        sorted_dir: 整理目录根路径
        serial_id: 番号对象

    Returns:
        目录路径（不含文件名）

    Examples:
        >>> from j_file_kit.models.value_objects import SerialId
        >>> generate_sorted_dir(Path("/sorted"), SerialId(prefix="ABCD", number="123"))
        Path("/sorted/A/AB/ABCD")

        >>> generate_sorted_dir(Path("/sorted"), SerialId(prefix="XYZ", number="456"))
        Path("/sorted/X/XY/XYZ")

        >>> generate_sorted_dir(Path("/sorted"), SerialId(prefix="AB", number="789"))
        Path("/sorted/A/AB/AB")
    """
    prefix = serial_id.prefix
    first_letter = prefix[0]
    first_two = prefix[:2]

    return sorted_dir / first_letter / first_two / prefix
