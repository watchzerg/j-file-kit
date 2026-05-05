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

番号匹配前可按 `JavAnalyzeConfig` 传入的子串列表（字段 **`jav_filename_strip_substrings`**，管线默认取自 **`organizer_defaults`**，大小写不敏感）；
未配置或空配置则不处理。成功重构时输出文件名同样不含已移除的子串。

番号匹配（代码内固定 grammar，与 `SerialId` / `serial_number_raw_is_valid` 对齐）：
- 字母前缀：2–6 个英文字母；前不得紧贴字母；与数字间可选 `-`/`_`
- 数字段：连续 3–5 个数字字符；有效位数 1–4（见 domain）
- 边界：数字段后不得再紧跟数字；滑动搜索失败则从下一位置重试，避免误吞过长数字
- 输出：标准形式 `PREFIX-NUMBER`（大写前缀，数字经 `SerialId` 规范化）
"""

import re
from pathlib import Path

from j_file_kit.app.file_task.domain.models import (
    SERIAL_DIGIT_CHARS_MAX,
    SerialId,
    serial_number_raw_is_valid,
)

PREFIX_LETTERS_MIN = 2
PREFIX_LETTERS_MAX = 6

FILENAME_SEPARATORS = " -_@#"

# 文件系统文件名字节上限（ext4 / APFS 等主流文件系统均为 255 字节）
MAX_FILENAME_BYTES = 255

# 固定番号前缀正则（模块加载时编译一次；数字段在 `_match_serial_id` 中按领域规则校验）
JAV_SERIAL_PREFIX_PATTERN = re.compile(
    rf"(?<![a-zA-Z])([a-zA-Z]{{{PREFIX_LETTERS_MIN},{PREFIX_LETTERS_MAX}}})"
    r"[-_]?(?=\d)",
    re.IGNORECASE,
)


def _match_serial_id(filename: str) -> tuple[SerialId | None, int | None, int | None]:
    """匹配番号：返回 SerialId 与 [start, end) 切片（半开区间）。

    在 `JAV_SERIAL_PREFIX_PATTERN` 上滑动搜索；对每次前缀命中截取连续数字串，按领域规则校验；
    失败则自 `match.start() + 1` 继续，避免误吞过长数字段。

    Args:
        filename: 文件名

    Returns:
        (SerialId, start, end)；未命中为 (None, None, None)
    """
    pos = 0
    while pos <= len(filename):
        m = JAV_SERIAL_PREFIX_PATTERN.search(filename, pos)
        if m is None:
            return None, None, None

        letters = m.group(1).upper()
        digit_start = m.end()
        rest = filename[digit_start:]
        dm = re.match(r"\d+", rest)
        if dm is None:
            pos = m.start() + 1
            continue

        run = dm.group(0)
        if len(run) > SERIAL_DIGIT_CHARS_MAX:
            pos = m.start() + 1
            continue

        raw = run
        if not serial_number_raw_is_valid(raw):
            pos = m.start() + 1
            continue

        end_exclusive = digit_start + len(raw)
        if end_exclusive < len(filename) and filename[end_exclusive].isdigit():
            pos = m.start() + 1
            continue

        serial_id = SerialId(prefix=letters, number=raw)
        return serial_id, m.start(), end_exclusive

    return None, None, None


def strip_jav_filename_noise(filename: str, substrings: tuple[str, ...]) -> str:
    """从文件名中移除配置的子串（大小写不敏感，各处出现均删除）。

    `substrings` 为空元组时不做处理，原样返回 `filename`。
    """
    if not substrings:
        return filename
    result = filename
    for token in substrings:
        result = re.sub(re.escape(token), "", result, flags=re.IGNORECASE)
    return result


def _truncate_to_bytes(text: str, max_bytes: int) -> str:
    """将文本截断到 UTF-8 编码不超过 max_bytes 字节。

    在字节边界处截断时会自动跳过不完整的多字节字符，保证结果是合法 UTF-8。

    Args:
        text: 原始文本
        max_bytes: 最大字节数（含）

    Returns:
        截断后的字符串，其 UTF-8 编码长度 <= max_bytes
    """
    if max_bytes <= 0:
        return ""
    encoded = text.encode()
    if len(encoded) <= max_bytes:
        return text
    return encoded[:max_bytes].decode(errors="ignore")


def generate_jav_filename(
    filename: str,
    *,
    strip_substrings: tuple[str, ...] = (),
) -> tuple[str, SerialId | None]:
    """根据番号生成新文件名。

    从文件名中提取番号并按业务规则重构文件名。
    先按 `strip_substrings` 去除站标等子串再匹配番号；若匹配成功，输出文件名基于去噪后的字符串，
    不再包含这些子串。未匹配到番号时返回原始 `filename`（不去噪）。
    若生成的文件名超过 MAX_FILENAME_BYTES 字节，会截断非关键内容（第1、3部分），
    确保番号、占位符和扩展名始终完整保留。
    纯文件名转换函数，不涉及路径处理。番号前缀匹配使用模块内固定 `JAV_SERIAL_PREFIX_PATTERN`。

    Args:
        filename: 原始文件名（包含扩展名）
        strip_substrings: 匹配前从文件名中移除的子串（大小写不敏感）；空则不处理

    Returns:
        元组：(新文件名, 提取到的番号)。如果没有找到番号，返回 (原文件名, None)
    """
    path = Path(filename)
    suffix = path.suffix

    working = strip_jav_filename_noise(filename, strip_substrings)
    serial_id, start, end = _match_serial_id(working)
    if serial_id is None or start is None or end is None:
        return filename, None

    part1 = working[:start]
    part3_with_suffix = working[end:]
    part3 = part3_with_suffix.removesuffix(suffix) if suffix else part3_with_suffix
    part4 = suffix

    trimmed_part1 = part1.strip(FILENAME_SEPARATORS)
    trimmed_part3 = part3.strip(FILENAME_SEPARATORS)
    serial_id_str = str(serial_id)

    if not trimmed_part1:
        if not trimmed_part3:
            new_filename = f"{serial_id_str}{part4}"
        else:
            fixed_bytes = len(f"{serial_id_str} {part4}".encode())
            safe_part3 = _truncate_to_bytes(
                trimmed_part3,
                MAX_FILENAME_BYTES - fixed_bytes,
            )
            new_filename = f"{serial_id_str} {safe_part3}{part4}"
    else:
        if not trimmed_part3:
            fixed_bytes = len(f"{serial_id_str} -serialId{part4}".encode())
            safe_part1 = _truncate_to_bytes(
                trimmed_part1,
                MAX_FILENAME_BYTES - fixed_bytes,
            )
            new_filename = f"{serial_id_str} {safe_part1}-serialId{part4}"
        else:
            fixed_bytes = len(f"{serial_id_str} -serialId-{part4}".encode())
            avail = MAX_FILENAME_BYTES - fixed_bytes
            part1_bytes = len(trimmed_part1.encode())
            if part1_bytes < avail:
                safe_part1 = trimmed_part1
                safe_part3 = _truncate_to_bytes(trimmed_part3, avail - part1_bytes)
            else:
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
    SerialId 已验证 prefix 长度在 2-6 之间，因此可以安全访问 prefix[0] 和 prefix[:2]。
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
