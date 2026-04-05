"""Domain models 单元测试

覆盖 SerialId、FileTaskRunReport、TaskConfig 等模型的业务逻辑。
"""

from datetime import datetime

import pytest

from j_file_kit.app.file_task.application.config import JavVideoOrganizeConfig
from j_file_kit.app.file_task.domain.models import (
    FileTaskRunReport,
    SerialId,
    TaskConfig,
)

pytestmark = pytest.mark.unit


class TestSerialIdFromString:
    """SerialId.from_string() 解析逻辑"""

    def test_valid_hyphen_format(self) -> None:
        result = SerialId.from_string("ABC-123")
        assert result.prefix == "ABC"
        assert result.number == "123"

    def test_valid_underscore_format(self) -> None:
        result = SerialId.from_string("ABC_123")
        assert result.prefix == "ABC"
        assert result.number == "123"

    def test_valid_no_separator_format(self) -> None:
        result = SerialId.from_string("ABC123")
        assert result.prefix == "ABC"
        assert result.number == "123"

    def test_lowercase_prefix_normalized_to_upper(self) -> None:
        result = SerialId.from_string("abc-123")
        assert result.prefix == "ABC"

    def test_min_length_prefix(self) -> None:
        result = SerialId.from_string("AB-12")
        assert result.prefix == "AB"
        assert result.number == "012"

    def test_max_length_prefix(self) -> None:
        result = SerialId.from_string("ABCDE-12345")
        assert result.prefix == "ABCDE"
        assert result.number == "12345"

    def test_invalid_format_raises(self) -> None:
        with pytest.raises(ValueError, match="无效的番号格式"):
            SerialId.from_string("invalid")

    def test_prefix_too_short_raises(self) -> None:
        with pytest.raises(ValueError, match="无效的番号格式"):
            SerialId.from_string("A-123")

    def test_number_too_short_raises(self) -> None:
        with pytest.raises(ValueError, match="无效的番号格式"):
            SerialId.from_string("AB-1")


class TestSerialIdFieldValidator:
    """SerialId field_validator 验证逻辑"""

    def test_prefix_non_alpha_raises(self) -> None:
        with pytest.raises(ValueError, match="前缀必须只包含字母"):
            SerialId(prefix="AB1", number="123")

    def test_prefix_six_letters_valid(self) -> None:
        """6个字母的前缀合法（支持 serial_id_combinations 中的 (6,x) 组合）"""
        sid = SerialId(prefix="ABCDEF", number="123")
        assert sid.prefix == "ABCDEF"

    def test_prefix_too_long_raises(self) -> None:
        with pytest.raises(ValueError, match="前缀长度必须在2-6个字符之间"):
            SerialId(prefix="ABCDEFG", number="123")

    def test_number_non_digit_raises(self) -> None:
        with pytest.raises(ValueError, match="数字部分必须只包含数字"):
            SerialId(prefix="ABC", number="12a")

    def test_number_too_long_raises(self) -> None:
        with pytest.raises(ValueError, match="数字部分长度必须在2-5个字符之间"):
            SerialId(prefix="ABC", number="123456")

    def test_number_two_digits_padded_to_three(self) -> None:
        """2位数字构造时自动补零至3位"""
        sid = SerialId(prefix="ABC", number="12")
        assert sid.number == "012"
        assert str(sid) == "ABC-012"

    def test_number_three_digits_unchanged(self) -> None:
        """3位数字保持不变"""
        sid = SerialId(prefix="ABC", number="123")
        assert sid.number == "123"

    def test_number_four_digits_unchanged(self) -> None:
        """4位数字保持不变"""
        sid = SerialId(prefix="ABC", number="1234")
        assert sid.number == "1234"


class TestSerialIdModelValidator:
    """SerialId model_validator 字符串自动解析"""

    def test_string_input_parsed(self) -> None:
        result = SerialId.model_validate("XYZ-789")
        assert result.prefix == "XYZ"
        assert result.number == "789"

    def test_dict_input_passed_through(self) -> None:
        result = SerialId.model_validate({"prefix": "AB", "number": "12"})
        assert result.prefix == "AB"
        assert result.number == "012"


class TestSerialIdStr:
    """SerialId 字符串表示"""

    def test_str_format(self) -> None:
        sid = SerialId(prefix="ABC", number="123")
        assert str(sid) == "ABC-123"


class TestFileTaskRunReport:
    """FileTaskRunReport 派生属性和 update_from_stats"""

    def test_success_rate_zero_items(self) -> None:
        report = FileTaskRunReport(
            run_name="test",
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_items=0,
            success_items=0,
            error_items=0,
            skipped_items=0,
            warning_items=0,
            total_duration_ms=0.0,
        )
        assert report.success_rate == 0.0

    def test_success_rate_calculated(self) -> None:
        report = FileTaskRunReport(
            run_name="test",
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_items=10,
            success_items=8,
            error_items=0,
            skipped_items=0,
            warning_items=0,
            total_duration_ms=0.0,
        )
        assert report.success_rate == 0.8

    def test_error_rate_zero_items(self) -> None:
        report = FileTaskRunReport(
            run_name="test",
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_items=0,
            success_items=0,
            error_items=0,
            skipped_items=0,
            warning_items=0,
            total_duration_ms=0.0,
        )
        assert report.error_rate == 0.0

    def test_error_rate_calculated(self) -> None:
        report = FileTaskRunReport(
            run_name="test",
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_items=10,
            success_items=0,
            error_items=2,
            skipped_items=0,
            warning_items=0,
            total_duration_ms=0.0,
        )
        assert report.error_rate == 0.2

    def test_duration_seconds(self) -> None:
        report = FileTaskRunReport(
            run_name="test",
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_items=0,
            success_items=0,
            error_items=0,
            skipped_items=0,
            warning_items=0,
            total_duration_ms=5000.0,
        )
        assert report.duration_seconds == 5.0

    def test_update_from_stats(self) -> None:
        report = FileTaskRunReport(
            run_name="test",
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_items=0,
            success_items=0,
            error_items=0,
            skipped_items=0,
            warning_items=0,
            total_duration_ms=0.0,
        )
        stats = {
            "total_items": 5,
            "success_items": 3,
            "error_items": 1,
            "skipped_items": 1,
            "warning_items": 0,
            "total_duration_ms": 100.5,
        }
        report.update_from_stats(stats)
        assert report.total_items == 5
        assert report.success_items == 3
        assert report.error_items == 1
        assert report.skipped_items == 1
        assert report.total_duration_ms == 100.5

    def test_update_from_stats_partial_dict_uses_defaults_for_missing_keys(
        self,
    ) -> None:
        report = FileTaskRunReport(
            run_name="test",
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_items=10,
            success_items=0,
            error_items=0,
            skipped_items=0,
            warning_items=0,
            total_duration_ms=0.0,
        )
        report.update_from_stats({"success_items": 7})
        assert report.success_items == 7
        assert report.total_items == 0


class TestTaskConfigGetConfig:
    """TaskConfig.get_config() 字典转 Pydantic 模型"""

    def test_get_config_returns_typed_model(self) -> None:
        config = TaskConfig(
            type="jav_video_organizer",
            enabled=True,
            config={
                "inbox_dir": None,
                "sorted_dir": None,
                "unsorted_dir": None,
                "archive_dir": None,
                "misc_dir": None,
                "video_extensions": [".mp4"],
                "image_extensions": [".jpg"],
                "subtitle_extensions": [".srt"],
                "archive_extensions": [".zip"],
                "misc_file_delete_rules": {},
            },
        )
        result: JavVideoOrganizeConfig = config.get_config(JavVideoOrganizeConfig)
        assert isinstance(result, JavVideoOrganizeConfig)
        assert result.video_extensions == {".mp4"}
