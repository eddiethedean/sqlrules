from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

OnUnsupported = Literal["raise", "warn", "ignore"]
OnConflict = Literal["raise", "replace", "ignore"]
DiagnosticSeverity = Literal["warning", "info"]


@dataclass(frozen=True, slots=True)
class PatternSpec:
    """Normalized ``pattern`` constraint value (preserves case-folding intent)."""

    pattern: str
    ignore_case: bool = False


@dataclass(frozen=True, slots=True)
class TypeSpec:
    """Normalized ``type_check`` constraint value (Pydantic type + strictness)."""

    python_type: type
    strict: bool = False
    allow_none: bool = False


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


@dataclass(frozen=True, slots=True)
class FieldIR:
    descriptor: FieldDescriptor
    constraints: tuple[Constraint, ...]


@dataclass(frozen=True, slots=True)
class ModelIR:
    model: type[Any]
    fields: tuple[FieldIR, ...]
