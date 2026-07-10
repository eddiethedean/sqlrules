from __future__ import annotations

import operator
import warnings
from collections.abc import Callable
from typing import Any, cast

from sqlalchemy import func
from sqlalchemy.sql.elements import ColumnElement

from sqlrules.errors import RegistryError, TranslatorError, UnsupportedConstraintError
from sqlrules.ir import CompilationContext, Constraint

Translator = Callable[[Constraint, ColumnElement[Any], CompilationContext], ColumnElement[bool]]


class SQLRulesWarning(UserWarning):
    """Warning emitted when an unsupported constraint is skipped."""


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
        if not replace and operator_name in self._translators:
            raise RegistryError(f"Translator for {operator_name!r} is already registered.")
        self._translators[operator_name] = translator

    def lookup(self, operator_name: str) -> Translator | None:
        return self._translators.get(operator_name)

    def translate(
        self,
        constraint: Constraint,
        column: ColumnElement[Any],
        context: CompilationContext,
    ) -> ColumnElement[bool] | None:
        translator = self.lookup(constraint.operator)
        if translator is None:
            if context.on_unsupported == "raise":
                raise UnsupportedConstraintError(
                    field=constraint.field,
                    operator=constraint.operator,
                    value=constraint.value,
                    suggestion=("Remove the constraint, or set on_unsupported='warn'/'ignore'."),
                )
            if context.on_unsupported == "warn":
                # sqlrules.compile → Compiler.compile → translate → warn
                # stacklevel=4 attributes the warning to the caller's code.
                warnings.warn(
                    (
                        f"Field {constraint.field!r}: constraint {constraint.operator!r} "
                        "is not supported and will be skipped."
                    ),
                    SQLRulesWarning,
                    stacklevel=4,
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
    return registry
