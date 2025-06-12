import json
import contextvars
import config
from enums.bot_entity import BotEntity


_language_var = contextvars.ContextVar("language", default=config.BOT_LANGUAGE)


class Localizator:

    @staticmethod
    def get_text(entity: BotEntity, key: str) -> str:
        language = _language_var.get()
        localization_filename = f"./l10n/{language}.json"
        with open(localization_filename, "r", encoding="UTF-8") as f:
            if entity == BotEntity.ADMIN:
                return json.loads(f.read())["admin"][key]
            elif entity == BotEntity.USER:
                return json.loads(f.read())["user"][key]
            else:
                return json.loads(f.read())["common"][key]

    @staticmethod
    def set_language(language: str) -> None:
        _language_var.set(language)

    @staticmethod
    def get_currency_symbol():
        return Localizator.get_text(BotEntity.COMMON, f"{config.CURRENCY.value.lower()}_symbol")

    @staticmethod
    def get_currency_text():
        return Localizator.get_text(BotEntity.COMMON, f"{config.CURRENCY.value.lower()}_text")
