from __future__ import annotations

from sqlrules.plugins import PLUGIN_API_VERSION
from sqlrules.translators import TranslatorRegistry
from sqlrules_postgresql.array import translate_array_contains, translate_array_overlap
from sqlrules_postgresql.jsonb import translate_json_contains, translate_json_has_key
from sqlrules_postgresql.pattern import translate_pattern
from sqlrules_postgresql.range import translate_range_contains, translate_range_overlap
from sqlrules_postgresql.type_check import translate_type_check

__version__ = "1.0.1"


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
        registry.register_constraint(
            "type_check",
            translate_type_check,
            on_conflict="replace",
        )
        for operator, translator in (
            ("json_contains", translate_json_contains),
            ("json_has_key", translate_json_has_key),
            ("array_contains", translate_array_contains),
            ("array_overlap", translate_array_overlap),
            ("range_contains", translate_range_contains),
            ("range_overlap", translate_range_overlap),
        ):
            registry.register_constraint(operator, translator, on_conflict="replace")


__all__ = [
    "PostgresPlugin",
    "__version__",
    "translate_array_contains",
    "translate_array_overlap",
    "translate_json_contains",
    "translate_json_has_key",
    "translate_pattern",
    "translate_range_contains",
    "translate_range_overlap",
    "translate_type_check",
]
