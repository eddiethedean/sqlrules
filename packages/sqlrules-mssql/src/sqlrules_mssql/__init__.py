from __future__ import annotations

from sqlrules.plugins import PLUGIN_API_VERSION
from sqlrules.translators import TranslatorRegistry
from sqlrules_mssql.json import translate_json_contains, translate_json_has_key
from sqlrules_mssql.length import translate_max_length, translate_min_length

__version__ = "1.0.0"


class MssqlPlugin:
    """Register SQL Server constraint translators.

    Does not register ``pattern`` — SQL Server has no portable regex operator
    that SQLRules can emit deterministically. Provide a custom translator if
    needed.
    """

    name = "mssql"
    api_version = PLUGIN_API_VERSION

    def register(self, registry: TranslatorRegistry) -> None:
        registry.register_constraint(
            "min_length",
            translate_min_length,
            on_conflict="replace",
        )
        registry.register_constraint(
            "max_length",
            translate_max_length,
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
    "MssqlPlugin",
    "__version__",
    "translate_json_contains",
    "translate_json_has_key",
    "translate_max_length",
    "translate_min_length",
]
