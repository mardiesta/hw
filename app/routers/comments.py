import logging

from fastapi import APIRouter, Response
from sqlalchemy import select

from app.crud import apply_changes, delete_and_commit, get_or_404, save_and_refresh
from app.database import DbSession
from app.models import Comment
from app.schemas import CommentCreate, CommentRead, CommentUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/comments", tags=["comments"])


@router.get("", response_model=list[CommentRead])
def list_comments(db: DbSession, task_id: int | None = None):
    logger.debug("Список комментариев: task_id=%s", task_id)
    stmt = select(Comment).order_by(Comment.id)
    if task_id is not None:
        stmt = stmt.where(Comment.task_id == task_id)
    return db.scalars(stmt).all()


@router.get("/{item_id}", response_model=CommentRead)
def get_comment(item_id: int, db: DbSession):
    return get_or_404(db, Comment, item_id, "Комментарий")


@router.post("", response_model=CommentRead, status_code=201)
def create_comment(payload: CommentCreate, db: DbSession):
    obj = Comment(**payload.model_dump())
    db.add(obj)
    save_and_refresh(db, obj)
    logger.info("Создание: комментарий, id=%s", obj.id)
    return obj


@router.patch("/{item_id}", response_model=CommentRead)
def update_comment(item_id: int, payload: CommentUpdate, db: DbSession):
    obj = get_or_404(db, Comment, item_id, "Комментарий")
    apply_changes(obj, payload)
    save_and_refresh(db, obj)
    logger.info("Обновление: комментарий, id=%s", item_id)
    return obj


@router.delete("/{item_id}", status_code=204, response_class=Response)
def delete_comment(item_id: int, db: DbSession):
    obj = get_or_404(db, Comment, item_id, "Комментарий")
    delete_and_commit(db, obj)
    logger.info("Удаление: комментарий, id=%s", item_id)
    return Response(status_code=204)
