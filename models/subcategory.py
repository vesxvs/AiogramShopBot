from pydantic import BaseModel
from sqlalchemy import Integer, Column, String, JSON

from models.base import Base


class Subcategory(Base):
    __tablename__ = 'subcategories'

    id = Column(Integer, primary_key=True, unique=True)
    name = Column(String, nullable=False)
    name_translations = Column(JSON, nullable=False, default={})


class SubcategoryDTO(BaseModel):
    id: int | None
    name: str | None
    name_translations: dict | None = None
