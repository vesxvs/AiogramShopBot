from typing import Dict

from utils.localizator import Localizator


def get_translated(base: str, translations: Dict[str, str] | None) -> str:
    language = Localizator.get_language()
    if translations and language in translations:
        return translations[language]
    return base
