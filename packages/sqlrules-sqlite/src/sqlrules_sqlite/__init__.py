from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlrules.backend import prepare_sqlite_scalar
from sqlrules.ir import CompilationContext, PreparedValue, RuleField
from sqlrules.plugins import PLUGIN_API_VERSION
from sqlrules.translators import TranslatorRegistry
from sqlrules_sqlite.json import translate_json_contains, translate_json_has_key
from sqlrules_sqlite.length import translate_max_length, translate_min_length
from sqlrules_sqlite.pattern import translate_pattern
from sqlrules_sqlite.regexp import register_regexp
from sqlrules_sqlite.runtime import register_sqlite_functions

__version__ = "2.0.0"


class SQLitePlugin:
    """Register SQLite-specific constraint translators.

    Pattern and text-coercion expressions emit ``column REGEXP pattern``;
    length constraints use SQLRules' Unicode-aware character counter. Call
    :func:`register_sqlite_functions` on each SQLite connection before
    executing SQL that needs these functions. ``register_regexp`` remains as a
    backward-compatible alias.
    """

    name = "sqlite"
    api_version = PLUGIN_API_VERSION

    def __init__(self, *, server_version: tuple[int, ...] | None = None) -> None:
        self.server_version = tuple(server_version) if server_version is not None else None

    def capabilities(self) -> Mapping[str, Any]:
        return {
            "backend": self.name,
            "server_version": self.server_version,
            "native_scalar_types": ("bool", "int", "float", "str"),
            "safe_text_numeric_conversion": True,
            "safe_text_numeric_targets": ("int", "float"),
            "assumptions": (
                "Runtime typeof() storage classes determine bool/int/float/text values.",
                "Register SQLRules SQLite functions on each connection when using text "
                "coercion, patterns, or string length constraints.",
                "Date/time/UUID and exact Decimal checks require "
                "a future explicit storage adapter.",
            ),
        }

    def prepare_value(
        self,
        column: Any,
        field: RuleField,
        context: CompilationContext,
    ) -> PreparedValue:
        return prepare_sqlite_scalar(column, field, context)

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
    "register_sqlite_functions",
    "translate_json_contains",
    "translate_json_has_key",
    "translate_pattern",
]
