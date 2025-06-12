import traceback
from aiogram import types, F, Router
from aiogram.filters import Command
from aiogram.types import ErrorEvent, Message, BufferedInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import config
from config import SUPPORT_LINK
import logging
from bot import dp, main, redis
from enums.bot_entity import BotEntity
from middleware.database import DBSessionMiddleware
from middleware.throttling_middleware import ThrottlingMiddleware
from middleware.localization_middleware import LocalizationMiddleware
from models.user import UserDTO
from repositories.user import UserRepository
from multibot import main as main_multibot
from handlers.user.cart import cart_router
from handlers.admin.admin import admin_router
from handlers.user.all_categories import all_categories_router
from handlers.user.my_profile import my_profile_router
from services.notification import NotificationService
from services.user import UserService
from utils.custom_filters import IsUserExistFilter
from utils.localizator import Localizator
from db import session_commit
from callbacks import LanguageCallback

logging.basicConfig(level=logging.INFO)
main_router = Router()


def get_main_menu(telegram_id: int) -> types.ReplyKeyboardMarkup:
    all_categories_button = types.KeyboardButton(text=Localizator.get_text(BotEntity.USER, "all_categories"))
    my_profile_button = types.KeyboardButton(text=Localizator.get_text(BotEntity.USER, "my_profile"))
    faq_button = types.KeyboardButton(text=Localizator.get_text(BotEntity.USER, "faq"))
    help_button = types.KeyboardButton(text=Localizator.get_text(BotEntity.USER, "help"))
    admin_menu_button = types.KeyboardButton(text=Localizator.get_text(BotEntity.ADMIN, "menu"))
    cart_button = types.KeyboardButton(text=Localizator.get_text(BotEntity.USER, "cart"))
    keyboard = [[all_categories_button, my_profile_button], [faq_button, help_button], [cart_button]]
    if telegram_id in config.ADMIN_ID_LIST:
        keyboard.append([admin_menu_button])
    return types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2, keyboard=keyboard)


@main_router.message(Command(commands=["start"]))
async def start(message: types.message):
    kb_builder = InlineKeyboardBuilder()
    for lang_file in Path("l10n").glob("*.json"):
        code = lang_file.stem
        kb_builder.button(text=code, callback_data=LanguageCallback.create(code).pack())
    await message.answer(Localizator.get_text(BotEntity.COMMON, "choose_language"), reply_markup=kb_builder.as_markup())


@main_router.callback_query(LanguageCallback.filter())
async def set_language(callback: types.CallbackQuery, callback_data: LanguageCallback, session: AsyncSession | Session):
    telegram_id = callback.from_user.id
    await UserService.create_if_not_exist(UserDTO(
        telegram_username=callback.from_user.username,
        telegram_id=telegram_id,
        language=callback_data.code
    ), session)
    await UserRepository.update(UserDTO(telegram_id=telegram_id, language=callback_data.code), session)
    await session_commit(session)
    start_markup = get_main_menu(telegram_id)
    await callback.message.edit_text(Localizator.get_text(BotEntity.COMMON, "start_message"), reply_markup=start_markup)


@main_router.message(Command(commands=["help"]))
async def cmd_help(message: types.Message, session: AsyncSession | Session):
    telegram_id = message.from_user.id
    await UserService.create_if_not_exist(UserDTO(
        telegram_username=message.from_user.username,
        telegram_id=telegram_id
    ), session)
    start_markup = get_main_menu(telegram_id)
    await message.answer(Localizator.get_text(BotEntity.COMMON, "start_message"), reply_markup=start_markup)


@main_router.message(F.text == Localizator.get_text(BotEntity.USER, "faq"), IsUserExistFilter())
async def faq(message: types.message):
    await message.answer(Localizator.get_text(BotEntity.USER, "faq_string"))


@main_router.message(F.text == Localizator.get_text(BotEntity.USER, "help"), IsUserExistFilter())
async def support(message: types.message):
    admin_keyboard_builder = InlineKeyboardBuilder()

    admin_keyboard_builder.button(text=Localizator.get_text(BotEntity.USER, "help_button"), url=SUPPORT_LINK)
    await message.answer(Localizator.get_text(BotEntity.USER, "help_string"),
                         reply_markup=admin_keyboard_builder.as_markup())


@main_router.error(F.update.message.as_("message"))
async def error_handler(event: ErrorEvent, message: Message):
    await message.answer(Localizator.get_text(BotEntity.COMMON, "oops"))
    traceback_str = traceback.format_exc()
    admin_notification = (
        f"Critical error caused by {event.exception}\n\n"
        f"Stack trace:\n{traceback_str}"
    )
    if len(admin_notification) > 4096:
        byte_array = bytearray(admin_notification, 'utf-8')
        admin_notification = BufferedInputFile(byte_array, "exception.txt")
    await NotificationService.send_to_admins(admin_notification, None)


throttling_middleware = ThrottlingMiddleware(redis)
users_routers = Router()
users_routers.include_routers(
    all_categories_router,
    my_profile_router,
    cart_router
)
users_routers.message.middleware(throttling_middleware)
users_routers.callback_query.middleware(throttling_middleware)
main_router.include_router(admin_router)
main_router.include_routers(users_routers)
main_router.message.middleware(DBSessionMiddleware())
main_router.callback_query.middleware(DBSessionMiddleware())
main_router.message.middleware(LocalizationMiddleware())
main_router.callback_query.middleware(LocalizationMiddleware())

if __name__ == '__main__':
    if config.MULTIBOT:
        main_multibot(main_router)
    else:
        dp.include_router(main_router)
        main()
