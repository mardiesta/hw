# TaskFlow API

REST API для управления задачами команды. Стек: Python 3.12, FastAPI, PostgreSQL 16, SQLAlchemy 2, Alembic, Docker Compose.

## Модель данных

| Таблица | Назначение |
|---|---|
| `users` | Пользователи (роли `operator`, `admin`) |
| `projects` | Проекты; при удалении проекта удаляются его задачи и комментарии |
| `labels` | Метки с цветом `#RRGGBB` |
| `tasks` | Задачи проекта; статусы `open`, `in_progress`, `done`; приоритеты `low`, `medium`, `high` |
| `comments` | Комментарии к задаче; при удалении задачи удаляются, автора с комментариями удалить нельзя |

Схема создаётся только миграциями Alembic (`alembic/versions/`).

## Быстрый старт (Docker Compose)

1. Создайте файл с переменными окружения (необязательно, без него используются значения по умолчанию из `docker-compose.yml`):

   ```bash
   cp .env.example .env
   ```

2. Запустите API и PostgreSQL:

   ```bash
   docker compose up --build
   ```

   При старте контейнера `api` автоматически выполняется `alembic upgrade head`, затем запускается сервер.

3. Проверьте работу:

   ```bash
   curl http://localhost:8000/health
   ```

   Ожидаемый ответ: `{"status":"ok","database":"ok"}`.

4. Откройте интерактивную документацию: http://localhost:8000/docs

Данные PostgreSQL хранятся в именованном volume `pgdata` и сохраняются после `docker compose down` и перезапуска. Полностью удалить данные можно командой `docker compose down -v`.

## Запуск без Docker

Нужны Python 3.12 и запущенный PostgreSQL 16.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export DATABASE_URL=postgresql+psycopg://taskflow:change_me@localhost:5432/taskflow
alembic upgrade head
uvicorn app.main:app --reload
```

## Миграции

```bash
export DATABASE_URL=postgresql+psycopg://taskflow:change_me@localhost:5432/taskflow
alembic upgrade head
alembic downgrade base
alembic upgrade head
```

Внутри контейнера:

```bash
docker compose exec api alembic downgrade base
docker compose exec api alembic upgrade head
```

## Тесты

pytest запускают API против одноразового PostgreSQL 16 в Docker: контейнер поднимается автоматически через `testcontainers`, схема создаётся миграциями Alembic. Для запуска нужен работающий Docker.

```bash
pip install -r requirements-dev.txt
pytest
```

Тесты используют отдельную базу из контейнера и не трогают базу из `DATABASE_URL` / `.env`.

## CI

Workflow `.github/workflows/ci.yml` запускается на `push` и `pull_request` и состоит из трёх джоб:

- `lint` — стиль кода: `ruff check .` и `ruff format --check .`;
- `static-analysis` — статический анализ типов: `mypy app`;
- `tests` — `pytest -v`.

Те же проверки локально:

```bash
pip install -r requirements-dev.txt
ruff check . && ruff format --check .
mypy app
pytest
```

## Логирование

Логи пишутся в stderr (и, при заданном `LOG_FILE`, в файл). Настройка выполняется переменными окружения; значения по умолчанию подходят для запуска без `.env`.

| Переменная | Значения | По умолчанию | Назначение |
|---|---|---|---|
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` | `INFO` | Минимальный уровень сообщений |
| `LOG_FORMAT` | `text`, `json` | `text` | Формат строки лога |
| `LOG_SQL` | `true`, `false` | `false` | Логировать SQL-запросы SQLAlchemy |
| `LOG_FILE` | путь | пусто | Дополнительно писать логи в файл |

Что пишется на каждом уровне:

- `DEBUG` — поиск записей, применяемые поля PATCH, параметры фильтров, проверка БД при старте;
- `INFO` — запуск и остановка, создание, изменение и удаление записей, успешный `/health`, успешные запросы (2xx, 3xx);
- `WARNING` — `404`, `409`, `422` и другие ответы `4xx`;
- `ERROR` — недоступная БД в `/health`, ответы `5xx` и необработанные исключения;
- `CRITICAL` — БД недоступна при старте: приложение останавливается.

Пример:

```bash
LOG_LEVEL=DEBUG LOG_FORMAT=json docker compose up --build
```

## Эндпоинты

| Метод | URL | Результат |
|---|---|---|
| `GET` | `/v1/{resource}` | Список записей (`200`) |
| `GET` | `/v1/{resource}/{id}` | Одна запись (`200`, `404`) |
| `POST` | `/v1/{resource}` | Создание (`201`, `422`, `409`) |
| `PATCH` | `/v1/{resource}/{id}` | Частичное обновление (`200`, `404`, `422`, `409`) |
| `DELETE` | `/v1/{resource}/{id}` | Удаление (`204`, `404`, `409`) |

`{resource}`: `users`, `projects`, `labels`, `tasks`, `comments`.

Дополнительно:

- `GET /v1/tasks?project_id=1&status=open` — фильтр задач по проекту и статусу (оба параметра необязательные);
- `GET /v1/comments?task_id=1` — комментарии задачи;
- `GET /health` — проверка соединения с БД;
- `GET /docs` — Swagger UI.

Коды ошибок:

- `404` — запись не найдена;
- `422` — ошибка входных данных (неверный статус, формат цвета или email, пустой комментарий, лишние поля вроде `id` или `created_at`);
- `409` — дубликат уникального значения (например, `email`) или нарушение внешнего ключа (например, несуществующий `project_id`, либо попытка удалить пользователя с комментариями).

## Примеры запросов

Создать пользователя:

```bash
curl -X POST http://localhost:8000/v1/users \
  -H "Content-Type: application/json" \
  -d '{"email": "anna@example.com", "display_name": "Anna", "role": "admin"}'
```

Ответ `201`:

```json
{"id": 1, "email": "anna@example.com", "display_name": "Anna", "role": "admin", "created_at": "2026-10-17T10:00:00Z"}
```

Создать проект, метку и задачу:

```bash
curl -X POST http://localhost:8000/v1/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "Website", "description": "Corporate site"}'

curl -X POST http://localhost:8000/v1/labels \
  -H "Content-Type: application/json" \
  -d '{"name": "bug", "color": "#ff0000"}'

curl -X POST http://localhost:8000/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{"project_id": 1, "assignee_id": 1, "label_id": 1, "title": "Fix login", "priority": "high"}'
```

Добавить комментарий к задаче:

```bash
curl -X POST http://localhost:8000/v1/comments \
  -H "Content-Type: application/json" \
  -d '{"task_id": 1, "author_id": 1, "body": "Reproduced on Safari"}'
```

Получить открытые задачи проекта:

```bash
curl "http://localhost:8000/v1/tasks?project_id=1&status=open"
```

Перевести задачу в `done` (частичное обновление):

```bash
curl -X PATCH http://localhost:8000/v1/tasks/1 \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

Пример ошибки — дубликат email (`409`):

```bash
curl -X POST http://localhost:8000/v1/users \
  -H "Content-Type: application/json" \
  -d '{"email": "anna@example.com", "display_name": "Anna again"}'
```

Удалить проект вместе с его задачами и комментариями (`204`):

```bash
curl -i -X DELETE http://localhost:8000/v1/projects/1
```

## Структура проекта

```text
.
├── app/
│   ├── main.py          # создание приложения, /health
│   ├── config.py        # настройки из переменных окружения
│   ├── database.py      # engine, сессии, базовый класс моделей
│   ├── models.py        # таблицы SQLAlchemy
│   ├── schemas.py       # Pydantic-модели запросов и ответов
│   ├── crud.py          # общие функции CRUD и перевод ошибок БД в HTTP
│   └── routers/         # эндпоинты по ресурсам
├── alembic/
│   ├── env.py           # подключение по DATABASE_URL
│   └── versions/        # миграции
├── alembic.ini
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── .env.example
└── requirements.txt
```
