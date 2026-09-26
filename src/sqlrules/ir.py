from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from sqlalchemy.sql.elements import ColumnElement

OnUnsupported = Literal["raise"]
OnConflict = Literal["raise", "replace", "ignore"]
DiagnosticSeverity = Literal["warning", "info"]


@dataclass(frozen=True, slots=True)
class PatternSpec:
    """Normalized ``pattern`` constraint value (preserves case-folding intent)."""

    pattern: str
    ignore_case: bool = False


@dataclass(frozen=True, slots=True)
class Constraint:
    field: str
    operator: str
    value: Any


@dataclass(frozen=True, slots=True)
class FieldDescriptor:
    name: str
    alias: str | None
    annotation: Any
    metadata: tuple[Any, ...] = ()
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RuleField:
    """SQLRules-owned normalized field declaration."""

    name: str
    annotation: Any
    python_type: Any
    nullable: bool
    strict: bool
    constraints: tuple[Constraint, ...]
    column: str | None = None
    alias: str | None = None
    title: str | None = None
    description: str | None = None
    examples: tuple[Any, ...] = ()
    source: str = "native"
    source_location: str = ""


@dataclass(frozen=True, slots=True)
class SchemaSpec:
    """Immutable, table-independent normalized RuleSchema representation."""

    model: type[Any]
    fields: tuple[RuleField, ...]
    allow_empty: bool = False
    provenance: str = "native"


@dataclass(frozen=True, slots=True)
class PreparedValue:
    """Backend-prepared source value and total type/coercion evidence."""

    source: ColumnElement[Any]
    value: ColumnElement[Any]
    valid: ColumnElement[bool]
    is_null: ColumnElement[bool]
    logical_type: str
    coercion: str = "identity"
    capability: str = "native"


@dataclass(frozen=True, slots=True)
class FieldResult:
    """Bound result for one normalized field."""

    name: str
    predicate: ColumnElement[bool]
    column: ColumnElement[Any]
    logical_type: str
    strict: bool
    nullable: bool
    coercion: str
    capability: str


@dataclass(frozen=True, slots=True)
class CompiledRules:
    """Complete, total predicate returned by the 2.0 application API."""

    predicate: ColumnElement[bool]
    fields: tuple[FieldResult, ...]
    diagnostics: tuple[Diagnostic, ...] = ()
    backend: str = ""
    server_version: tuple[int, ...] | None = None
    assumptions: tuple[str, ...] = ()
    provenance: str = "native"

    def explain(self) -> dict[str, Any]:
        """Return a structured compile plan without executing database EXPLAIN."""
        return {
            "backend": self.backend,
            "server_version": self.server_version,
            "assumptions": self.assumptions,
            "provenance": self.provenance,
            "fields": [
                {
                    "name": item.name,
                    "logical_type": item.logical_type,
                    "strict": item.strict,
                    "nullable": item.nullable,
                    "coercion": item.coercion,
                    "capability": item.capability,
                    "predicate": str(item.predicate),
                }
                for item in self.fields
            ],
            "diagnostics": [
                {
                    "severity": item.severity,
                    "field": item.field,
                    "operator": item.operator,
                    "code": item.code,
                    "message": item.message,
                }
                for item in self.diagnostics
            ],
        }


@dataclass(frozen=True, slots=True)
class Diagnostic:
    severity: DiagnosticSeverity
    field: str
    operator: str
    value: Any = None
    message: str = ""
    code: str = ""


@dataclass(slots=True)
class DiagnosticsCollector:
    """Mutable collector; snapshots are immutable tuples."""

    _items: list[Diagnostic] = field(default_factory=list)

    def add(self, diagnostic: Diagnostic) -> None:
        self._items.append(diagnostic)

    def clear(self) -> None:
        self._items.clear()

    def snapshot(self) -> tuple[Diagnostic, ...]:
        return tuple(self._items)


@dataclass(frozen=True, slots=True)
class CompilationContext:
    on_unsupported: OnUnsupported = "raise"
    collector: DiagnosticsCollector | None = None
    dialect: str | None = None
    server_version: tuple[int, ...] | None = None
    assumptions: tuple[str, ...] = ()

    def record(
        self,
        *,
        severity: DiagnosticSeverity,
        field: str,
        operator: str,
        value: Any = None,
        message: str = "",
        code: str = "",
    ) -> None:
        if self.collector is None:
            return
        self.collector.add(
            Diagnostic(
                severity=severity,
                field=field,
                operator=operator,
                value=value,
                message=message,
                code=code,
            )
        )
