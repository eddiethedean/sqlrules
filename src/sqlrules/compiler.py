from __future__ import annotations

from collections.abc import Mapping
from itertools import chain
from typing import Any

from pydantic import BaseModel
from sqlalchemy.sql.elements import ColumnElement

from sqlrules.cache import ModelIRCache, default_cache
from sqlrules.columns import resolve_column
from sqlrules.constraints import ensure_supported_type, extract_constraints
from sqlrules.errors import ConfigurationError
from sqlrules.inspectors import inspect_model
from sqlrules.ir import (
    CompilationContext,
    Diagnostic,
    DiagnosticsCollector,
    FieldIR,
    ModelIR,
    OnUnsupported,
)
from sqlrules.translators import TranslatorRegistry, default_registry

RulesDict = dict[str, list[ColumnElement[bool]]]


class Compiler:
    def __init__(
        self,
        *,
        registry: TranslatorRegistry | None = None,
        on_unsupported: OnUnsupported = "raise",
        cache: bool = True,
        model_cache: ModelIRCache | None = None,
    ) -> None:
        if on_unsupported not in {"raise", "warn", "ignore"}:
            raise ConfigurationError(option="on_unsupported", value=on_unsupported)
        self.registry = registry or default_registry()
        self.on_unsupported = on_unsupported
        self.cache_enabled = cache
        self._model_cache = model_cache if model_cache is not None else default_cache()
        self._collector = DiagnosticsCollector()
        self.context = CompilationContext(
            on_unsupported=on_unsupported,
            collector=self._collector,
        )

    @property
    def diagnostics(self) -> tuple[Diagnostic, ...]:
        """Diagnostics from the most recent ``compile`` / ``bind`` call."""
        return self._collector.snapshot()

    def compile_model(self, model: type[BaseModel]) -> ModelIR:
        """Phase 1: inspect the model and extract constraint IR (no table binding)."""
        if self.cache_enabled:
            cached = self._model_cache.get(model)
            if cached is not None:
                return cached

        fields: list[FieldIR] = []
        for descriptor in inspect_model(model):
            ensure_supported_type(descriptor)
            constraints = tuple(extract_constraints(descriptor))
            fields.append(FieldIR(descriptor=descriptor, constraints=constraints))

        model_ir = ModelIR(model=model, fields=tuple(fields))
        if self.cache_enabled:
            return self._model_cache.put(model, model_ir)
        return model_ir

    def bind(
        self,
        model_ir: ModelIR,
        table: Any,
        *,
        column_map: Mapping[str, ColumnElement[Any]] | None = None,
    ) -> RulesDict:
        """Phase 2: resolve columns and translate IR into SQLAlchemy expressions."""
        self._collector.clear()
        # Refresh context in case on_unsupported was mutated (should not be).
        self.context = CompilationContext(
            on_unsupported=self.on_unsupported,
            collector=self._collector,
        )

        rules: RulesDict = {}
        for field_ir in model_ir.fields:
            if not field_ir.constraints:
                continue

            descriptor = field_ir.descriptor
            column = resolve_column(
                descriptor.name,
                table,
                column_map,
                alias=descriptor.alias,
                aliases=descriptor.aliases,
            )

            expressions: list[ColumnElement[bool]] = []
            for constraint in field_ir.constraints:
                expression = self.registry.translate(constraint, column, self.context)
                if expression is not None:
                    expressions.append(expression)

            if expressions:
                rules[descriptor.name] = expressions

        return rules

    def compile(
        self,
        model: type[BaseModel],
        table: Any,
        *,
        column_map: Mapping[str, ColumnElement[Any]] | None = None,
    ) -> RulesDict:
        return self.bind(self.compile_model(model), table, column_map=column_map)


def compile(
    model: type[BaseModel],
    table: Any,
    *,
    column_map: Mapping[str, ColumnElement[Any]] | None = None,
    on_unsupported: OnUnsupported = "raise",
    cache: bool = True,
) -> RulesDict:
    return Compiler(on_unsupported=on_unsupported, cache=cache).compile(
        model, table, column_map=column_map
    )


def flatten(rules: RulesDict) -> list[ColumnElement[bool]]:
    return list(chain.from_iterable(rules.values()))


def where(rules: RulesDict) -> list[ColumnElement[bool]]:
    return flatten(rules)
