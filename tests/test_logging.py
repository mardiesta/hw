"""Логирование: уровни, настройка через env и CRITICAL при недоступной БД."""

import logging
from collections.abc import Iterator
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.exc import OperationalError

from app.config import Settings
from app.logging_config import JsonFormatter, setup_logging


@pytest.fixture(autouse=True)
def restore_logging() -> Iterator[None]:
    yield
    setup_logging()


def _settings(database_url: str, **overrides: object) -> Settings:
    return Settings(database_url=database_url, **overrides)  # type: ignore[arg-type]


def test_missing_record_logs_warning(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)

    assert client.get("/v1/users/999999").status_code == 404

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert any(r.name == "app.crud" and "не найден" in r.getMessage() for r in warnings)


def test_successful_create_logs_info(
    client: TestClient, caplog: pytest.LogCaptureFixture, database_url: str
) -> None:
    setup_logging(_settings(database_url, log_level="INFO"))

    response = client.post("/v1/labels", json={"name": "bug", "color": "#ff0000"})

    assert response.status_code == 201
    infos = [r for r in caplog.records if r.levelno == logging.INFO]
    assert any("Создание: метка" in r.getMessage() for r in infos)


def test_log_level_error_hides_warnings(
    client: TestClient, caplog: pytest.LogCaptureFixture, database_url: str
) -> None:
    setup_logging(_settings(database_url, log_level="ERROR"))

    assert client.get("/v1/users/999999").status_code == 404

    assert [r for r in caplog.records if r.levelno < logging.ERROR] == []


def test_log_level_debug_shows_debug(
    client: TestClient, caplog: pytest.LogCaptureFixture, database_url: str
) -> None:
    setup_logging(_settings(database_url, log_level="DEBUG"))

    assert client.get("/v1/users/999999").status_code == 404

    assert any(r.levelno == logging.DEBUG and r.name == "app.crud" for r in caplog.records)


def test_log_level_is_case_insensitive_and_validated(database_url: str) -> None:
    assert _settings(database_url, log_level="debug").log_level == "DEBUG"

    with pytest.raises(ValidationError):
        _settings(database_url, log_level="verbose")


def test_json_formatter_outputs_valid_json() -> None:
    record = logging.LogRecord(
        "app.test", logging.WARNING, __file__, 1, "привет %s", ("мир",), None
    )

    line = JsonFormatter().format(record)

    assert '"level": "WARNING"' in line
    assert '"message": "привет мир"' in line


def test_unreachable_database_at_startup_logs_critical(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    from app import main

    def broken_connect() -> None:
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    monkeypatch.setattr(main, "engine", SimpleNamespace(connect=broken_connect))

    with pytest.raises(OperationalError), TestClient(main.app):
        pass

    assert any(r.levelno == logging.CRITICAL for r in caplog.records)
