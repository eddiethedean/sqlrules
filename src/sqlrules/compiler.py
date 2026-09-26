from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import and_, true
from sqlalchemy.sql.elements import ColumnElement

from sqlrules.backend import total_predicate
from sqlrules.columns import resolve_column
from sqlrules.errors import CapabilityError, ConfigurationError, MissingColumnError, PluginError
from sqlrules.ir import (
    CompilationContext,
    CompiledRules,
    DiagnosticsCollector,
    FieldResult,
    OnConflict,
    RuleField,
    SchemaSpec,
)
from sqlrules.models import RuleSchema, normalize_schema
from sqlrules.plugins import BackendProvider, SQLRulesPlugin, validate_backend, validate_plugin
from sqlrules.translators import TranslatorRegistry, default_registry


class Compiler:
    """Compile SQLRules-owned Pydantic schemas through one explicit backend."""

    def __init__(
        self,
        *,
        plugins: Sequence[SQLRulesPlugin] | None = None,
        registry: TranslatorRegistry | None = None,
        on_conflict: OnConflict = "raise",
        on_unsupported: str = "raise",
        dialect: str | None = None,
        cache: bool = True,
    ) -> None:
        if on_conflict not in {"raise", "replace", "ignore"}:
            raise ConfigurationError("on_conflict", on_conflict)
        if on_unsupported != "raise":
            raise ConfigurationError("on_unsupported", on_unsupported)
        base = registry.copy() if registry is not None else default_registry()
        plugin_list = list(plugins or ())
        for plugin in plugin_list:
            validate_plugin(plugin)
        if sum(_is_backend(plugin) for plugin in plugin_list) > 1:
            raise PluginError(message="Pass exactly one backend provider to Compiler(plugins=...).")
        aware = _PluginAwareRegistry(base, default_on_conflict=on_conflict)
        for plugin in plugin_list:
            plugin.register(aware)
        self._registry = aware.copy()
        self.plugins = tuple(plugin_list)
        self.dialect = dialect
        # The option remains for the 1.x constructor surface. Schema metadata is
        # normalized per call and table-bound state is never cached.
        self.cache_enabled = cache

    @property
    def registry(self) -> TranslatorRegistry:
        """Return a copy of this compiler's immutable translator snapshot."""
        return self._registry.copy()

    @property
    def backend(self) -> BackendProvider:
        providers = [plugin for plugin in self.plugins if _is_backend(plugin)]
        if len(providers) != 1:
            raise PluginError(
                message=(
                    "SQLRules 2.0 requires exactly one explicit backend provider in plugins=. "
                    f"Found {len(providers)}. Pass one dialect plugin such as PostgresPlugin()."
                )
            )
        return validate_backend(providers[0])

    def capabilities(self) -> Mapping[str, Any]:
        """Return the configured backend's declared capability profile."""
        return dict(self.backend.capabilities())

    def compile_model(self, model: type[RuleSchema]) -> SchemaSpec:
        """Normalize a RuleSchema class without binding database columns."""
        if not isinstance(model, type) or not issubclass(model, RuleSchema):
            from sqlrules.errors import InvalidModelError

            raise InvalidModelError(model=model)
        # Re-normalize on each call. RuleSchema classes are not globally cached,
        # so mutable extension payloads cannot leave stale IR behind.
        return normalize_schema(model)

    def bind(
        self,
        schema: SchemaSpec,
        table: Any,
        *,
        column_map: Mapping[str, ColumnElement[Any]] | None = None,
    ) -> CompiledRules:
        """Bind normalized fields and produce one total root predicate."""
        provider = self.backend
        capability_info = dict(provider.capabilities())
        server_version = getattr(provider, "server_version", None)
        if self.dialect is not None and self.dialect != provider.name:
            raise ConfigurationError("dialect", self.dialect)
        assumptions = tuple(capability_info.get("assumptions", ()))
        collector = DiagnosticsCollector()
        context = CompilationContext(
            on_unsupported="raise",
            collector=collector,
            dialect=provider.name,
            server_version=server_version,
            assumptions=assumptions,
        )

        field_results: list[FieldResult] = []
        root_expressions: list[ColumnElement[bool]] = []
        for field in schema.fields:
            column = _resolve_rule_column(field, table, column_map)
            prepared = provider.prepare_value(column, field, context)
            constraint_expressions: list[ColumnElement[bool]] = []
            for constraint in field.constraints:
                if self._registry.lookup(constraint.operator) is None:
                    raise CapabilityError(
                        provider.name,
                        field.name,
                        prepared.logical_type,
                        type(column.type).__name__,
                        f"no translator is registered for retained operator "
                        f"{constraint.operator!r}.",
                    )
                expression = self._registry.translate(constraint, prepared.value, context)
                constraint_expressions.append(expression)

            matched_value = and_(prepared.valid, *constraint_expressions)
            if field.nullable:
                field_predicate = prepared.is_null | matched_value
            else:
                field_predicate = column.is_not(None) & matched_value
            field_predicate = total_predicate(field_predicate)
            root_expressions.append(field_predicate)
            field_results.append(
                FieldResult(
                    name=field.name,
                    predicate=field_predicate,
                    column=column,
                    logical_type=prepared.logical_type,
                    strict=field.strict,
                    nullable=field.nullable,
                    coercion=prepared.coercion,
                    capability=prepared.capability,
                )
            )

        predicate = total_predicate(and_(*root_expressions) if root_expressions else true())
        return CompiledRules(
            predicate=predicate,
            fields=tuple(field_results),
            diagnostics=collector.snapshot(),
            backend=provider.name,
            server_version=server_version,
            assumptions=assumptions,
            provenance=schema.provenance,
        )

    def compile(
        self,
        model: type[RuleSchema],
        table: Any,
        *,
        column_map: Mapping[str, ColumnElement[Any]] | None = None,
    ) -> CompiledRules:
        return self.bind(self.compile_model(model), table, column_map=column_map)


def _is_backend(plugin: Any) -> bool:
    return callable(getattr(plugin, "prepare_value", None)) and callable(
        getattr(plugin, "capabilities", None)
    )


class _PluginAwareRegistry(TranslatorRegistry):
    """Apply the compiler's conflict policy to plugin register() calls."""

    def __init__(self, base: TranslatorRegistry, *, default_on_conflict: OnConflict) -> None:
        super().__init__()
        self._translators = {
            name: translator
            for name in base.operators()
            if (translator := base.lookup(name)) is not None
        }
        self._default_on_conflict = default_on_conflict

    def register(self, operator_name: str, translator: Any, *, replace: bool = False) -> None:
        policy = "replace" if replace else self._default_on_conflict
        self.register_constraint(operator_name, translator, on_conflict=policy)

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
            on_conflict=on_conflict or self._default_on_conflict,
        )


def _resolve_rule_column(
    field: RuleField,
    table: Any,
    column_map: Mapping[str, ColumnElement[Any]] | None,
) -> ColumnElement[Any]:
    if column_map and field.name in column_map:
        return resolve_column(field.name, table, column_map=column_map)
    if field.column is not None:
        try:
            return resolve_column(field.column, table)
        except MissingColumnError as exc:
            raise MissingColumnError(field=field.name) from exc
    return resolve_column(field.name, table)


def clear_model_cache() -> None:
    """Compatibility no-op; normalized schema lives immutably on each class."""


def compile(
    model: type[RuleSchema],
    table: Any,
    *,
    plugins: Sequence[SQLRulesPlugin],
    column_map: Mapping[str, ColumnElement[Any]] | None = None,
) -> CompiledRules:
    """One-shot 2.0 compile using explicitly selected backend plugins."""
    return Compiler(plugins=plugins).compile(model, table, column_map=column_map)


def flatten(compiled: CompiledRules) -> list[ColumnElement[bool]]:
    """Return the authoritative root predicate in spread-friendly list form."""
    _require_compiled(compiled)
    return [compiled.predicate]


def where(compiled: CompiledRules) -> list[ColumnElement[bool]]:
    """Return one complete predicate for a spread-style SQLAlchemy WHERE call."""
    return flatten(compiled)


def notwhere(compiled: CompiledRules) -> list[ColumnElement[bool]]:
    """Return the total complement selecting rows that fail any rule."""
    _require_compiled(compiled)
    return [~compiled.predicate]


def _require_compiled(value: Any) -> None:
    if not isinstance(value, CompiledRules):
        raise TypeError("where(), notwhere(), and flatten() require a CompiledRules result")


__all__ = ["Compiler", "clear_model_cache", "compile", "flatten", "notwhere", "where"]
