from json import load
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from callbacks import AddType
from db import session_commit
from enums.bot_entity import BotEntity
from models.item import ItemDTO
from repositories.category import CategoryRepository
from repositories.item import ItemRepository
from repositories.subcategory import SubcategoryRepository
from utils.localizator import Localizator


class ItemService:

    @staticmethod
    async def get_new(session: AsyncSession | Session) -> list[ItemDTO]:
        return await ItemRepository.get_new(session)

    @staticmethod
    async def get_in_stock_items(session: AsyncSession | Session):
        return await ItemRepository.get_in_stock(session)

    @staticmethod
    async def parse_items_json(path_to_file: str, session: AsyncSession | Session):
        with open(path_to_file, 'r', encoding='utf-8') as file:
            items = load(file)
            items_list = []
            for item in items:
                category_data = item.pop('category')
                subcategory_data = item.pop('subcategory')
                category = await CategoryRepository.get_or_create(category_data, session)
                subcategory = await SubcategoryRepository.get_or_create(subcategory_data, session)
                description = item.get('description')
                description_translations = {}
                if isinstance(description, dict):
                    description_translations = {k: v for k, v in description.items() if k != 'en'}
                    description = description.get('en')
                item['description'] = description
                item['description_translations'] = description_translations
                items_list.append(ItemDTO(
                    category_id=category.id,
                    subcategory_id=subcategory.id,
                    **item
                ))
            return items_list

    @staticmethod
    async def parse_items_txt(path_to_file: str, session: AsyncSession | Session):
        with open(path_to_file, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            items_list = []
            for line in lines:
                category_field, subcategory_field, description_field, price, private_data = line.strip().split(';')

                def parse_field(field: str) -> tuple[str, dict]:
                    parts = field.split('|')
                    base = parts[0]
                    translations = {}
                    for part in parts[1:]:
                        if ':' in part:
                            lang, val = part.split(':', 1)
                            translations[lang] = val
                    return base, translations

                cat_en, cat_trans = parse_field(category_field)
                sub_en, sub_trans = parse_field(subcategory_field)
                desc_en, desc_trans = parse_field(description_field)

                category = await CategoryRepository.get_or_create({'en': cat_en, **cat_trans}, session)
                subcategory = await SubcategoryRepository.get_or_create({'en': sub_en, **sub_trans}, session)
                items_list.append(ItemDTO(
                    category_id=category.id,
                    subcategory_id=subcategory.id,
                    price=float(price),
                    description=desc_en,
                    description_translations=desc_trans,
                    private_data=private_data
                ))
            return items_list

    @staticmethod
    async def add_items(path_to_file: str, add_type: AddType, session: AsyncSession | Session) -> str:
        try:
            items = []
            if add_type == AddType.JSON:
                items += await ItemService.parse_items_json(path_to_file, session)
            else:
                items += await ItemService.parse_items_txt(path_to_file, session)
            await ItemRepository.add_many(items, session)
            await session_commit(session)
            return Localizator.get_text(BotEntity.ADMIN, "add_items_success").format(adding_result=len(items))
        except Exception as e:
            return Localizator.get_text(BotEntity.ADMIN, "add_items_err").format(adding_result=e)
        finally:
            Path(path_to_file).unlink(missing_ok=True)
