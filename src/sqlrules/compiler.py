from __future__ import annotations

from collections.abc import Mapping
from itertools import chain
from typing import Any

from pydantic import BaseModel
from sqlalchemy.sql.elements import ColumnElement

from sqlrules.columns import resolve_column
from sqlrules.constraints import extract_constraints
from sqlrules.errors import ConfigurationError
from sqlrules.inspectors import inspect_model
from sqlrules.ir import CompilationContext, OnUnsupported
from sqlrules.translators import TranslatorRegistry, default_registry

RulesDict = dict[str, list[ColumnElement[bool]]]


class Compiler:
    def __init__(
        self,
        *,
        registry: TranslatorRegistry | None = None,
        on_unsupported: OnUnsupported = "raise",
    ) -> None:
        if on_unsupported not in {"raise", "warn", "ignore"}:
            raise ConfigurationError(option="on_unsupported", value=on_unsupported)
        self.registry = registry or default_registry()
        self.context = CompilationContext(on_unsupported=on_unsupported)

    def compile(
        self,
        model: type[BaseModel],
        table: Any,
        *,
        column_map: Mapping[str, ColumnElement[Any]] | None = None,
    ) -> RulesDict:
        rules: RulesDict = {}

        for field in inspect_model(model):
            column = resolve_column(field.name, table, column_map)
            constraints = extract_constraints(field)

            expressions: list[ColumnElement[bool]] = []
            for constraint in constraints:
                expression = self.registry.translate(constraint, column, self.context)
                if expression is not None:
                    expressions.append(expression)

            if expressions:
                rules[field.name] = expressions

        return rules


def compile(
    model: type[BaseModel],
    table: Any,
    *,
    column_map: Mapping[str, ColumnElement[Any]] | None = None,
    on_unsupported: OnUnsupported = "raise",
) -> RulesDict:
    return Compiler(on_unsupported=on_unsupported).compile(model, table, column_map=column_map)


def flatten(rules: RulesDict) -> list[ColumnElement[bool]]:
    return list(chain.from_iterable(rules.values()))


def where(rules: RulesDict) -> list[ColumnElement[bool]]:
    return flatten(rules)
