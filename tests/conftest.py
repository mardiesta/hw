"""Временный PostgreSQL 16 в Docker, миграции Alembic и тестовый клиент API."""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from testcontainers.community.postgres import PostgresContainer

ROOT = Path(__file__).resolve().parent.parent

TRUNCATE_ALL = "TRUNCATE comments, tasks, labels, projects, users RESTART IDENTITY CASCADE"


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    """Поднимает одноразовый контейнер postgres:16 и направляет приложение на него.

    DATABASE_URL выставляется ДО импорта приложения: app/database.py создаёт engine
    при импорте. Переменная окружения имеет приоритет над .env, поэтому реальная база
    из .env тестами не затрагивается.
    """
    with PostgresContainer("postgres:16", driver="psycopg") as postgres:
        url = postgres.get_connection_url()
        os.environ["DATABASE_URL"] = url

        # Схема создаётся реальными миграциями, а не Base.metadata.create_all().
        config = Config(str(ROOT / "alembic.ini"))
        config.set_main_option("script_location", str(ROOT / "alembic"))
        config.set_main_option("path_separator", "os")
        command.upgrade(config, "head")

        yield url


@pytest.fixture(scope="session")
def engine(database_url: str) -> Iterator[Engine]:
    eng = create_engine(database_url)
    yield eng
    eng.dispose()


@pytest.fixture(scope="session")
def client(database_url: str) -> Iterator[TestClient]:
    # Импорт приложения внутри фикстуры: к этому моменту DATABASE_URL уже задан.
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clean_db(engine: Engine) -> None:
    """Очищает все таблицы перед каждым тестом, чтобы тесты не зависели друг от друга."""
    with engine.begin() as conn:
        conn.execute(text(TRUNCATE_ALL))
