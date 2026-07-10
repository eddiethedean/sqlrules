from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class SQLRulesError(Exception):
    """Base class for all public SQLRules exceptions."""


@dataclass(slots=True)
class InvalidModelError(SQLRulesError):
    model: Any

    def __str__(self) -> str:
        return f"Expected a Pydantic BaseModel subclass, got {self.model!r}."


@dataclass(slots=True)
class MissingColumnError(SQLRulesError):
    field: str

    def __str__(self) -> str:
        return f"No SQLAlchemy column found for field {self.field!r}."


@dataclass(slots=True)
class UnsupportedConstraintError(SQLRulesError):
    field: str
    operator: str
    value: Any = None

    def __str__(self) -> str:
        return (
            f"Field {self.field!r}: constraint {self.operator!r} is not supported "
            "by the active SQLRules compiler."
        )


@dataclass(slots=True)
class TranslatorError(SQLRulesError):
    field: str
    operator: str
    message: str

    def __str__(self) -> str:
        return (
            f"Translator failed for field {self.field!r}, "
            f"operator {self.operator!r}: {self.message}"
        )


@dataclass(slots=True)
class InvalidTranslatorError(SQLRulesError):
    operator: str
    translator: Any

    def __str__(self) -> str:
        return f"Invalid translator for operator {self.operator!r}: {self.translator!r}."


@dataclass(slots=True)
class RegistryError(SQLRulesError):
    message: str

    def __str__(self) -> str:
        return self.message


@dataclass(slots=True)
class ConfigurationError(SQLRulesError):
    option: str
    value: Any

    def __str__(self) -> str:
        return f"Invalid configuration value for {self.option!r}: {self.value!r}."


class InternalCompilerError(SQLRulesError):
    """Unexpected internal compiler failure."""
