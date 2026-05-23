from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from ..database import SessionLocal
from ..models import Item

router = APIRouter()

class ItemCreate(BaseModel):
    name: str
    description: str | None = None

class ItemRead(BaseModel):
    id: int
    name: str
    description: str | None = None

    class Config:
        orm_mode = True


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=List[ItemRead])
def read_items(db: Session = Depends(get_db)):
    return db.query(Item).all()

@router.post("/", response_model=ItemRead)
def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    db_item = Item(name=item.name, description=item.description)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item
