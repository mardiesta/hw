"""Настройка логирования: уровень, формат, вывод в файл и SQL-логи задаются через env."""

import json
import logging
import sys
from datetime import UTC, datetime

from app.config import Settings, get_settings

# Маркер, по которому setup_logging находит собственные обработчики
# и заменяет их при повторном вызове (чужие обработчики не трогаются).
_HANDLER_MARK = "_taskflow_handler"

TEXT_FORMAT = "%(asctime)s %(levelname)-8s [%(name)s] %(message)s"


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def _make_formatter(log_format: str) -> logging.Formatter:
    if log_format == "json":
        return JsonFormatter()
    return logging.Formatter(TEXT_FORMAT)


def setup_logging(settings: Settings | None = None) -> None:
    """Применяет настройки логирования ко всему процессу (app, uvicorn, alembic, sqlalchemy)."""
    settings = settings or get_settings()
    formatter = _make_formatter(settings.log_format)

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]
    if settings.log_file:
        handlers.append(logging.FileHandler(settings.log_file, encoding="utf-8"))

    root = logging.getLogger()
    for old in [h for h in root.handlers if getattr(h, _HANDLER_MARK, False)]:
        root.removeHandler(old)
        old.close()
    for handler in handlers:
        handler.setFormatter(formatter)
        setattr(handler, _HANDLER_MARK, True)
        root.addHandler(handler)
    root.setLevel(settings.log_level)

    # uvicorn и alembic пишут через корневой логгер, чтобы формат и уровень были едиными.
    for name in ("uvicorn", "uvicorn.error", "alembic"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True
        logger.setLevel(logging.NOTSET)

    # Запросы логирует middleware приложения, поэтому access-лог uvicorn отключается.
    access = logging.getLogger("uvicorn.access")
    access.handlers.clear()
    access.propagate = False

    # SQL-запросы (эхо SQLAlchemy) включаются отдельным флагом.
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.log_sql else logging.WARNING
    )
