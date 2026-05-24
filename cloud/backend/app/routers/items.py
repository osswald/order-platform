from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from ..deps import get_db
from ..models import Item

router = APIRouter()


class ItemCreate(BaseModel):
    name: str
    description: str | None = None


class ItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None


@router.get("/", response_model=list[ItemRead])
def read_items(db: Session = Depends(get_db)) -> list[Item]:
    return db.query(Item).all()


@router.post("/", response_model=ItemRead)
def create_item(item: ItemCreate, db: Session = Depends(get_db)) -> Item:
    db_item = Item(name=item.name, description=item.description)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item
