from __future__ import annotations

from sqlrules.plugins import PLUGIN_API_VERSION
from sqlrules.translators import TranslatorRegistry
from sqlrules_sqlite.pattern import translate_pattern

__version__ = "0.3.0"


class SQLitePlugin:
    """Register SQLite-specific constraint translators.

    The ``pattern`` translator emits ``column REGEXP pattern``. SQLite
    requires the application to register a REGEXP function on the
    connection before executing the resulting SQL.
    """

    name = "sqlite"
    api_version = PLUGIN_API_VERSION

    def register(self, registry: TranslatorRegistry) -> None:
        registry.register_constraint(
            "pattern",
            translate_pattern,
            on_conflict="replace",
        )


__all__ = [
    "SQLitePlugin",
    "__version__",
    "translate_pattern",
]
