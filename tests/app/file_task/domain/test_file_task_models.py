import pytest
from pydantic import ValidationError

from j_file_kit.app.file_task.domain.models import SerialId

pytestmark = pytest.mark.unit


def test_serial_id_from_string_parses_and_normalizes() -> None:
    serial_id = SerialId.from_string("abC-001")

    assert serial_id.prefix == "ABC"
    assert serial_id.number == "001"
    assert str(serial_id) == "ABC-001"


def test_serial_id_model_accepts_string_input() -> None:
    serial_id = SerialId.model_validate("abc_123")

    assert serial_id.prefix == "ABC"
    assert serial_id.number == "123"


def test_serial_id_rejects_invalid_prefix() -> None:
    with pytest.raises(ValidationError):
        SerialId(prefix="A1", number="123")


def test_serial_id_rejects_invalid_number() -> None:
    with pytest.raises(ValidationError):
        SerialId(prefix="AB", number="1a2")


def test_serial_id_from_string_rejects_invalid_format() -> None:
    with pytest.raises(ValueError):
        SerialId.from_string("invalid-serial")
