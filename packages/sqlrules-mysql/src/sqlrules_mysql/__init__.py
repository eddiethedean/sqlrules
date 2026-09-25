from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlrules.backend import prepare_scalar
from sqlrules.ir import CompilationContext, PreparedValue, RuleField
from sqlrules.plugins import PLUGIN_API_VERSION
from sqlrules.translators import TranslatorRegistry
from sqlrules_mysql.fulltext import translate_fulltext_match
from sqlrules_mysql.json import translate_json_contains, translate_json_has_key
from sqlrules_mysql.length import translate_max_length, translate_min_length
from sqlrules_mysql.pattern import translate_pattern

__version__ = "2.0.0"


class MysqlPlugin:
    """Register MySQL / MariaDB constraint translators."""

    name = "mysql"
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
            ),
            "safe_text_numeric_conversion": self.server_version is not None
            and self.server_version >= (8, 0),
            "safe_text_numeric_targets": (
                ("int",)
                if self.server_version is not None and self.server_version >= (8, 0)
                else ()
            ),
            "assumptions": (
                "MySQL 8.0 REGEXP and native column types provide the advertised type evidence.",
                "Lax integer/float/Decimal conversions accept the documented lexical profile.",
            ),
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
            ("min_length", translate_min_length),
            ("max_length", translate_max_length),
            ("json_contains", translate_json_contains),
            ("json_has_key", translate_json_has_key),
            ("fulltext_match", translate_fulltext_match),
        ):
            registry.register_constraint(operator, translator, on_conflict="replace")


__all__ = [
    "MysqlPlugin",
    "__version__",
    "translate_fulltext_match",
    "translate_max_length",
    "translate_min_length",
    "translate_json_contains",
    "translate_json_has_key",
    "translate_pattern",
]
