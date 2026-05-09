"""SerialId 领域模型测试。"""

import pytest

from j_file_kit.app.file_task.domain.serial_id import (
    SerialId,
    effective_serial_digit_len,
    serial_number_raw_is_valid,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("raw", "prefix", "number"),
    [
        ("ABC-123", "ABC", "123"),
        ("ABC_123", "ABC", "123"),
        ("ABC123", "ABC", "123"),
        ("abc-123", "ABC", "123"),
        ("AB-123", "AB", "123"),
        ("ABCDE-1234", "ABCDE", "1234"),
        ("AB-01234", "AB", "1234"),
    ],
)
def test_from_string_success(raw: str, prefix: str, number: str) -> None:
    result = SerialId.from_string(raw)
    assert result.prefix == prefix
    assert result.number == number


@pytest.mark.parametrize("raw", ["AB-12345", "invalid", "A-123", "AB-12"])
def test_from_string_invalid(raw: str) -> None:
    with pytest.raises(ValueError):
        SerialId.from_string(raw)


def test_effective_serial_len() -> None:
    assert effective_serial_digit_len("01234") == 4
    assert effective_serial_digit_len("12345") == 5
    assert effective_serial_digit_len("000") == 3


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("01234", True), ("12345", False), ("12", False)],
)
def test_serial_number_raw_is_valid(raw: str, expected: bool) -> None:
    assert serial_number_raw_is_valid(raw) is expected


@pytest.mark.parametrize(
    ("payload", "match"),
    [
        ({"prefix": "AB1", "number": "123"}, "前缀必须只包含字母"),
        ({"prefix": "ABCDEFG", "number": "123"}, "前缀长度必须在2-6个字符之间"),
        ({"prefix": "ABC", "number": "12a"}, "数字部分必须只包含数字"),
        ({"prefix": "ABC", "number": "123456"}, "数字部分须为3-5位"),
        ({"prefix": "ABC", "number": "12"}, "数字部分须为3-5位"),
    ],
)
def test_field_validation_failures(payload: dict[str, str], match: str) -> None:
    with pytest.raises(ValueError, match=match):
        SerialId(**payload)


def test_number_normalization() -> None:
    assert SerialId(prefix="ABC", number="123").number == "123"
    assert SerialId(prefix="ABC", number="1234").number == "1234"
    assert SerialId(prefix="ABC", number="0123").number == "123"
    assert str(SerialId(prefix="ABC", number="0123")) == "ABC-123"
    assert SerialId(prefix="ABCDE", number="00001").number == "001"


def test_model_validate_accepts_string_and_dict() -> None:
    from_string = SerialId.model_validate("XYZ-789")
    assert from_string.prefix == "XYZ"
    assert from_string.number == "789"

    from_dict = SerialId.model_validate({"prefix": "AB", "number": "012"})
    assert from_dict.prefix == "AB"
    assert from_dict.number == "012"


def test_str_representation() -> None:
    assert str(SerialId(prefix="ABC", number="123")) == "ABC-123"
