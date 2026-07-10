from __future__ import annotations

from sqlrules.plugins import PLUGIN_API_VERSION
from sqlrules.translators import TranslatorRegistry
from sqlrules_postgresql.pattern import translate_pattern

__version__ = "0.3.0"


class PostgresPlugin:
    """Register PostgreSQL-specific constraint translators."""

    name = "postgresql"
    api_version = PLUGIN_API_VERSION

    def register(self, registry: TranslatorRegistry) -> None:
        registry.register_constraint(
            "pattern",
            translate_pattern,
            on_conflict="replace",
        )


__all__ = [
    "PostgresPlugin",
    "__version__",
    "translate_pattern",
]
