from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.database import DbSession
from app.routers import comments, labels, projects, tasks, users

app = FastAPI(
    title="TaskFlow API",
    version="1.0.0",
    description="REST API для управления задачами команды",
)

for router in (users.router, projects.router, labels.router, tasks.router, comments.router):
    app.include_router(router)


@app.get("/health", tags=["system"])
def health(db: DbSession):
    try:
        db.execute(select(1))
    except SQLAlchemyError:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "database": "unavailable"},
        )
    return {"status": "ok", "database": "ok"}
