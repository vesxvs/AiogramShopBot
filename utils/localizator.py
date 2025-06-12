import json
import contextvars
import config
from enums.bot_entity import BotEntity


_language_var = contextvars.ContextVar("language", default=config.BOT_LANGUAGE)
_currency_var = contextvars.ContextVar("currency", default=config.CURRENCY.value)


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
    def get_language() -> str:
        return _language_var.get()

    @staticmethod
    def set_currency(currency: str) -> None:
        _currency_var.set(currency)

    @staticmethod
    def get_currency() -> str:
        return _currency_var.get()

    @staticmethod
    def get_currency_symbol(currency: str | None = None):
        if currency is None:
            currency = Localizator.get_currency()
        symbols = Localizator.get_text(BotEntity.COMMON, "currency_symbols")
        return symbols.get(currency, currency)

    @staticmethod
    def get_currency_text(currency: str | None = None):
        if currency is None:
            currency = Localizator.get_currency()
        names = Localizator.get_text(BotEntity.COMMON, "currency_names")
        return names.get(currency, currency)

    @staticmethod
    def get_currency_list_text() -> str:
        names = Localizator.get_text(BotEntity.COMMON, "currency_names")
        lines = [f"{code} - {name}{' *' if code in Localizator.get_text(BotEntity.COMMON, 'not_amex') else ''}" for code, name in names.items()]
        return "\n".join(lines)
