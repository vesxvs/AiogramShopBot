from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from models.user import UserDTO
from repositories.user import UserRepository
from utils.localizator import Localizator
import config


class LocalizationMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any]
    ) -> Awaitable[Any]:
        session = data.get("session")
        telegram_id = None
        if hasattr(event, "from_user") and event.from_user:
            telegram_id = event.from_user.id
        elif hasattr(event, "message") and getattr(event.message, "from_user", None):
            telegram_id = event.message.from_user.id
        language = "en"
        currency = config.CURRENCY.value
        if telegram_id and session:
            user = await UserRepository.get_by_tgid(telegram_id, session)
            if user:
                if user.language:
                    language = user.language
                if getattr(user, "currency", None):
                    currency = user.currency
        Localizator.set_language(language)
        Localizator.set_currency(currency)
        return await handler(event, data)
