"""JAV 领域工具函数模块

提供 JAV 文件处理相关的工具函数，包括番号匹配、文件名重构和目录生成。

业务规则：
1. 文件名分解为4部分：番号之前的内容、番号、番号之后的内容、扩展名
2. 对第1、3部分分别执行trim操作：去除前后的空格、连字符(-)、下划线(_)、@符号、#符号
3. 根据第1部分trim后是否为空判断番号是否在开头
4. 按不同规则拼接新文件名；若生成文件名超过 MAX_FILENAME_BYTES 字节，截断非关键部分

拼接规则：
- 番号在开头（第1部分trim后为空）：
  - 标准番号 + [空格 + 第3部分trim后的内容] + 扩展名
  - 如果第3部分trim后为空，则只输出：标准番号 + 扩展名

- 番号不在开头（第1部分trim后不为空）：
  - 标准番号 + 空格 + 第1部分 + 占位符 + 扩展名
  - 占位符：第3部分trim后为空 → "-serialId"，否则 → "-serialId-" + 第3部分

截断规则（仅在生成文件名超过 MAX_FILENAME_BYTES 字节时生效）：
- 关键部分（永不截断）：标准番号、"-serialId[-]" 占位符、扩展名
- 非关键部分（可截断）：第1部分、第3部分
- 截断顺序：优先截断第3部分；若仍超限则丢弃第3部分并截断第1部分

番号规则（基于正则表达式：`(?<![a-zA-Z])([a-zA-Z]{2,5})[-_]?(\\d{2,5})(?![0-9])`）：
- 字母部分：2-5个英文字母（大小写都可以）
- 分隔符：可选，支持 `-`、`_` 或无分隔符
- 数字部分：2-5个数字
- 边界条件：番号前面不能紧挨着字母，番号后面不能紧挨着数字
- 输出格式：统一标准化为 `字母-数字` 格式（大写字母）
"""

import re
from pathlib import Path

from j_file_kit.app.file_task.domain.models import SerialId

DEFAULT_SERIAL_PATTERN = r"(?<![a-zA-Z])([a-zA-Z]{2,5})[-_]?(\d{2,5})(?![0-9])"

FILENAME_SEPARATORS = " -_@#"

# 文件系统文件名字节上限（ext4 / APFS 等主流文件系统均为 255 字节）
MAX_FILENAME_BYTES = 255


def _truncate_to_bytes(text: str, max_bytes: int) -> str:
    """将文本截断到 UTF-8 编码不超过 max_bytes 字节。

    在字节边界处截断时会自动跳过不完整的多字节字符，保证结果是合法 UTF-8。

    Args:
        text: 原始字符串
        max_bytes: 最大字节数（含）

    Returns:
        截断后的字符串，其 UTF-8 编码长度 <= max_bytes
    """
    if max_bytes <= 0:
        return ""
    encoded = text.encode()
    if len(encoded) <= max_bytes:
        return text
    # errors="ignore" 会自动丢弃截断点处不完整的多字节尾部
    return encoded[:max_bytes].decode(errors="ignore")


def _match_serial_id(
    filename: str,
    pattern: str = DEFAULT_SERIAL_PATTERN,
) -> tuple[SerialId | None, re.Match[str] | None]:
    """匹配番号，同时返回 SerialId 和 Match 对象以避免重复正则匹配。

    Args:
        filename: 文件名
        pattern: 番号正则表达式

    Returns:
        元组：(SerialId 对象, Match 对象)。如果没有匹配到，返回 (None, None)
    """
    match = re.search(pattern, filename, re.IGNORECASE)
    if not match:
        return None, None

    letters = match.group(1).upper()
    digits = match.group(2)
    serial_id = SerialId(prefix=letters, number=digits)
    return serial_id, match


def generate_jav_filename(filename: str) -> tuple[str, SerialId | None]:
    """根据番号生成新文件名

    使用内置的 DEFAULT_SERIAL_PATTERN 进行番号提取和文件名重构。
    若生成的文件名超过 MAX_FILENAME_BYTES 字节，会截断非关键内容（第1、3部分），
    确保番号、占位符和扩展名始终完整保留。
    纯文件名转换函数，不涉及路径处理。

    Args:
        filename: 原始文件名（包含扩展名）

    Returns:
        元组：(新文件名, 提取到的番号)。如果没有找到番号，返回 (原文件名, None)

    Examples:
        >>> new_filename, serial_id = generate_jav_filename("video_ABC-001_hd.mp4")
        >>> new_filename
        "ABC-001 video-serialId-hd.mp4"
        >>> serial_id
        SerialId(prefix='ABC', number='001')

        >>> new_filename, serial_id = generate_jav_filename("ABC-001_video.mp4")
        >>> new_filename
        "ABC-001 video.mp4"
        >>> serial_id
        SerialId(prefix='ABC', number='001')

        >>> new_filename, serial_id = generate_jav_filename("no_serial.mp4")
        >>> new_filename
        "no_serial.mp4"
        >>> serial_id
        None
    """
    # 使用 Path 仅用于提取扩展名
    path = Path(filename)
    suffix = path.suffix

    # 匹配番号并获取位置信息（一次正则匹配同时获取 SerialId 和位置）
    serial_id, match = _match_serial_id(filename)
    if not serial_id or not match:
        return filename, None

    # 分解文件名为4部分
    start, end = match.span()
    part1 = filename[:start]  # 番号之前的内容
    # 番号之后的内容（不含扩展名）：使用 removesuffix 安全移除扩展名
    part3_with_suffix = filename[end:]
    part3 = part3_with_suffix.removesuffix(suffix) if suffix else part3_with_suffix
    part4 = suffix  # 扩展名

    trimmed_part1 = part1.strip(FILENAME_SEPARATORS)
    trimmed_part3 = part3.strip(FILENAME_SEPARATORS)
    serial_id_str = str(serial_id)

    # 判断番号是否在开头（第1部分trim后为空）
    if not trimmed_part1:
        if not trimmed_part3:
            new_filename = f"{serial_id_str}{part4}"
        else:
            # 关键固定部分："{serial_id} " + ext；第3部分为可截断内容
            fixed_bytes = len(f"{serial_id_str} {part4}".encode())
            safe_part3 = _truncate_to_bytes(
                trimmed_part3,
                MAX_FILENAME_BYTES - fixed_bytes,
            )
            new_filename = f"{serial_id_str} {safe_part3}{part4}"
    else:
        # 番号不在开头
        if not trimmed_part3:
            # 关键固定部分："{serial_id} -serialId" + ext；第1部分为可截断内容
            fixed_bytes = len(f"{serial_id_str} -serialId{part4}".encode())
            safe_part1 = _truncate_to_bytes(
                trimmed_part1,
                MAX_FILENAME_BYTES - fixed_bytes,
            )
            new_filename = f"{serial_id_str} {safe_part1}-serialId{part4}"
        else:
            # 关键固定部分："{serial_id} -serialId-" + ext；优先截断 part3，part1 超限时丢弃 part3 并截断 part1
            fixed_bytes = len(f"{serial_id_str} -serialId-{part4}".encode())
            avail = MAX_FILENAME_BYTES - fixed_bytes
            part1_bytes = len(trimmed_part1.encode())
            if part1_bytes < avail:
                safe_part1 = trimmed_part1
                safe_part3 = _truncate_to_bytes(trimmed_part3, avail - part1_bytes)
            else:
                # 第1部分已超出预算，丢弃第3部分，仅截断第1部分
                fixed_bytes2 = len(f"{serial_id_str} -serialId{part4}".encode())
                safe_part1 = _truncate_to_bytes(
                    trimmed_part1,
                    MAX_FILENAME_BYTES - fixed_bytes2,
                )
                safe_part3 = ""
            if safe_part3:
                new_filename = (
                    f"{serial_id_str} {safe_part1}-serialId-{safe_part3}{part4}"
                )
            else:
                new_filename = f"{serial_id_str} {safe_part1}-serialId{part4}"

    return new_filename, serial_id


def generate_sorted_dir(serial_id: SerialId) -> Path:
    """生成整理子目录路径：A/AB/ABCD

    根据番号生成子目录路径，格式为：首字母/前两字母/完整前缀
    SerialId 已验证 prefix 长度在 2-5 之间，因此可以安全访问。
    调用者负责拼接基础目录。

    Args:
        serial_id: 番号对象

    Returns:
        相对子目录路径（不含基础目录和文件名）

    Examples:
        >>> from j_file_kit.app.file_task.domain.models import SerialId
        >>> generate_sorted_dir(SerialId(prefix="ABCD", number="123"))
        Path("A/AB/ABCD")

        >>> generate_sorted_dir(SerialId(prefix="XYZ", number="456"))
        Path("X/XY/XYZ")

        >>> generate_sorted_dir(SerialId(prefix="AB", number="789"))
        Path("A/AB/AB")
    """
    prefix = serial_id.prefix
    first_letter = prefix[0]
    first_two = prefix[:2]

    return Path(first_letter) / first_two / prefix
