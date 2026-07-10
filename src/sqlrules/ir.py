from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

OnUnsupported = Literal["raise", "warn", "ignore"]


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
class CompilationContext:
    on_unsupported: OnUnsupported = "raise"
    diagnostics: tuple[str, ...] = field(default_factory=tuple)
