import logging
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.database import DbSession, engine
from app.logging_config import setup_logging
from app.routers import comments, labels, projects, tasks, users

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    logger.info(
        "Запуск TaskFlow API (LOG_LEVEL=%s, LOG_FORMAT=%s)", settings.log_level, settings.log_format
    )
    try:
        with engine.connect() as connection:
            connection.execute(select(1))
    except SQLAlchemyError:
        logger.critical(
            "База данных недоступна при старте, приложение останавливается", exc_info=True
        )
        raise
    logger.debug("Соединение с базой данных проверено")
    yield
    logger.info("Остановка TaskFlow API")
    engine.dispose()


app = FastAPI(
    title="TaskFlow API",
    version="1.0.0",
    description="REST API для управления задачами команды",
    lifespan=lifespan,
)


@app.middleware("http")
async def log_requests(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        elapsed_ms = (time.perf_counter() - started) * 1000
        logger.error(
            "%s %s -> необработанная ошибка (%.1f мс)", request.method, request.url.path, elapsed_ms
        )
        raise
    elapsed_ms = (time.perf_counter() - started) * 1000
    if response.status_code >= 500:
        level = logging.ERROR
    elif response.status_code >= 400:
        level = logging.WARNING
    else:
        level = logging.INFO
    logger.log(
        level,
        "%s %s -> %s (%.1f мс)",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "Необработанное исключение при %s %s", request.method, request.url.path, exc_info=exc
    )
    return JSONResponse(status_code=500, content={"detail": "Внутренняя ошибка сервера"})


for router in (users.router, projects.router, labels.router, tasks.router, comments.router):
    app.include_router(router)


@app.get("/health", tags=["system"])
def health(db: DbSession):
    try:
        db.execute(select(1))
    except SQLAlchemyError:
        logger.error("Проверка /health: база данных недоступна", exc_info=True)
        return JSONResponse(
            status_code=503,
            content={"status": "error", "database": "unavailable"},
        )
    logger.info("Проверка /health: база данных доступна")
    return {"status": "ok", "database": "ok"}
