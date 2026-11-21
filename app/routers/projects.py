import logging

from fastapi import APIRouter, Response
from sqlalchemy import select

from app.crud import apply_changes, delete_and_commit, get_or_404, save_and_refresh
from app.database import DbSession
from app.models import Project
from app.schemas import ProjectCreate, ProjectRead, ProjectUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/projects", tags=["projects"])


@router.get("", response_model=list[ProjectRead])
def list_projects(db: DbSession):
    return db.scalars(select(Project).order_by(Project.id)).all()


@router.get("/{item_id}", response_model=ProjectRead)
def get_project(item_id: int, db: DbSession):
    return get_or_404(db, Project, item_id, "Проект")


@router.post("", response_model=ProjectRead, status_code=201)
def create_project(payload: ProjectCreate, db: DbSession):
    obj = Project(**payload.model_dump())
    db.add(obj)
    save_and_refresh(db, obj)
    logger.info("Создание: проект, id=%s", obj.id)
    return obj


@router.patch("/{item_id}", response_model=ProjectRead)
def update_project(item_id: int, payload: ProjectUpdate, db: DbSession):
    obj = get_or_404(db, Project, item_id, "Проект")
    apply_changes(obj, payload)
    save_and_refresh(db, obj)
    logger.info("Обновление: проект, id=%s", item_id)
    return obj


@router.delete("/{item_id}", status_code=204, response_class=Response)
def delete_project(item_id: int, db: DbSession):
    obj = get_or_404(db, Project, item_id, "Проект")
    # Задачи и их комментарии удаляются каскадно на уровне БД (ON DELETE CASCADE).
    delete_and_commit(db, obj)
    logger.info("Удаление: проект, id=%s", item_id)
    return Response(status_code=204)
