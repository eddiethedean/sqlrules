from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlrules.backend import prepare_scalar
from sqlrules.ir import CompilationContext, PreparedValue, RuleField
from sqlrules.plugins import PLUGIN_API_VERSION
from sqlrules.translators import TranslatorRegistry
from sqlrules_postgresql.array import translate_array_contains, translate_array_overlap
from sqlrules_postgresql.jsonb import translate_json_contains, translate_json_has_key
from sqlrules_postgresql.pattern import translate_pattern
from sqlrules_postgresql.range import translate_range_contains, translate_range_overlap

__version__ = "2.0.0"


class PostgresPlugin:
    """Register PostgreSQL-specific constraint translators."""

    name = "postgresql"
    api_version = PLUGIN_API_VERSION

    def __init__(self, *, server_version: tuple[int, ...] | None = None) -> None:
        self.server_version = tuple(server_version) if server_version is not None else None

    def capabilities(self) -> Mapping[str, Any]:
        return {
            "backend": self.name,
            "server_version": self.server_version,
            "native_scalar_types": (
                "bool",
                "int",
                "float",
                "decimal",
                "str",
                "date",
                "datetime",
                "time",
                "uuid",
            ),
            "safe_text_numeric_conversion": self.server_version is not None
            and self.server_version >= (16, 0),
            "safe_text_numeric_targets": (
                ("int", "float", "decimal")
                if self.server_version is not None and self.server_version >= (16, 0)
                else ()
            ),
            "assumptions": ("PostgreSQL native column types provide logical type evidence.",),
        }

    def prepare_value(
        self,
        column: Any,
        field: RuleField,
        context: CompilationContext,
    ) -> PreparedValue:
        return prepare_scalar(column, field, context, backend=self.name)

    def register(self, registry: TranslatorRegistry) -> None:
        registry.register_constraint(
            "pattern",
            translate_pattern,
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
]
