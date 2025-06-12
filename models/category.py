from pydantic import BaseModel
from sqlalchemy import Integer, Column, String, JSON

from models.base import Base


class Category(Base):
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True, unique=True)
    name = Column(String, nullable=False, unique=True)
    name_translations = Column(JSON, nullable=False, default={})


class CategoryDTO(BaseModel):
    id: int | None = None
    name: str | None = None
    name_translations: dict | None = None
