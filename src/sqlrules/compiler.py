from __future__ import annotations

from collections.abc import Mapping, Sequence
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
    OnConflict,
    OnUnsupported,
)
from sqlrules.plugins import SQLRulesPlugin, validate_plugin
from sqlrules.translators import TranslatorRegistry, default_registry

RulesDict = dict[str, list[ColumnElement[bool]]]


class Compiler:
    """Compile constrained Pydantic models into SQLAlchemy rule dictionaries.

    ``dialect`` is an optional hint stored on ``CompilationContext`` for
    custom translators. It does **not** load dialect plugins or change
    built-in translations — pass ``plugins=[...]`` explicitly.
    """

    def __init__(
        self,
        *,
        registry: TranslatorRegistry | None = None,
        plugins: Sequence[SQLRulesPlugin] | None = None,
        on_conflict: OnConflict = "raise",
        on_unsupported: OnUnsupported = "raise",
        dialect: str | None = None,
        cache: bool = True,
        model_cache: ModelIRCache | None = None,
    ) -> None:
        if on_unsupported not in {"raise", "warn", "ignore"}:
            raise ConfigurationError(option="on_unsupported", value=on_unsupported)
        if on_conflict not in {"raise", "replace", "ignore"}:
            raise ConfigurationError(option="on_conflict", value=on_conflict)

        # Always copy so caller-owned and shared default registries are never mutated.
        base = (registry if registry is not None else default_registry()).copy()
        plugin_list = list(plugins or ())
        resolved: TranslatorRegistry
        if plugin_list:
            aware = _PluginAwareRegistry(
                base,
                default_on_conflict=on_conflict,
            )
            for plugin in plugin_list:
                validate_plugin(plugin).register(aware)
            # Freeze to a plain registry after registration.
            resolved = aware.copy()
        else:
            resolved = base
        self.registry = resolved

        self.on_unsupported = on_unsupported
        self.on_conflict = on_conflict
        self.dialect = dialect
        self.cache_enabled = cache
        self._model_cache = model_cache if model_cache is not None else default_cache()
        self._collector = DiagnosticsCollector()
        self.context = CompilationContext(
            on_unsupported=on_unsupported,
            collector=self._collector,
            dialect=dialect,
        )

    @property
    def diagnostics(self) -> tuple[Diagnostic, ...]:
        """Diagnostics from the most recent ``compile`` / ``bind`` call."""
        return self._collector.snapshot()

    def compile_model(self, model: type[BaseModel]) -> ModelIR:
        """Phase 1: inspect the model and extract constraint IR (no table binding)."""
        self._collector.clear()
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
            dialect=self.dialect,
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


class _PluginAwareRegistry(TranslatorRegistry):
    """Registry that applies Compiler.on_conflict as the default for register()."""

    def __init__(
        self,
        base: TranslatorRegistry,
        *,
        default_on_conflict: OnConflict,
    ) -> None:
        super().__init__()
        for operator_name in base.operators():
            translator = base.lookup(operator_name)
            if translator is not None:
                # Already validated on the source registry.
                self._translators[operator_name] = translator
        self._default_on_conflict = default_on_conflict

    def register(
        self,
        operator_name: str,
        translator: Any,
        *,
        replace: bool = False,
    ) -> None:
        on_conflict: OnConflict = "replace" if replace else self._default_on_conflict
        self.register_constraint(operator_name, translator, on_conflict=on_conflict)

    def register_constraint(
        self,
        operator_name: str,
        translator: Any,
        *,
        on_conflict: OnConflict | None = None,
    ) -> None:
        super().register_constraint(
            operator_name,
            translator,
            on_conflict=on_conflict if on_conflict is not None else self._default_on_conflict,
        )


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
