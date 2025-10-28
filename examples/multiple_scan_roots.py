#!/usr/bin/env python3
"""多扫描根目录示例

演示如何使用 j-file-kit 的多个扫描根目录功能。
"""

from __future__ import annotations

from pathlib import Path
import tempfile
import shutil

from jfk.core.config import TaskConfig, GlobalConfig, TaskDefinition
from jfk.core.pipeline import Pipeline
from jfk.processors.analyzers import FileClassifier, SerialIdExtractor
from jfk.processors.executors import FileRenamer
from jfk.processors.finalizers import EmptyDirCleaner


def create_sample_files():
    """创建示例文件结构"""
    # 创建临时目录
    temp_dirs = []
    for i in range(3):
        temp_dir = Path(tempfile.mkdtemp(prefix=f"jfk_example_{i}_"))
        temp_dirs.append(temp_dir)
        
        # 在每个目录中创建不同类型的文件
        (temp_dir / "ABCD-001_video.mp4").write_text("video content")
        (temp_dir / "XYZ-999_movie.avi").write_text("video content")
        (temp_dir / "no_serial_video.mkv").write_text("video content")
        (temp_dir / "document.txt").write_text("text content")
        
        # 创建子目录
        subdir = temp_dir / "subdir"
        subdir.mkdir()
        (subdir / "ABC-123_hd.mov").write_text("video content")
        (subdir / "image.jpg").write_text("image content")
    
    return temp_dirs


def main():
    """主函数"""
    print("🚀 j-file-kit 多扫描根目录示例")
    print("=" * 50)
    
    # 创建示例文件
    print("📁 创建示例文件...")
    temp_dirs = create_sample_files()
    
    try:
        # 创建配置
        print("⚙️ 创建配置...")
        global_config = GlobalConfig(
            scan_roots=temp_dirs,  # 多个扫描根目录
            log_dir=Path("./logs"),
            report_dir=Path("./reports")
        )
        
        task = TaskDefinition(
            name="multi_root_organizer",
            type="file_organize",
            enabled=True,
            config={
                "todo_non_vidpic_dir": str(Path("./todo_non_vidpic")),
                "todo_vidpic_dir": str(Path("./todo_vidpic")),
                "video_extensions": [".mp4", ".avi", ".mkv", ".mov"],
                "image_extensions": [".jpg", ".jpeg", ".png", ".webp"]
            }
        )
        
        config = TaskConfig(global_=global_config, tasks=[task])
        
        # 创建管道
        print("🔧 创建处理管道...")
        pipeline = Pipeline(config, "multi_root_organizer")
        
        # 添加处理器
        pipeline.add_analyzer(FileClassifier(
            {".mp4", ".avi", ".mkv", ".mov"}, 
            {".jpg", ".jpeg", ".png", ".webp"}
        ))
        pipeline.add_analyzer(SerialIdExtractor())
        pipeline.add_executor(FileRenamer())
        pipeline.add_finalizer(EmptyDirCleaner(Path("./")))
        
        # 运行预览模式
        print("🔍 运行预览模式...")
        report = pipeline.run_dry()
        
        # 显示结果
        print("\n📊 处理结果:")
        print(f"总文件数: {report.total_files}")
        print(f"成功处理: {report.success_files}")
        print(f"失败处理: {report.error_files}")
        print(f"跳过处理: {report.skipped_files}")
        print(f"警告处理: {report.warning_files}")
        
        print("\n📋 文件处理详情:")
        for result in report.results:
            status = "✅" if result.success else "❌"
            print(f"{status} {result.file_info.path.name}")
            if result.context.serial_id:
                print(f"   番号: {result.context.serial_id}")
            if result.context.file_type:
                print(f"   类型: {result.context.file_type}")
        
        print(f"\n⏱️ 总耗时: {report.duration_seconds:.2f}秒")
        print(f"📈 成功率: {report.success_rate:.1%}")
        
    finally:
        # 清理临时目录
        print("\n🧹 清理临时文件...")
        for temp_dir in temp_dirs:
            shutil.rmtree(temp_dir, ignore_errors=True)
        
        # 清理输出目录
        for output_dir in ["./logs", "./reports", "./todo_non_vidpic", "./todo_vidpic"]:
            shutil.rmtree(output_dir, ignore_errors=True)
    
    print("\n✨ 示例完成！")


if __name__ == "__main__":
    main()
