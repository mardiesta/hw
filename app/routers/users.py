import logging

from fastapi import APIRouter, Response
from sqlalchemy import select

from app.crud import apply_changes, delete_and_commit, get_or_404, save_and_refresh
from app.database import DbSession
from app.models import User
from app.schemas import UserCreate, UserRead, UserUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/users", tags=["users"])

CONFLICT_MESSAGE = "Пользователь связан с комментариями и не может быть удалён"


@router.get("", response_model=list[UserRead])
def list_users(db: DbSession):
    return db.scalars(select(User).order_by(User.id)).all()


@router.get("/{item_id}", response_model=UserRead)
def get_user(item_id: int, db: DbSession):
    return get_or_404(db, User, item_id, "Пользователь")


@router.post("", response_model=UserRead, status_code=201)
def create_user(payload: UserCreate, db: DbSession):
    obj = User(**payload.model_dump())
    db.add(obj)
    save_and_refresh(db, obj)
    logger.info("Создание: пользователь, id=%s", obj.id)
    return obj


@router.patch("/{item_id}", response_model=UserRead)
def update_user(item_id: int, payload: UserUpdate, db: DbSession):
    obj = get_or_404(db, User, item_id, "Пользователь")
    apply_changes(obj, payload)
    save_and_refresh(db, obj)
    logger.info("Обновление: пользователь, id=%s", item_id)
    return obj


@router.delete("/{item_id}", status_code=204, response_class=Response)
def delete_user(item_id: int, db: DbSession):
    obj = get_or_404(db, User, item_id, "Пользователь")
    delete_and_commit(db, obj, conflict_message=CONFLICT_MESSAGE)
    logger.info("Удаление: пользователь, id=%s", item_id)
    return Response(status_code=204)
