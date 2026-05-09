"""一次性脚本：从 VR-JAV 与 VR-deleted-JAV 目录收集番号前缀。

- VR-JAV：取一级子目录名第一个 '-' 之前部分
- VR-deleted-JAV：取一级文件名第一个 '-' 之前部分
- 全局去重，统一大写后排序输出
"""

from pathlib import Path

VR_JAV_DIR = Path("/Volumes/Porn-VR/VR-JAV")
VR_DELETED_JAV_DIR = Path("/Volumes/Porn-VR/VR-deleted-JAV")


def extract_prefix(name: str) -> str | None:
    if "-" not in name:
        return None
    prefix = name.split("-", 1)[0].strip()
    if not prefix:
        return None
    return prefix.upper()


def collect_from_subdirs(root: Path) -> set[str]:
    prefixes: set[str] = set()
    for entry in root.iterdir():
        if not entry.is_dir():
            continue
        if entry.name.startswith("."):
            continue
        prefix = extract_prefix(entry.name)
        if prefix:
            prefixes.add(prefix)
    return prefixes


def collect_from_files(root: Path) -> set[str]:
    prefixes: set[str] = set()
    for entry in root.iterdir():
        if not entry.is_file():
            continue
        if entry.name.startswith("."):
            continue
        prefix = extract_prefix(entry.name)
        if prefix:
            prefixes.add(prefix)
    return prefixes


def main() -> None:
    from_subdirs = collect_from_subdirs(VR_JAV_DIR)
    from_files = collect_from_files(VR_DELETED_JAV_DIR)

    print(f"VR-JAV 子目录提取到 {len(from_subdirs)} 个前缀")
    print(f"VR-deleted-JAV 文件提取到 {len(from_files)} 个前缀")

    merged = sorted(from_subdirs | from_files)
    print(f"合并去重后共 {len(merged)} 个前缀:")
    for p in merged:
        print(p)


if __name__ == "__main__":
    main()
