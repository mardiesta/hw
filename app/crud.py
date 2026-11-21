import logging
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Коды ошибок PostgreSQL (SQLSTATE), которые переводятся в HTTP-ответы.
UNIQUE_VIOLATION = "23505"
FOREIGN_KEY_VIOLATION = "23503"
NOT_NULL_VIOLATION = "23502"
CHECK_VIOLATION = "23514"


def get_or_404(db: Session, model: type[Any], item_id: int, label: str) -> Any:
    logger.debug("Поиск %s: model=%s id=%s", label, model.__name__, item_id)
    obj = db.get(model, item_id)
    if obj is None:
        logger.warning("%s с id=%s не найден(а)", label, item_id)
        raise HTTPException(status_code=404, detail=f"{label} с id={item_id} не найден(а)")
    logger.debug("%s с id=%s найден(а)", label, item_id)
    return obj


def apply_changes(obj: Any, payload: BaseModel) -> None:
    """Переносит только поля, которые клиент передал явно (PATCH)."""
    changes = payload.model_dump(exclude_unset=True)
    logger.debug("Применяются изменения %s: %s", type(obj).__name__, changes)
    for field, value in changes.items():
        setattr(obj, field, value)


def _integrity_error_to_http(exc: IntegrityError, conflict_message: str | None) -> HTTPException:
    orig = exc.orig
    sqlstate = getattr(orig, "sqlstate", None) or ""
    diag = getattr(orig, "diag", None)
    detail = (
        getattr(diag, "message_detail", None)
        or getattr(diag, "message_primary", None)
        or str(orig).splitlines()[0]
    )

    if sqlstate == UNIQUE_VIOLATION:
        error = HTTPException(
            status_code=409, detail=f"Конфликт: такое значение уже существует ({detail})"
        )
    elif sqlstate == FOREIGN_KEY_VIOLATION:
        message = conflict_message or f"Конфликт: нарушена связь с другой записью ({detail})"
        error = HTTPException(status_code=409, detail=message)
    elif sqlstate in (NOT_NULL_VIOLATION, CHECK_VIOLATION) or sqlstate.startswith("22"):
        error = HTTPException(status_code=422, detail=f"Некорректные данные ({detail})")
    else:
        error = HTTPException(
            status_code=409, detail="Конфликт: нарушено ограничение целостности данных"
        )
    logger.warning(
        "Нарушение ограничения БД (sqlstate=%s) -> HTTP %s: %s", sqlstate, error.status_code, detail
    )
    return error


def _commit(db: Session, conflict_message: str | None = None) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise _integrity_error_to_http(exc, conflict_message) from exc


def save_and_refresh(db: Session, obj: Any) -> None:
    """Сохраняет объект и перечитывает его, чтобы подтянуть значения, заполненные БД."""
    _commit(db)
    db.refresh(obj)


def delete_and_commit(db: Session, obj: Any, conflict_message: str | None = None) -> None:
    db.delete(obj)
    _commit(db, conflict_message)
