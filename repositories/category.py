import math

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import config
from db import session_execute, session_flush
from models.category import Category, CategoryDTO
from models.item import Item


class CategoryRepository:
    @staticmethod
    async def get(page: int, session: Session | AsyncSession) -> list[CategoryDTO]:
        stmt = (select(Category)
                .join(Item, Item.category_id == Category.id)
                .where(Item.is_sold == False)
                .distinct()
                .limit(config.PAGE_ENTRIES)
                .offset(page * config.PAGE_ENTRIES)
                .group_by(Category.name))
        category_names = await session_execute(stmt, session)
        categories = category_names.scalars().all()
        return [CategoryDTO.model_validate(category, from_attributes=True) for category in categories]

    @staticmethod
    async def get_maximum_page(session: Session | AsyncSession) -> int:
        unique_categories_subquery = (
            select(Category.id)
            .join(Item, Item.category_id == Category.id)
            .filter(Item.is_sold == 0)
            .distinct()
        ).alias('unique_categories')
        stmt = select(func.count()).select_from(unique_categories_subquery)
        max_page = await session_execute(stmt, session)
        max_page = max_page.scalar_one()
        if max_page % config.PAGE_ENTRIES == 0:
            return max_page / config.PAGE_ENTRIES - 1
        else:
            return math.trunc(max_page / config.PAGE_ENTRIES)

    @staticmethod
    async def get_by_id(category_id: int, session: Session | AsyncSession):
        stmt = select(Category).where(Category.id == category_id)
        category = await session_execute(stmt, session)
        return CategoryDTO.model_validate(category.scalar(), from_attributes=True)

    @staticmethod
    async def get_to_delete(page: int, session: Session | AsyncSession) -> list[CategoryDTO]:
        stmt = select(Category).join(Item, Item.category_id == Category.id
                                     ).where(Item.is_sold == 0).distinct().limit(config.PAGE_ENTRIES).offset(
            page * config.PAGE_ENTRIES).group_by(Category.name)
        categories = await session_execute(stmt, session)
        return [CategoryDTO.model_validate(category, from_attributes=True) for category in
                categories.scalars().all()]

    @staticmethod
    async def get_or_create(category_data: dict | str, session: Session | AsyncSession):
        if isinstance(category_data, dict):
            category_name = category_data.get("en")
            translations = {k: v for k, v in category_data.items() if k != "en"}
        else:
            category_name = category_data
            translations = {}
        stmt = select(Category).where(Category.name == category_name)
        category = await session_execute(stmt, session)
        category = category.scalar()
        if category is None:
            new_category_obj = Category(name=category_name, name_translations=translations)
            session.add(new_category_obj)
            await session_flush(session)
            return new_category_obj
        else:
            if translations:
                category.name_translations.update(translations)
            return category
