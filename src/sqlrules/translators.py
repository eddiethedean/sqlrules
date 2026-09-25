from __future__ import annotations

import inspect
import math
import operator
import threading
from collections.abc import Callable
from decimal import Decimal, InvalidOperation
from typing import Any, NoReturn, cast

from sqlalchemy import func
from sqlalchemy.sql.elements import ColumnElement

from sqlrules.errors import (
    InvalidTranslatorError,
    RegistryError,
    TranslatorError,
    UnsupportedConstraintError,
)
from sqlrules.ir import CompilationContext, Constraint, OnConflict

Translator = Callable[[Constraint, ColumnElement[Any], CompilationContext], ColumnElement[bool]]


def _binary(op: Callable[[Any, Any], Any]) -> Translator:
    def translate(
        constraint: Constraint,
        column: ColumnElement[Any],
        context: CompilationContext,
    ) -> ColumnElement[bool]:
        return cast(ColumnElement[bool], op(column, constraint.value))

    return translate


def _is_positive_finite(value: Any) -> bool:
    """Return True when ``value`` is a finite number strictly greater than zero."""
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        return False
    if isinstance(value, Decimal):
        try:
            return value.is_finite() and value > 0
        except InvalidOperation:
            return False
    if isinstance(value, float):
        return math.isfinite(value) and value > 0
    return bool(value > 0)


def _multiple_of(
    constraint: Constraint,
    column: ColumnElement[Any],
    context: CompilationContext,
) -> ColumnElement[bool]:
    value = constraint.value
    if not _is_positive_finite(value):
        raise UnsupportedConstraintError(
            field=constraint.field,
            operator="multiple_of",
            value=value,
            suggestion="multiple_of requires a finite positive numeric value.",
        )
    return cast(ColumnElement[bool], (column % value) == 0)


def _min_length(
    constraint: Constraint,
    column: ColumnElement[Any],
    context: CompilationContext,
) -> ColumnElement[bool]:
    return cast(ColumnElement[bool], func.length(column) >= constraint.value)


def _max_length(
    constraint: Constraint,
    column: ColumnElement[Any],
    context: CompilationContext,
) -> ColumnElement[bool]:
    return cast(ColumnElement[bool], func.length(column) <= constraint.value)


def _in_values(
    constraint: Constraint,
    column: ColumnElement[Any],
    context: CompilationContext,
) -> ColumnElement[bool]:
    return cast(ColumnElement[bool], column.in_(constraint.value))


def _validate_translator(operator_name: str, translator: Any) -> Translator:
    if not callable(translator):
        raise InvalidTranslatorError(operator=operator_name, translator=translator)
    try:
        signature = inspect.signature(translator)
    except (TypeError, ValueError):
        return cast(Translator, translator)

    params = list(signature.parameters.values())
    if any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in params):
        return cast(Translator, translator)

    positional = [
        p
        for p in params
        if p.kind
        in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        )
    ]
    if len(positional) < 3:
        raise InvalidTranslatorError(operator=operator_name, translator=translator)
    return cast(Translator, translator)


class TranslatorRegistry:
    def __init__(self) -> None:
        self._translators: dict[str, Translator] = {}

    def register(
        self,
        operator_name: str,
        translator: Translator,
        *,
        replace: bool = False,
    ) -> None:
        self.register_constraint(
            operator_name,
            translator,
            on_conflict="replace" if replace else "raise",
        )

    def register_constraint(
        self,
        operator_name: str,
        translator: Translator,
        *,
        on_conflict: OnConflict = "raise",
    ) -> None:
        if on_conflict not in {"raise", "replace", "ignore"}:
            raise RegistryError(
                f"Invalid on_conflict value {on_conflict!r}. "
                "Use one of: 'raise', 'replace', 'ignore'."
            )
        validated = _validate_translator(operator_name, translator)
        if operator_name in self._translators:
            if on_conflict == "raise":
                raise RegistryError(f"Translator for {operator_name!r} is already registered.")
            if on_conflict == "ignore":
                return
        self._translators[operator_name] = validated

    def lookup(self, operator_name: str) -> Translator | None:
        return self._translators.get(operator_name)

    def operators(self) -> frozenset[str]:
        return frozenset(self._translators)

    def __contains__(self, operator_name: object) -> bool:
        return isinstance(operator_name, str) and operator_name in self._translators

    def copy(self) -> TranslatorRegistry:
        clone = TranslatorRegistry()
        clone._translators = dict(self._translators)
        return clone

    def handle_missing_translator(
        self,
        constraint: Constraint,
    ) -> NoReturn:
        """Fail when a retained constraint has no translator."""
        raise UnsupportedConstraintError(
            field=constraint.field,
            operator=constraint.operator,
            value=constraint.value,
            suggestion=(
                "Remove it or use from_pydantic() to convert and report unsupported declarations."
            ),
        )

    def translate(
        self,
        constraint: Constraint,
        column: ColumnElement[Any],
        context: CompilationContext,
    ) -> ColumnElement[bool]:
        translator = self.lookup(constraint.operator)
        if translator is None:
            self.handle_missing_translator(constraint)

        try:
            result = translator(constraint, column, context)
        except UnsupportedConstraintError:
            raise
        except Exception as exc:  # pragma: no cover - defensive wrapper
            raise TranslatorError(
                field=constraint.field,
                operator=constraint.operator,
                message=str(exc),
            ) from exc
        if not isinstance(result, ColumnElement):
            raise TranslatorError(
                field=constraint.field,
                operator=constraint.operator,
                message=(
                    f"translator returned {type(result).__name__!r}, "
                    "expected a SQLAlchemy ColumnElement"
                ),
            )
        return result


def default_registry() -> TranslatorRegistry:
    """Return a **copy** of the built-in portable translator registry.

    The builtin template is built once per process. Callers may mutate the
    returned registry without affecting other callers or ``Compiler``.
    """
    return _builtin_registry().copy()


def _builtin_registry() -> TranslatorRegistry:
    global _BUILTIN_REGISTRY
    if _BUILTIN_REGISTRY is None:
        with _BUILTIN_REGISTRY_LOCK:
            if _BUILTIN_REGISTRY is None:
                _BUILTIN_REGISTRY = _build_builtin_registry()
    return _BUILTIN_REGISTRY


def _build_builtin_registry() -> TranslatorRegistry:
    registry = TranslatorRegistry()
    registry.register("gt", _binary(operator.gt))
    registry.register("ge", _binary(operator.ge))
    registry.register("lt", _binary(operator.lt))
    registry.register("le", _binary(operator.le))
    registry.register("multiple_of", _multiple_of)
    registry.register("min_length", _min_length)
    registry.register("max_length", _max_length)
    registry.register("literal", _in_values)
    registry.register("enum", _in_values)
    # pattern is extracted into IR but has no portable core translator.
    return registry


_BUILTIN_REGISTRY: TranslatorRegistry | None = None
_BUILTIN_REGISTRY_LOCK = threading.Lock()
