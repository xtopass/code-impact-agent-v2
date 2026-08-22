"""国际化模块"""
from src.i18n.manager import (
    I18nManager,
    Locale,
    get_i18n,
    init_i18n,
    translate
)

__all__ = [
    "I18nManager",
    "Locale",
    "get_i18n",
    "init_i18n",
    "translate"
]
