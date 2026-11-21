import logging

from fastapi import APIRouter, Response
from sqlalchemy import select

from app.crud import apply_changes, delete_and_commit, get_or_404, save_and_refresh
from app.database import DbSession
from app.models import Label
from app.schemas import LabelCreate, LabelRead, LabelUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/labels", tags=["labels"])


@router.get("", response_model=list[LabelRead])
def list_labels(db: DbSession):
    return db.scalars(select(Label).order_by(Label.id)).all()


@router.get("/{item_id}", response_model=LabelRead)
def get_label(item_id: int, db: DbSession):
    return get_or_404(db, Label, item_id, "Метка")


@router.post("", response_model=LabelRead, status_code=201)
def create_label(payload: LabelCreate, db: DbSession):
    obj = Label(**payload.model_dump())
    db.add(obj)
    save_and_refresh(db, obj)
    logger.info("Создание: метка, id=%s", obj.id)
    return obj


@router.patch("/{item_id}", response_model=LabelRead)
def update_label(item_id: int, payload: LabelUpdate, db: DbSession):
    obj = get_or_404(db, Label, item_id, "Метка")
    apply_changes(obj, payload)
    save_and_refresh(db, obj)
    logger.info("Обновление: метка, id=%s", item_id)
    return obj


@router.delete("/{item_id}", status_code=204, response_class=Response)
def delete_label(item_id: int, db: DbSession):
    obj = get_or_404(db, Label, item_id, "Метка")
    # У задач с этой меткой поле label_id становится NULL (ON DELETE SET NULL).
    delete_and_commit(db, obj)
    logger.info("Удаление: метка, id=%s", item_id)
    return Response(status_code=204)
