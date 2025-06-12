from aiogram import types, Router, F
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from callbacks import MyProfileCallback
from enums.bot_entity import BotEntity
from enums.user import UserResponse
from models.user import UserDTO
from services.buy import BuyService
from services.user import UserService
from utils.custom_filters import IsUserExistFilter
from utils.localizator import Localizator

my_profile_router = Router()


@my_profile_router.message(lambda message: message.text == Localizator.get_text(BotEntity.USER, "my_profile"),
                           IsUserExistFilter())
async def my_profile_text_message(message: types.message, session: Session | AsyncSession):
    await my_profile(message=message, session=session)


class MyProfileConstants:
    back_to_main_menu = types.InlineKeyboardButton(
        text=Localizator.get_text(BotEntity.USER, "back_to_my_profile"),
        callback_data=MyProfileCallback.create(level=0).pack())


async def my_profile(**kwargs):
    message = kwargs.get("message") or kwargs.get("callback")
    session = kwargs.get("session")
    user_dto = UserDTO(telegram_id=message.from_user.id)
    msg_text, kb_builder = await UserService.get_my_profile_buttons(user_dto, session)
    if isinstance(message, Message):
        await message.answer(msg_text, reply_markup=kb_builder.as_markup())
    elif isinstance(message, CallbackQuery):
        callback = message
        await callback.message.edit_text(msg_text, reply_markup=kb_builder.as_markup())


async def purchase_history(**kwargs):
    callback = kwargs.get("callback")
    session = kwargs.get("session")
    msg_text, kb_builder = await UserService.get_purchase_history_buttons(callback, session)
    await callback.message.edit_text(text=msg_text, reply_markup=kb_builder.as_markup())




async def get_order_from_history(**kwargs):
    callback = kwargs.get("callback")
    session = kwargs.get("session")
    msg, kb_builder = await BuyService.get_purchase(callback, session)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())




@my_profile_router.callback_query(MyProfileCallback.filter(), IsUserExistFilter())
async def navigate(callback: CallbackQuery, callback_data: MyProfileCallback, session: AsyncSession | Session):
    current_level = callback_data.level

    levels = {
        0: my_profile,
        1: purchase_history,
        2: get_order_from_history
    }

    current_level_function = levels[current_level]

    kwargs = {
        "callback": callback,
        "session": session,
    }

    await current_level_function(**kwargs)
