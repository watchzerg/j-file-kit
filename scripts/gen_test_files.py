#!/usr/bin/env python3
"""生成测试文件脚本

在指定目录下生成各类场景的测试文件，用于本地验证 Docker 环境下的文件整理任务。

用法：
  python scripts/gen_test_files.py [目标目录]

  未传参数时，自动读取项目根目录的 .env 文件中的 MEDIA_ROOT 变量，
  生成到 $MEDIA_ROOT/jav/inbox（与 jav_video_organizer 默认 inbox_dir 对齐）。

测试场景分组（见下方 TEST_FILES）：
  A. 标准有番号媒体       → sorted/
  B. 番号边界 case       → sorted/ 或 unsorted/
  C. 文件名冲突消解       → sorted/（第二个触发 -jfk-xxxx）
  D. 无番号媒体           → unsorted/
  E. 压缩文件             → archive/
  F. Misc 扩展名匹配删除  → 删除
  G. Misc 关键字+体积删除 → 删除
  H. Misc 大小精确边界    → 删除 or misc/
  I. Misc 不满足删除规则  → misc/
  J. 子目录 & 空目录清理  → 文件处理后空目录被删除
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path

_1MB = 1024 * 1024


@dataclass
class TestFile:
    rel_path: str
    size: int
    description: str
    expected: str = field(default="")


# fmt: off
TEST_FILES: list[TestFile] = [

    # ── A. 标准有番号媒体 → sorted ────────────────────────────────────────────
    TestFile(
        "ABC-001.mp4", _1MB * 2,
        "有番号视频，番号在文件名开头",
        "sorted/A/AB/ABC/ABC-001.mp4",
    ),
    TestFile(
        "ABC-001_4k.mp4", _1MB * 2,
        "有番号视频，开头番号 + 后缀标签",
        "sorted/A/AB/ABC/ABC-001 4k.mp4",
    ),
    TestFile(
        "video_ABC-001_hd.mkv", _1MB * 2,
        "有番号视频，番号不在开头",
        "sorted/A/AB/ABC/ABC-001 video-serialId-hd.mkv",
    ),
    TestFile(
        "STAR-999.avi", _1MB * 3,
        "有番号视频，STAR 系列",
        "sorted/S/ST/STAR/STAR-999.avi",
    ),
    TestFile(
        "MIDE_123_sample_full.mp4", _1MB * 2,
        "有番号视频，下划线分隔番号 + 文件体积超删除阈值（注意 sample 在番号之后）",
        "sorted/M/MI/MIDE/MIDE-123 sample_full.mp4",
    ),
    TestFile(
        "ABC-001.jpg", 512,
        "有番号图片",
        "sorted/A/AB/ABC/ABC-001.jpg",
    ),
    TestFile(
        "STAR-999.png", 512,
        "有番号图片 PNG",
        "sorted/S/ST/STAR/STAR-999.png",
    ),

    # ── B. 番号边界 case ──────────────────────────────────────────────────────

    # B1. 最短合法番号：2字母 + 2数字
    TestFile(
        "AB-12.mp4", _1MB * 2,
        "[边界] 最短合法番号（2字母+2数字）→ sorted",
        "sorted/A/AB/AB/AB-12.mp4",
    ),
    # B2. 最长合法番号：5字母 + 5数字
    TestFile(
        "ABCDE-12345.mp4", _1MB * 2,
        "[边界] 最长合法番号（5字母+5数字）→ sorted",
        "sorted/A/AB/ABCDE/ABCDE-12345.mp4",
    ),
    # B3. 无分隔符番号
    TestFile(
        "ABC001.mp4", _1MB * 2,
        "[边界] 无分隔符番号 → sorted",
        "sorted/A/AB/ABC/ABC-001.mp4",
    ),
    # B4. 小写字母番号（应标准化为大写）
    TestFile(
        "abc-002.mp4", _1MB * 2,
        "[边界] 全小写番号，应标准化为 ABC-002 → sorted",
        "sorted/A/AB/ABC/ABC-002.mp4",
    ),
    # B5. 大写扩展名（.MP4）— 应被识别为视频
    TestFile(
        "ABC-003.MP4", _1MB * 2,
        "[边界] 大写扩展名 .MP4，应被识别为视频 → sorted",
        "sorted/A/AB/ABC/ABC-003.MP4",
    ),
    # B6. 单字母前缀 → 不匹配番号规则 → unsorted
    TestFile(
        "A-001.mp4", _1MB * 2,
        "[边界] 单字母前缀，不构成合法番号（前缀需2-5字母）→ unsorted",
        "unsorted/A-001.mp4",
    ),
    # B7. 6字母前缀 → 超出番号规则上限 → 可能匹配内部5字母子串，需观察实际行为
    TestFile(
        "ABCDEF-001.mp4", _1MB * 2,
        "[边界] 6字母前缀，贪婪匹配取前5字母 ABCDE 作为番号 → sorted",
        "sorted/A/AB/ABCDE/ABCDE-001.mp4（注：正则贪婪匹配前5字母）",
    ),
    # B8. 番号前紧跟字母 → 负向前瞻失败 → unsorted
    TestFile(
        "xABC-004.mp4", _1MB * 2,
        "[边界] 番号前紧跟字母 x，x 被贪婪吸入前缀成为 XABC-004 → sorted",
        "sorted/X/XA/XABC/XABC-004.mp4（前缀 x 被贪婪吸入）",
    ),
    # B9. 番号后紧跟数字 → 正向后瞻失败 → unsorted
    TestFile(
        "ABC-0019.mp4", _1MB * 2,
        "[边界] 数字部分5位（合法上限），后续无数字 → sorted",
        "sorted/A/AB/ABC/ABC-0019.mp4",
    ),

    # ── C. 文件名冲突消解 → sorted（第二个文件触发 -jfk-xxxx）─────────────────
    # inbox 根目录和子目录各有一个 ABC-001.mp4：
    #   第一个先被处理并移动到 sorted/A/AB/ABC/ABC-001.mp4，
    #   第二个（来自 conflict/）到达时目标路径已存在，触发 -jfk-xxxx 后缀。
    # 注意：scan_directory_items 自底向上遍历，子目录文件先处理！
    #   实际上 conflict/ABC-001.mp4 先处理，根目录 ABC-001.mp4 后处理，
    #   所以根目录的那个会触发冲突（而非子目录的那个）。
    TestFile(
        "conflict/ABC-001.mp4", _1MB * 2,
        "[冲突] 子目录中的 ABC-001.mp4，自底向上先处理 → sorted（正常移动）",
        "sorted/A/AB/ABC/ABC-001.mp4",
    ),
    # 根目录中同名文件（自底向上遍历时后处理）→ 冲突 → -jfk-xxxx
    # 注意：A 组第一个已经是 ABC-001.mp4，但为清晰起见此处另建路径
    # 实际冲突：A 组的 ABC-001.mp4 与 conflict/ABC-001.mp4 产生相同目标路径
    # （两组文件同时存在时，自底向上遍历先处理 conflict/ 子目录文件）

    # ── D. 无番号媒体 → unsorted ──────────────────────────────────────────────
    TestFile(
        "home_video_2024.mp4", _1MB * 2,
        "无番号视频 → unsorted",
        "unsorted/home_video_2024.mp4",
    ),
    TestFile(
        "random_clip.mkv", _1MB * 2,
        "无番号视频 MKV → unsorted",
        "unsorted/random_clip.mkv",
    ),
    TestFile(
        "photo.jpg", 512,
        "无番号图片 → 删除",
        "DELETE",
    ),

    # ── E. 压缩文件 → archive ─────────────────────────────────────────────────
    TestFile(
        "ABC-001.zip", _1MB * 5,
        "有番号压缩包 → archive（番号不影响压缩包分类）",
        "archive/ABC-001.zip",
    ),
    TestFile(
        "extras.rar", _1MB * 3,
        "无番号压缩包 → archive",
        "archive/extras.rar",
    ),
    TestFile(
        "backup.7z", _1MB * 2,
        "7z 压缩包 → archive",
        "archive/backup.7z",
    ),

    # ── F. Misc：扩展名匹配删除规则 → 删除 ────────────────────────────────────
    TestFile("info.nfo",         512,  "NFO 文件，扩展名匹配 → 删除",    "DELETE"),
    TestFile("readme.txt",       256,  "TXT 文件，扩展名匹配 → 删除",    "DELETE"),
    TestFile("description.html", 1024, "HTML 文件，扩展名匹配 → 删除",   "DELETE"),
    TestFile("magnet.torrent",   2048, "Torrent 文件，扩展名匹配 → 删除", "DELETE"),
    TestFile("shortcut.url",     128,  "URL 文件，扩展名匹配 → 删除",    "DELETE"),

    # ── G. Misc：关键字 + 体积 ≤ 1MB → 删除 ──────────────────────────────────
    TestFile(
        "sample_clip.dat", _1MB // 2,
        "含 sample 关键字 + 体积 512KB（≤1MB）→ 删除",
        "DELETE",
    ),
    TestFile(
        "preview_intro.dat", _1MB // 4,
        "含 preview 关键字 + 体积 256KB（≤1MB）→ 删除",
        "DELETE",
    ),
    TestFile(
        "temp_file.dat", _1MB // 8,
        "含 temp 关键字 + 体积 128KB（≤1MB）→ 删除",
        "DELETE",
    ),

    # ── H. Misc 大小精确边界 ──────────────────────────────────────────────────
    TestFile(
        "sample_exact_1mb.dat", _1MB,
        "[边界] 含 sample 关键字 + 体积恰好 1MB（== max_size，≤ 规则成立）→ 删除",
        "DELETE",
    ),
    TestFile(
        "sample_over_1mb.dat", _1MB + 1,
        "[边界] 含 sample 关键字 + 体积 1MB+1字节（> max_size）→ misc/",
        "misc/sample_over_1mb.dat",
    ),

    # ── I. Misc：不满足删除规则 → misc/ ──────────────────────────────────────
    TestFile(
        "large_data.bin", _1MB * 2,
        "无关键字无匹配扩展名的大文件 → misc/",
        "misc/large_data.bin",
    ),
    TestFile(
        "custom_format.dat", _1MB * 3,
        "自定义格式大文件，无关键字 → misc/",
        "misc/custom_format.dat",
    ),

    # ── J. 子目录 & 空目录清理 ─────────────────────────────────────────────────
    TestFile(
        "subdir/IPPA-456.mp4", _1MB * 2,
        "子目录中有番号视频 → sorted；子目录因文件移走后变空 → 被自动删除",
        "sorted/I/IP/IPPA/IPPA-456.mp4 + subdir/ 被清理",
    ),
    TestFile(
        "subdir/info.nfo", 256,
        "子目录中 NFO 文件 → 删除；配合上方让 subdir/ 最终变空",
        "DELETE + subdir/ 被清理",
    ),
    TestFile(
        "deep/nested/MIDV-789.mp4", _1MB * 2,
        "深层嵌套子目录中的有番号视频 → sorted；各层空目录逐级被清理",
        "sorted/M/MI/MIDV/MIDV-789.mp4 + deep/nested/ 和 deep/ 被清理",
    ),
    TestFile(
        "only_nfo_dir/useless.nfo", 512,
        "只含 NFO 的子目录，NFO 删除后目录变空 → 目录被清理",
        "DELETE + only_nfo_dir/ 被清理",
    ),
]
# fmt: on


def create_file(path: Path, size: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        f.write(b"\x00" * size)


def format_size(size: int) -> str:
    if size >= _1MB:
        mb = size / _1MB
        return f"{mb:.1f}MB" if mb != int(mb) else f"{int(mb)}MB"
    if size >= 1024:
        return f"{size // 1024}KB"
    return f"{size}B"


def _load_dotenv(dotenv_path: Path) -> dict[str, str]:
    """从 .env 文件读取 KEY=VALUE 变量，忽略注释和空行。"""
    result: dict[str, str] = {}
    if not dotenv_path.exists():
        return result
    for line in dotenv_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        result[key.strip()] = value.strip()
    return result


def main() -> None:
    if len(sys.argv) > 1:
        target_dir = Path(sys.argv[1]).resolve()
    else:
        project_root = Path(__file__).parent.parent
        dotenv = _load_dotenv(project_root / ".env")
        media_root = dotenv.get("MEDIA_ROOT", "").strip()
        if not media_root:
            print(
                "错误：未传入目标目录，且 .env 中未设置 MEDIA_ROOT。",
                file=sys.stderr,
            )
            print("用法：python scripts/gen_test_files.py [目标目录]", file=sys.stderr)
            sys.exit(1)
        target_dir = (Path(media_root) / "jav" / "inbox").resolve()

    print(f"目标目录：{target_dir}")
    print(f"准备生成 {len(TEST_FILES)} 个测试文件\n")

    created = skipped = 0
    for tf in TEST_FILES:
        dest = target_dir / tf.rel_path
        if dest.exists():
            print(f"  [跳过] {tf.rel_path}（已存在）")
            skipped += 1
            continue
        create_file(dest, tf.size)
        size_str = format_size(tf.size)
        print(f"  [创建] {tf.rel_path:<45} {size_str:<8}  # {tf.description}")
        created += 1

    print(f"\n完成：创建 {created} 个，跳过 {skipped} 个（已存在）")

    print("\n⚠  冲突消解说明：")
    print("  inbox/ABC-001.mp4 与 inbox/conflict/ABC-001.mp4 将映射到同一目标路径。")
    print("  scan_directory_items 自底向上遍历，子目录先处理：")
    print("    1. conflict/ABC-001.mp4 先移动到 sorted/A/AB/ABC/ABC-001.mp4（正常）")
    print("    2. ABC-001.mp4 后处理，目标已存在 → 移动为 ABC-001-jfk-xxxx.mp4")

    print("\n预期处理结果汇总：")
    rows = [
        ("场景", "预期结果"),
        ("A. 标准有番号视频/图片", "→ sorted/<首字母>/<前2字母>/<全前缀>/"),
        ("B. 番号边界 case", "→ sorted/ 或 unsorted/（见注释）"),
        ("C. 文件名冲突（第2个同名）", "→ sorted/ 但文件名追加 -jfk-xxxx"),
        ("D. 无番号媒体", "→ unsorted/"),
        ("E. 压缩文件", "→ archive/"),
        ("F. Misc 扩展名匹配", "→ 删除"),
        ("G. Misc 关键字+小体积", "→ 删除"),
        ("H. Misc 恰好 1MB", "→ 删除（<= max_size）"),
        ("H. Misc 1MB+1字节", "→ misc/（> max_size）"),
        ("I. Misc 无规则匹配", "→ misc/"),
        ("J. 处理后空子目录", "→ 自动被删除"),
    ]
    col_w = max(len(r[0]) for r in rows)
    for label, result in rows:
        print(f"  {label:<{col_w}}  {result}")


if __name__ == "__main__":
    main()
