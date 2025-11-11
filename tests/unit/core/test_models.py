"""核心模型单元测试

测试核心数据模型，包括 SerialId 模型。
"""

import pytest

from j_file_kit.core.models import SerialId


@pytest.mark.unit
class TestSerialId:
    """测试 SerialId 模型"""

    def test_from_string_with_hyphen(self):
        """测试从连字符分隔的字符串解析"""
        serial_id = SerialId.from_string("ABC-123")
        assert serial_id.prefix == "ABC"
        assert serial_id.number == "123"

    def test_from_string_with_underscore(self):
        """测试从下划线分隔的字符串解析"""
        serial_id = SerialId.from_string("ABC_123")
        assert serial_id.prefix == "ABC"
        assert serial_id.number == "123"

    def test_from_string_without_separator(self):
        """测试从无分隔符的字符串解析"""
        serial_id = SerialId.from_string("ABC123")
        assert serial_id.prefix == "ABC"
        assert serial_id.number == "123"

    def test_from_string_lowercase(self):
        """测试从小写字符串解析（应转换为大写）"""
        serial_id = SerialId.from_string("abc-123")
        assert serial_id.prefix == "ABC"
        assert serial_id.number == "123"

    def test_from_string_mixed_case(self):
        """测试从混合大小写字符串解析"""
        serial_id = SerialId.from_string("AbC-123")
        assert serial_id.prefix == "ABC"
        assert serial_id.number == "123"

    def test_from_string_invalid_format(self):
        """测试无效格式的字符串解析"""
        with pytest.raises(ValueError, match="无效的番号格式"):
            SerialId.from_string("invalid")

    def test_from_string_too_short_prefix(self):
        """测试前缀太短的字符串"""
        with pytest.raises(ValueError, match="无效的番号格式"):
            SerialId.from_string("A-123")

    def test_from_string_too_long_prefix(self):
        """测试前缀太长的字符串"""
        with pytest.raises(ValueError, match="无效的番号格式"):
            SerialId.from_string("ABCDEF-123")

    def test_from_string_too_short_number(self):
        """测试数字太短的字符串"""
        with pytest.raises(ValueError, match="无效的番号格式"):
            SerialId.from_string("ABC-1")

    def test_from_string_too_long_number(self):
        """测试数字太长的字符串"""
        with pytest.raises(ValueError, match="无效的番号格式"):
            SerialId.from_string("ABC-123456")

    def test_str_representation(self):
        """测试字符串表示"""
        serial_id = SerialId(prefix="ABC", number="123")
        assert str(serial_id) == "ABC-123"

    def test_direct_construction(self):
        """测试直接构造"""
        serial_id = SerialId(prefix="ABC", number="123")
        assert serial_id.prefix == "ABC"
        assert serial_id.number == "123"

    def test_direct_construction_lowercase_prefix(self):
        """测试直接构造时小写前缀自动转换为大写"""
        serial_id = SerialId(prefix="abc", number="123")
        assert serial_id.prefix == "ABC"
        assert serial_id.number == "123"

    def test_validation_prefix_too_short(self):
        """测试前缀长度验证（太短）"""
        with pytest.raises(ValueError, match="前缀长度必须在2-5个字符之间"):
            SerialId(prefix="A", number="12")

    def test_validation_prefix_too_long(self):
        """测试前缀长度验证（太长）"""
        with pytest.raises(ValueError, match="前缀长度必须在2-5个字符之间"):
            SerialId(prefix="ABCDEF", number="12")

    def test_validation_prefix_non_alpha(self):
        """测试前缀非字母验证"""
        with pytest.raises(ValueError, match="前缀必须只包含字母"):
            SerialId(prefix="AB1", number="12")

    def test_validation_number_too_short(self):
        """测试数字长度验证（太短）"""
        with pytest.raises(ValueError, match="数字部分长度必须在2-5个字符之间"):
            SerialId(prefix="ABC", number="1")

    def test_validation_number_too_long(self):
        """测试数字长度验证（太长）"""
        with pytest.raises(ValueError, match="数字部分长度必须在2-5个字符之间"):
            SerialId(prefix="ABC", number="123456")

    def test_validation_number_non_digit(self):
        """测试数字非数字验证"""
        with pytest.raises(ValueError, match="数字部分必须只包含数字"):
            SerialId(prefix="ABC", number="12a")

    def test_model_validator_from_string(self):
        """测试从字符串自动解析（向后兼容）"""
        serial_id = SerialId.model_validate("ABC-123")
        assert serial_id.prefix == "ABC"
        assert serial_id.number == "123"

    def test_model_validator_from_dict(self):
        """测试从字典构造"""
        serial_id = SerialId.model_validate({"prefix": "ABC", "number": "123"})
        assert serial_id.prefix == "ABC"
        assert serial_id.number == "123"

    def test_prefix_access(self):
        """测试前缀访问（用于判断系列）"""
        serial_id1 = SerialId(prefix="ABC", number="123")
        serial_id2 = SerialId(prefix="ABC", number="456")
        serial_id3 = SerialId(prefix="XYZ", number="123")

        # 同一系列
        assert serial_id1.prefix == serial_id2.prefix

        # 不同系列
        assert serial_id1.prefix != serial_id3.prefix

