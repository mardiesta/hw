import logging

from fastapi import APIRouter, Response
from sqlalchemy import select

from app.crud import apply_changes, delete_and_commit, get_or_404, save_and_refresh
from app.database import DbSession
from app.models import Task
from app.schemas import TaskCreate, TaskRead, TaskStatus, TaskUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskRead])
def list_tasks(db: DbSession, project_id: int | None = None, status: TaskStatus | None = None):
    logger.debug("Список задач: project_id=%s status=%s", project_id, status)
    stmt = select(Task).order_by(Task.id)
    if project_id is not None:
        stmt = stmt.where(Task.project_id == project_id)
    if status is not None:
        stmt = stmt.where(Task.status == status)
    return db.scalars(stmt).all()


@router.get("/{item_id}", response_model=TaskRead)
def get_task(item_id: int, db: DbSession):
    return get_or_404(db, Task, item_id, "Задача")


@router.post("", response_model=TaskRead, status_code=201)
def create_task(payload: TaskCreate, db: DbSession):
    obj = Task(**payload.model_dump())
    db.add(obj)
    save_and_refresh(db, obj)
    logger.info("Создание: задача, id=%s", obj.id)
    return obj


@router.patch("/{item_id}", response_model=TaskRead)
def update_task(item_id: int, payload: TaskUpdate, db: DbSession):
    obj = get_or_404(db, Task, item_id, "Задача")
    apply_changes(obj, payload)
    save_and_refresh(db, obj)
    logger.info("Обновление: задача, id=%s", item_id)
    return obj


@router.delete("/{item_id}", status_code=204, response_class=Response)
def delete_task(item_id: int, db: DbSession):
    obj = get_or_404(db, Task, item_id, "Задача")
    # Комментарии задачи удаляются каскадно на уровне БД (ON DELETE CASCADE).
    delete_and_commit(db, obj)
    logger.info("Удаление: задача, id=%s", item_id)
    return Response(status_code=204)
