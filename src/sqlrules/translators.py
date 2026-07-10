from __future__ import annotations

import inspect
import operator
import sys
import types
import warnings
from collections.abc import Callable
from typing import Any, cast

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


class SQLRulesWarning(UserWarning):
    """Warning emitted when an unsupported constraint is skipped."""


def _warning_stacklevel() -> int:
    """Stacklevel that attributes warnings to the first frame outside sqlrules."""
    frame: types.FrameType | None = sys._getframe(1)
    level = 1
    while frame is not None:
        module = frame.f_globals.get("__name__", "")
        if not (isinstance(module, str) and module.startswith("sqlrules")):
            return level
        frame = frame.f_back
        level += 1
    return 2


def _binary(op: Callable[[Any, Any], Any]) -> Translator:
    def translate(
        constraint: Constraint,
        column: ColumnElement[Any],
        context: CompilationContext,
    ) -> ColumnElement[bool]:
        return cast(ColumnElement[bool], op(column, constraint.value))

    return translate


def _multiple_of(
    constraint: Constraint,
    column: ColumnElement[Any],
    context: CompilationContext,
) -> ColumnElement[bool]:
    value = constraint.value
    try:
        non_positive = value <= 0
    except TypeError as exc:
        raise UnsupportedConstraintError(
            field=constraint.field,
            operator="multiple_of",
            value=value,
            suggestion="multiple_of requires a positive numeric value.",
        ) from exc
    if non_positive:
        raise UnsupportedConstraintError(
            field=constraint.field,
            operator="multiple_of",
            value=value,
            suggestion="multiple_of requires a positive numeric value.",
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

    def translate(
        self,
        constraint: Constraint,
        column: ColumnElement[Any],
        context: CompilationContext,
    ) -> ColumnElement[bool] | None:
        translator = self.lookup(constraint.operator)
        if translator is None:
            message = (
                f"Field {constraint.field!r}: constraint {constraint.operator!r} "
                "is not supported and will be skipped."
            )
            if context.on_unsupported == "raise":
                raise UnsupportedConstraintError(
                    field=constraint.field,
                    operator=constraint.operator,
                    value=constraint.value,
                    suggestion=("Remove the constraint, or set on_unsupported='warn'/'ignore'."),
                )
            if context.on_unsupported == "warn":
                context.record(
                    severity="warning",
                    field=constraint.field,
                    operator=constraint.operator,
                    value=constraint.value,
                    message=message,
                    code="unsupported_constraint",
                )
                warnings.warn(message, SQLRulesWarning, stacklevel=_warning_stacklevel())
            else:
                context.record(
                    severity="info",
                    field=constraint.field,
                    operator=constraint.operator,
                    value=constraint.value,
                    message=message,
                    code="unsupported_constraint",
                )
            return None

        try:
            return translator(constraint, column, context)
        except UnsupportedConstraintError:
            raise
        except Exception as exc:  # pragma: no cover - defensive wrapper
            raise TranslatorError(
                field=constraint.field,
                operator=constraint.operator,
                message=str(exc),
            ) from exc


def default_registry() -> TranslatorRegistry:
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
