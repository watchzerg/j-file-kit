import logging
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace

import pytest
from loguru import logger as loguru_logger

from j_file_kit.shared.utils import logging as logging_utils

pytestmark = pytest.mark.unit


class DummyFrame:
    def __init__(self, filename: str) -> None:
        self.f_code = SimpleNamespace(co_filename=filename)
        self.f_back = None


@dataclass
class InterceptCalls:
    opt: tuple[int, object | None] | None = None
    log: tuple[str, str] | None = None


@dataclass
class SetupCalls:
    remove: int = 0
    add: list[AddCall] = field(default_factory=list)
    basic_config: BasicConfigCall | None = None
    set_level: int | None = None


@dataclass
class AddCall:
    args: tuple[object, ...]
    kwargs: dict[str, object]


@dataclass
class BasicConfigCall:
    args: tuple[object, ...]
    kwargs: dict[str, object]


@dataclass
class ConfigureCalls:
    ensure: tuple[Path, bool] | None = None
    add: FileAddCall | None = None


@dataclass
class FileAddCall:
    path: str
    kwargs: dict[str, object]


def test_intercept_handler_emits_loguru_standard_level(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = InterceptCalls()

    def _level(name: str) -> SimpleNamespace:
        return SimpleNamespace(name=name)

    def _log(level: str, message: str) -> None:
        calls.log = (level, message)

    def _opt(depth: int, exception: object | None) -> SimpleNamespace:
        calls.opt = (depth, exception)
        return SimpleNamespace(log=_log)

    monkeypatch.setattr(loguru_logger, "level", _level)
    monkeypatch.setattr(loguru_logger, "opt", _opt)
    monkeypatch.setattr(logging, "currentframe", lambda: DummyFrame("app.py"))

    record = logging.LogRecord("test", logging.INFO, "x.py", 10, "hello", (), None)
    handler = logging_utils.InterceptHandler()

    handler.emit(record)

    assert calls.opt == (2, None)
    assert calls.log == ("INFO", "hello")


def test_intercept_handler_falls_back_to_levelno(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = InterceptCalls()

    def _level(_name: str) -> SimpleNamespace:
        raise ValueError

    def _log(level: str, message: str) -> None:
        calls.log = (level, message)

    def _opt(depth: int, exception: object | None) -> SimpleNamespace:
        calls.opt = (depth, exception)
        return SimpleNamespace(log=_log)

    monkeypatch.setattr(loguru_logger, "level", _level)
    monkeypatch.setattr(loguru_logger, "opt", _opt)
    monkeypatch.setattr(logging, "currentframe", lambda: DummyFrame("app.py"))

    record = logging.LogRecord("test", 15, "x.py", 10, "custom", (), None)
    record.levelname = "CUSTOM"
    handler = logging_utils.InterceptHandler()

    handler.emit(record)

    assert calls.log == ("15", "custom")


def test_setup_logging_uses_development_handler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = SetupCalls()

    def _remove() -> None:
        calls.remove += 1

    def _add(*args: object, **kwargs: object) -> int:
        calls.add.append(AddCall(args=args, kwargs=kwargs))
        return 1

    def _basic_config(*args: object, **kwargs: object) -> None:
        calls.basic_config = BasicConfigCall(args=args, kwargs=kwargs)

    def _set_level(level: int) -> None:
        calls.set_level = level

    monkeypatch.delenv("J_FILE_KIT_ENV", raising=False)
    monkeypatch.setattr(loguru_logger, "remove", _remove)
    monkeypatch.setattr(loguru_logger, "add", _add)
    monkeypatch.setattr(logging, "basicConfig", _basic_config)
    monkeypatch.setattr(logging.root, "setLevel", _set_level)

    logging_utils.setup_logging()

    assert calls.remove == 1
    add_kwargs = calls.add[0].kwargs
    assert add_kwargs["level"] == "INFO"
    assert add_kwargs["colorize"] is True
    assert add_kwargs["diagnose"] is True
    assert add_kwargs.get("serialize") in (None, False)
    assert calls.basic_config is not None
    basic_config = calls.basic_config.kwargs
    assert basic_config["level"] == logging.INFO
    assert basic_config["force"] is True
    handlers = basic_config["handlers"]
    assert isinstance(handlers, list)
    assert len(handlers) == 1
    assert isinstance(handlers[0], logging_utils.InterceptHandler)
    assert calls.set_level == logging.INFO


def test_setup_logging_uses_production_handler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = SetupCalls()

    def _remove() -> None:
        calls.remove += 1

    def _add(*args: object, **kwargs: object) -> int:
        calls.add.append(AddCall(args=args, kwargs=kwargs))
        return 1

    def _basic_config(*args: object, **kwargs: object) -> None:
        calls.basic_config = BasicConfigCall(args=args, kwargs=kwargs)

    def _set_level(level: int) -> None:
        calls.set_level = level

    monkeypatch.setenv("J_FILE_KIT_ENV", "production")
    monkeypatch.setattr(loguru_logger, "remove", _remove)
    monkeypatch.setattr(loguru_logger, "add", _add)
    monkeypatch.setattr(logging, "basicConfig", _basic_config)
    monkeypatch.setattr(logging.root, "setLevel", _set_level)

    logging_utils.setup_logging()

    assert calls.remove == 1
    add_kwargs = calls.add[0].kwargs
    assert add_kwargs["serialize"] is True
    assert add_kwargs["diagnose"] is False
    assert add_kwargs["level"] == "INFO"
    assert calls.basic_config is not None
    basic_config = calls.basic_config.kwargs
    assert basic_config["level"] == logging.INFO
    assert calls.set_level == logging.INFO


def test_configure_task_logger_adds_jsonl_handler(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls = ConfigureCalls()

    def _ensure_directory(path: Path, parents: bool = True) -> None:
        calls.ensure = (path, parents)

    def _add(path: str, **kwargs: object) -> int:
        calls.add = FileAddCall(path=path, kwargs=kwargs)
        return 99

    monkeypatch.setattr(logging_utils, "ensure_directory", _ensure_directory)
    monkeypatch.setattr(loguru_logger, "add", _add)

    handler_id = logging_utils.configure_task_logger(tmp_path, "task", 9)

    assert handler_id == 99
    assert calls.ensure == (tmp_path, True)
    assert calls.add is not None
    assert calls.add.path == str(tmp_path / "task_9.jsonl")
    add_kwargs = calls.add.kwargs
    assert add_kwargs["serialize"] is True
    assert add_kwargs["level"] == "DEBUG"
    assert add_kwargs["rotation"] is None
    assert add_kwargs["retention"] is None
    assert add_kwargs["compression"] is None


def test_remove_task_logger_calls_logger_remove(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[int] = []

    def _remove(handler_id: int) -> None:
        calls.append(handler_id)

    monkeypatch.setattr(loguru_logger, "remove", _remove)

    logging_utils.remove_task_logger(42)

    assert calls == [42]
