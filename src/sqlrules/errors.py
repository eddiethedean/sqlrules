from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class SQLRulesError(Exception):
    """Base class for all public SQLRules exceptions."""


@dataclass(slots=True)
class InvalidModelError(SQLRulesError):
    model: Any

    def __str__(self) -> str:
        return (
            f"Expected a Pydantic BaseModel subclass, got {self.model!r}. "
            "Pass a model class such as class UserFilter(BaseModel): ..."
        )


@dataclass(slots=True)
class MissingColumnError(SQLRulesError):
    field: str

    def __str__(self) -> str:
        return (
            f"No SQLAlchemy column found for field {self.field!r}. "
            "Provide a matching table column, ORM attribute, or column_map entry."
        )


@dataclass(slots=True)
class UnsupportedConstraintError(SQLRulesError):
    field: str
    operator: str
    value: Any = None
    suggestion: str | None = None

    def __str__(self) -> str:
        message = (
            f"Field {self.field!r}: constraint {self.operator!r} is not supported by SQLRules."
        )
        if self.suggestion:
            return f"{message} {self.suggestion}"
        return f"{message} Remove the constraint, or set on_unsupported='warn'/'ignore'."


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
        return (
            f"Invalid translator for operator {self.operator!r}: {self.translator!r}. "
            "Translators must be callables returning a SQLAlchemy boolean expression."
        )


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
        if self.option == "on_unsupported":
            return (
                f"Invalid configuration value for {self.option!r}: {self.value!r}. "
                "Use one of: 'raise', 'warn', 'ignore'."
            )
        if self.option == "on_conflict":
            return (
                f"Invalid configuration value for {self.option!r}: {self.value!r}. "
                "Use one of: 'raise', 'replace', 'ignore'."
            )
        return f"Invalid configuration value for {self.option!r}: {self.value!r}."


@dataclass(slots=True)
class PluginError(SQLRulesError):
    """Raised when a plugin fails validation or registration."""

    message: str
    plugin: Any = None

    def __str__(self) -> str:
        return self.message


class InternalCompilerError(SQLRulesError):
    """Unexpected internal compiler failure."""
