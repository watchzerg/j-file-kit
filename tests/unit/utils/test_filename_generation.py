"""文件名生成单元测试

测试文件名重构相关的功能，包括：
- generate_new_filename 函数的各种场景
- 番号移动到文件名开头的处理
- 各种分隔符格式的处理
- trim 功能测试
- 保持文件扩展名不变

功能说明：
- 将文件名分解为4部分：番号之前、番号、番号之后、扩展名
- 对第1、2、3部分执行trim操作（去除前后的空格、连字符、下划线、@符号、#符号）
- 根据第1部分trim后是否为空判断番号是否在开头
- 按不同规则拼接新文件名
"""

from j_file_kit.utils.filename_generation import generate_new_filename


class TestFilenameGeneration:
    """测试文件名生成功能

    测试根据番号重构文件名的功能，支持：
    - 将番号移动到文件名开头
    - 处理各种分隔符格式
    - trim 功能
    - 保持文件扩展名不变
    """

    def test_generate_new_filename_already_at_start(self, tmp_path):
        """测试番号已在开头的情况"""
        original_path = tmp_path / "ABC-001_video.mp4"
        new_path, serial_id = generate_new_filename(original_path)
        expected = tmp_path / "ABC-001 video.mp4"
        assert new_path == expected
        assert serial_id == "ABC-001"

    def test_generate_new_filename_move_to_start(self, tmp_path):
        """测试番号移动到开头的情况"""
        original_path = tmp_path / "video_ABC-001_hd.mp4"
        new_path, serial_id = generate_new_filename(original_path)
        expected = tmp_path / "ABC-001 video-serialId-hd.mp4"
        assert new_path == expected
        assert serial_id == "ABC-001"

    def test_generate_new_filename_no_serial_id(self, tmp_path):
        """测试无番号的情况"""
        original_path = tmp_path / "video.mp4"
        new_path, serial_id = generate_new_filename(original_path)
        assert new_path == original_path
        assert serial_id is None

    def test_generate_new_filename_already_standard_format(self, tmp_path):
        """测试文件名已经是标准格式的情况"""
        original_path = tmp_path / "ABC-001.mp4"
        new_path, serial_id = generate_new_filename(original_path)
        # 文件名已经是标准格式，应该返回相同路径
        assert new_path == original_path
        assert serial_id == "ABC-001"


class TestFilenameGenerationEdgeCases:
    """测试文件名生成的边界情况

    测试各种边界情况和特殊场景：
    - 不同文件扩展名
    - 复杂文件名结构
    - 特殊字符处理
    - 长文件名处理
    - trim 功能测试
    """

    def test_different_file_extensions(self, tmp_path):
        """测试不同文件扩展名"""

        # 测试各种文件扩展名
        extensions = [".mp4", ".avi", ".mkv", ".jpg", ".png", ".txt", ".zip"]

        for ext in extensions:
            original_path = tmp_path / f"video_ABC-001_hd{ext}"
            new_path, serial_id = generate_new_filename(original_path)
            expected = tmp_path / f"ABC-001 video-serialId-hd{ext}"
            assert new_path == expected, f"Failed for extension: {ext}"

    def test_complex_filename_structures(self, tmp_path):
        """测试复杂文件名结构"""

        test_cases = [
            # (原始文件名, 期望的新文件名)
            (
                "[2023]video_ABC-001[1080p].mp4",
                "ABC-001 [2023]video-serialId-[1080p].mp4",
            ),
            (
                "(Uncensored)video_ABC-001(Leaked).mp4",
                "ABC-001 (Uncensored)video-serialId-(Leaked).mp4",
            ),
            ("video_ABC-001_v2_Final.mp4", "ABC-001 video-serialId-v2_Final.mp4"),
            ("video_ABC-001-Repack.mp4", "ABC-001 video-serialId-Repack.mp4"),
            (
                "video_ABC-001_Extended_Cut.mp4",
                "ABC-001 video-serialId-Extended_Cut.mp4",
            ),
        ]

        for original_name, expected_name in test_cases:
            original_path = tmp_path / original_name
            new_path, serial_id = generate_new_filename(original_path)
            expected_path = tmp_path / expected_name
            assert new_path == expected_path, f"Failed for: {original_name}"
            assert serial_id == "ABC-001"

    def test_special_characters_in_filename(self, tmp_path):
        """测试文件名中的特殊字符"""

        special_char_tests = [
            ("video_ABC-001@special.mp4", "ABC-001 video-serialId-special.mp4"),
            ("video_ABC-001#tag.mp4", "ABC-001 video-serialId-tag.mp4"),
            ("video_ABC-001.2023.mp4", "ABC-001 video-serialId-.2023.mp4"),
            ("video_ABC-001[HD].mp4", "ABC-001 video-serialId-[HD].mp4"),
            ("video_ABC-001(1080p).mp4", "ABC-001 video-serialId-(1080p).mp4"),
        ]

        for original_name, expected_name in special_char_tests:
            original_path = tmp_path / original_name
            new_path, serial_id = generate_new_filename(original_path)
            expected_path = tmp_path / expected_name
            assert new_path == expected_path, (
                f"Failed for special chars: {original_name}"
            )

    def test_long_filenames(self, tmp_path):
        """测试长文件名"""

        # 生成长文件名
        long_prefix = "very_long_prefix_" * 20
        long_suffix = "very_long_suffix" * 20

        original_name = f"{long_prefix}ABC-001{long_suffix}.mp4"
        original_path = tmp_path / original_name
        new_path, serial_id = generate_new_filename(original_path)
        # trim 会去掉下划线，所以期望值中下划线被去掉
        expected_name = f"ABC-001 {long_prefix.rstrip('_')}-serialId-{long_suffix}.mp4"
        expected_path = tmp_path / expected_name

        assert new_path == expected_path, "Failed for long filename"
        assert serial_id == "ABC-001"

    def test_no_extension_files(self, tmp_path):
        """测试无扩展名的文件"""

        original_path = tmp_path / "video_ABC-001_hd"
        new_path, serial_id = generate_new_filename(original_path)
        expected = tmp_path / "ABC-001 video-serialId-hd"
        assert new_path == expected
        assert serial_id == "ABC-001"

    def test_multiple_serial_ids_in_filename(self, tmp_path):
        """测试文件名中包含多个番号的情况"""

        # 当文件名中有多个番号时，应该处理第一个匹配的番号
        test_cases = [
            ("video_ABC-001_DEF-456_hd.mp4", "ABC-001 video-serialId-DEF-456_hd.mp4"),
            (
                "video_XYZ-999_ABC-001_GHI-789.mp4",
                "XYZ-999 video-serialId-ABC-001_GHI-789.mp4",
            ),
        ]

        for original_name, expected_name in test_cases:
            original_path = tmp_path / original_name
            new_path, serial_id = generate_new_filename(original_path)
            expected_path = tmp_path / expected_name
            assert new_path == expected_path, (
                f"Failed for multiple serials: {original_name}"
            )

    def test_case_sensitivity(self, tmp_path):
        """测试大小写敏感性"""

        case_tests = [
            ("video_abc-001_hd.mp4", "ABC-001 video-serialId-hd.mp4"),  # 小写番号
            ("video_AbC-001_hd.mp4", "ABC-001 video-serialId-hd.mp4"),  # 混合大小写番号
            ("video_ABC-001_hd.mp4", "ABC-001 video-serialId-hd.mp4"),  # 大写番号
        ]

        for original_name, expected_name in case_tests:
            original_path = tmp_path / original_name
            new_path, serial_id = generate_new_filename(original_path)
            expected_path = tmp_path / expected_name
            assert new_path == expected_path, f"Failed for case test: {original_name}"


class TestTrimFunctionality:
    """测试 trim 功能

    测试各种分隔符的 trim 处理：
    - 空格、连字符、下划线、@符号、#符号的 trim
    - 番号在开头但需要规范化的场景
    - 第三部分为空和不为空的情况
    """

    def test_serial_at_start_with_different_separators(self, tmp_path):
        """测试番号在开头但分隔符不同的情况"""

        test_cases = [
            # (原始文件名, 期望的新文件名) - 番号在开头时也要重构
            ("abc-001_video.mp4", "ABC-001 video.mp4"),
            ("ABC001video.mp4", "ABC-001 video.mp4"),
            ("ABC-001.mp4", "ABC-001.mp4"),
            ("ABC-001", "ABC-001"),
            ("_ABC-001_hd.mp4", "ABC-001 hd.mp4"),
            ("-ABC-001-.mp4", "ABC-001.mp4"),
            ("ABC-001_1080p_uncensored.mp4", "ABC-001 1080p_uncensored.mp4"),
        ]

        for original_name, expected_name in test_cases:
            original_path = tmp_path / original_name
            new_path, serial_id = generate_new_filename(original_path)
            expected_path = tmp_path / expected_name
            assert new_path == expected_path, (
                f"Failed for serial at start: {original_name}"
            )
            assert serial_id == "ABC-001"

    def test_serial_not_at_start_with_trim(self, tmp_path):
        """测试番号不在开头的情况，包含 trim 处理"""

        test_cases = [
            # (原始文件名, 期望的新文件名)
            ("video_ABC-001_hd.mp4", "ABC-001 video-serialId-hd.mp4"),
            ("prefix_ABC-001.mp4", "ABC-001 prefix-serialId.mp4"),
            ("prefix_ABC-001", "ABC-001 prefix-serialId"),
            ("[2023]_ABC-001_[1080p].mp4", "ABC-001 [2023]-serialId-[1080p].mp4"),
            (
                "my_video_ABC001_final_cut.avi",
                "ABC-001 my_video-serialId-final_cut.avi",
            ),
        ]

        for original_name, expected_name in test_cases:
            original_path = tmp_path / original_name
            new_path, serial_id = generate_new_filename(original_path)
            expected_path = tmp_path / expected_name
            assert new_path == expected_path, (
                f"Failed for serial not at start: {original_name}"
            )
            assert serial_id == "ABC-001"

    def test_trim_edge_cases(self, tmp_path):
        """测试 trim 的边界情况"""

        test_cases = [
            # (原始文件名, 期望的新文件名)
            ("___ABC-001___.mp4", "ABC-001.mp4"),  # 全是分隔符，番号在开头，重构
            (
                "...ABC-001...mp4",
                "ABC-001 ...-serialId-...mp4",
            ),  # 点号分隔符，第1部分不为空
            ("video__ABC-001__hd.mp4", "ABC-001 video-serialId-hd.mp4"),  # 双下划线
            (
                "  video  _  ABC-001  _  hd  .mp4",
                "ABC-001 video-serialId-hd.mp4",
            ),  # 多个空格
            ("@video@_ABC-001_#hd#.mp4", "ABC-001 video-serialId-hd.mp4"),  # @和#符号
            ("#ABC-001@.mp4", "ABC-001.mp4"),  # @和#符号在开头和结尾
        ]

        for original_name, expected_name in test_cases:
            original_path = tmp_path / original_name
            new_path, serial_id = generate_new_filename(original_path)
            expected_path = tmp_path / expected_name
            assert new_path == expected_path, (
                f"Failed for trim edge case: {original_name}"
            )
            assert serial_id == "ABC-001"

    def test_third_part_empty_vs_not_empty(self, tmp_path):
        """测试第三部分为空和不为空的情况"""

        test_cases = [
            # 第三部分为空的情况
            ("video_ABC-001.mp4", "ABC-001 video-serialId.mp4"),
            ("prefix_ABC-001", "ABC-001 prefix-serialId"),
            ("ABC-001.mp4", "ABC-001.mp4"),  # 番号在开头，第三部分为空，重构
            # 第三部分不为空的情况
            ("video_ABC-001_hd.mp4", "ABC-001 video-serialId-hd.mp4"),
            ("prefix_ABC-001_suffix", "ABC-001 prefix-serialId-suffix"),
            ("ABC-001_hd.mp4", "ABC-001 hd.mp4"),  # 番号在开头，第三部分不为空，重构
        ]

        for original_name, expected_name in test_cases:
            original_path = tmp_path / original_name
            new_path, serial_id = generate_new_filename(original_path)
            expected_path = tmp_path / expected_name
            assert new_path == expected_path, (
                f"Failed for third part test: {original_name}"
            )
            assert serial_id == "ABC-001"
