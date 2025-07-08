"""Property handlers for different Notion property types."""

from .base import PropertyHandler, PropertyHandlerRegistry
from .text import TitleHandler, RichTextHandler
from .number import NumberHandler
from .select import SelectHandler, MultiSelectHandler, StatusHandler
from .date import DateHandler
from .people import PeopleHandler
from .files import FilesHandler
from .checkbox import CheckboxHandler
from .url import URLHandler, EmailHandler, PhoneHandler
from .relation import RelationHandler
from .formula import FormulaHandler
from .rollup import RollupHandler
from .timestamp import CreatedTimeHandler, LastEditedTimeHandler
from .user import CreatedByHandler, LastEditedByHandler

__all__ = [
    "PropertyHandler",
    "PropertyHandlerRegistry",
    "TitleHandler",
    "RichTextHandler",
    "NumberHandler",
    "SelectHandler",
    "MultiSelectHandler",
    "StatusHandler",
    "DateHandler",
    "PeopleHandler",
    "FilesHandler",
    "CheckboxHandler",
    "URLHandler",
    "EmailHandler",
    "PhoneHandler",
    "RelationHandler",
    "FormulaHandler",
    "RollupHandler",
    "CreatedTimeHandler",
    "LastEditedTimeHandler",
    "CreatedByHandler",
    "LastEditedByHandler",
]