from __future__ import annotations

from sqlrules.plugins import PLUGIN_API_VERSION
from sqlrules.translators import TranslatorRegistry
from sqlrules_sqlite.json import translate_json_contains, translate_json_has_key
from sqlrules_sqlite.pattern import translate_pattern
from sqlrules_sqlite.regexp import register_regexp

__version__ = "1.0.0"


class SQLitePlugin:
    """Register SQLite-specific constraint translators.

    The ``pattern`` translator emits ``column REGEXP pattern``. Call
    :func:`register_regexp` on each SQLite connection before executing
    the resulting SQL.
    """

    name = "sqlite"
    api_version = PLUGIN_API_VERSION

    def register(self, registry: TranslatorRegistry) -> None:
        registry.register_constraint(
            "pattern",
            translate_pattern,
            on_conflict="replace",
        )
        registry.register_constraint(
            "json_contains",
            translate_json_contains,
            on_conflict="replace",
        )
        registry.register_constraint(
            "json_has_key",
            translate_json_has_key,
            on_conflict="replace",
        )


__all__ = [
    "SQLitePlugin",
    "__version__",
    "register_regexp",
    "translate_json_contains",
    "translate_json_has_key",
    "translate_pattern",
]
