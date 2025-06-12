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
from callbacks import LanguageCallback, CurrencyCallback
from enums.currency import Currency

logging.basicConfig(level=logging.INFO)
main_router = Router()

LANGUAGE_NAMES = {
    "en": "English",
    "de": "Deutsch",
    "pl": "Polski",
    "ru": "Русский",
    "uk": "Українська",
    "be": "Беларуская",
}

LANGUAGE_FLAGS = {
    "en": "🇬🇧",
    "de": "🇩🇪",
    "pl": "🇵🇱",
    "ru": "🇷🇺",
    "uk": "🇺🇦",
    "be": "🇧🇾",
}


def get_currency_keyboard() -> types.ReplyKeyboardMarkup:
    buttons = [types.KeyboardButton(text=c.value) for c in Currency]
    keyboard: list[list[types.KeyboardButton]] = []
    row: list[types.KeyboardButton] = []
    for i, button in enumerate(buttons, 1):
        row.append(button)
        if i % 4 == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    return types.ReplyKeyboardMarkup(resize_keyboard=True, keyboard=keyboard)


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
        name = LANGUAGE_NAMES.get(code, code)
        flag = LANGUAGE_FLAGS.get(code, "")
        button_text = f"{flag} {name}".strip()
        kb_builder.button(text=button_text, callback_data=LanguageCallback.create(code).pack())
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
    Localizator.set_language(callback_data.code)
    currency_list = Localizator.get_currency_list_text()
    msg = Localizator.get_text(BotEntity.COMMON, "choose_currency").format(
        default_currency=config.CURRENCY.value
    )
    await callback.message.delete()
    await callback.message.answer(
        f"{msg}\n{currency_list}", reply_markup=get_currency_keyboard()
    )


@main_router.message(lambda message: message.text in [c.value for c in Currency])
async def set_currency(message: types.Message, session: AsyncSession | Session):
    currency_code = message.text
    await UserRepository.update(UserDTO(telegram_id=message.from_user.id, currency=currency_code), session)
    await session_commit(session)
    Localizator.set_currency(currency_code)
    start_markup = get_main_menu(message.from_user.id)
    await message.answer(Localizator.get_text(BotEntity.COMMON, "start_message"), reply_markup=start_markup)


@main_router.message(Command(commands=["help"]))
async def cmd_help(message: types.Message, session: AsyncSession | Session):
    telegram_id = message.from_user.id
    await UserService.create_if_not_exist(UserDTO(
        telegram_username=message.from_user.username,
        telegram_id=telegram_id
    ), session)
    start_markup = get_main_menu(telegram_id)
    await message.answer(Localizator.get_text(BotEntity.COMMON, "start_message"), reply_markup=start_markup)


@main_router.message(lambda message: message.text == Localizator.get_text(BotEntity.USER, "faq"),
                     IsUserExistFilter())
async def faq(message: types.message):
    await message.answer(Localizator.get_text(BotEntity.USER, "faq_string"))


@main_router.message(lambda message: message.text == Localizator.get_text(BotEntity.USER, "help"),
                     IsUserExistFilter())
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

dp.message.outer_middleware(DBSessionMiddleware())
dp.callback_query.outer_middleware(DBSessionMiddleware())
dp.message.outer_middleware(LocalizationMiddleware())
dp.callback_query.outer_middleware(LocalizationMiddleware())

if __name__ == '__main__':
    if config.MULTIBOT:
        main_multibot(main_router)
    else:
        dp.include_router(main_router)
        main()
