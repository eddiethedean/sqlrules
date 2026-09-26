from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from sqlalchemy import String, case, func, literal
from sqlalchemy.sql.elements import ColumnElement

from sqlrules.backend import prepare_scalar, total_predicate
from sqlrules.errors import CapabilityError
from sqlrules.ir import CompilationContext, PreparedValue, RuleField
from sqlrules.plugins import PLUGIN_API_VERSION
from sqlrules.translators import TranslatorRegistry
from sqlrules_mssql.json import translate_json_contains, translate_json_has_key
from sqlrules_mssql.length import translate_max_length, translate_min_length

__version__ = "2.0.0"


class MssqlPlugin:
    """Register SQL Server constraint translators.

    Does not register ``pattern`` — SQL Server has no portable regex operator
    that SQLRules can emit deterministically. Provide a custom translator if
    needed. Scalar types are prepared by the backend provider.
    """

    name = "mssql"
    api_version = PLUGIN_API_VERSION

    def __init__(
        self,
        *,
        server_version: tuple[int, ...] | None = None,
        compatibility_level: int | None = None,
    ) -> None:
        self.server_version = tuple(server_version) if server_version is not None else None
        self.compatibility_level = compatibility_level

    def capabilities(self) -> Mapping[str, Any]:
        return {
            "backend": self.name,
            "server_version": self.server_version,
            "compatibility_level": self.compatibility_level,
            "json_markers_supported": self.server_version is not None
            and self.server_version >= (13, 0)
            and self.compatibility_level is not None
            and self.compatibility_level >= 130,
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
            and self.server_version >= (11, 0),
            "safe_text_numeric_targets": (
                ("int", "float")
                if self.server_version is not None and self.server_version >= (11, 0)
                else ()
            ),
            "assumptions": (
                "TRY_CAST provides safe numeric conversion on SQL Server 2012 and newer.",
                "Text-to-numeric conversion is accepted only when TRY_CAST succeeds.",
            ),
        }

    def prepare_value(
        self,
        column: Any,
        field: RuleField,
        context: CompilationContext,
    ) -> PreparedValue:
        if field.python_type is dict and any(
            item.operator in {"json_contains", "json_has_key"} for item in field.constraints
        ):
            if self.server_version is None or self.server_version < (13, 0):
                raise CapabilityError(
                    self.name,
                    field.name,
                    "json",
                    type(column.type).__name__,
                    "SQL Server JSON markers require SQL Server 2016 or newer; "
                    "pass server_version explicitly.",
                )
            if self.compatibility_level is None or self.compatibility_level < 130:
                raise CapabilityError(
                    self.name,
                    field.name,
                    "json",
                    type(column.type).__name__,
                    "OPENJSON requires database compatibility level 130 or higher; "
                    "pass compatibility_level explicitly.",
                )
            source_name = type(column.type).__name__.lower()
            if not isinstance(column.type, String) and "json" not in source_name:
                raise CapabilityError(
                    self.name,
                    field.name,
                    "json",
                    source_name,
                    "SQL Server JSON markers require a text or JSON column.",
                )
            valid = total_predicate(func.isjson(column) == 1)
            safe_json = case((valid, column), else_=literal("{}"))
            return PreparedValue(
                source=column,
                value=cast(ColumnElement[Any], safe_json),
                valid=valid,
                is_null=cast(ColumnElement[bool], column.is_(None)),
                logical_type="json",
                coercion="validated-json-text",
                capability="isjson-guarded",
            )
        return prepare_scalar(column, field, context, backend=self.name)

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
