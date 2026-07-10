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

    ``emit_type_checks`` (default ``False``) extracts ``type_check`` IR from
    supported scalar annotations. Translation requires a dialect plugin or
    custom translator (same pattern as ``pattern``).

    Do not mutate ``registry`` after construction; registration belongs in
    ``plugins`` / ``register_constraint`` during init. Do not call
    ``compile`` / ``bind`` / ``compile_model`` concurrently on the same
    instance.
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
        emit_type_checks: bool = False,
    ) -> None:
        """Create a compiler with an optional plugin set and policies.

        Args:
            registry: Optional base ``TranslatorRegistry``. Always copied;
                the caller's registry is never mutated.
            plugins: ``SQLRulesPlugin`` instances registered at init.
            on_conflict: Default conflict policy for plugin registration
                (``"raise"``, ``"replace"``, or ``"ignore"``).
            on_unsupported: Policy for unknown **operators** (``"raise"``,
                ``"warn"``, or ``"ignore"``). Unsupported **types** always
                raise.
            dialect: Hint stored on ``CompilationContext`` only — does not
                load plugins.
            cache: When ``True``, cache Phase-1 ``ModelIR`` in ``model_cache``.
            model_cache: Optional cache instance; defaults to the process-wide
                shared cache. Custom caches are not cleared by
                ``clear_model_cache()``.
            emit_type_checks: When ``True``, extract ``type_check`` IR for
                supported scalars (needs a plugin translator to bind).

        Raises:
            ConfigurationError: Invalid ``on_unsupported`` or ``on_conflict``.
            PluginError: Plugin failed validation (missing attributes or
                ``api_version`` mismatch).
            RegistryError: Plugin registration conflict under ``on_conflict``.
            InvalidTranslatorError: Plugin registered a non-callable or
                wrong-arity translator.
        """
        if on_unsupported not in {"raise", "warn", "ignore"}:
            raise ConfigurationError(option="on_unsupported", value=on_unsupported)
        if on_conflict not in {"raise", "replace", "ignore"}:
            raise ConfigurationError(option="on_conflict", value=on_conflict)

        # Always copy so caller-owned and shared default registries are never mutated.
        # default_registry() already returns a copy of the builtin template.
        base = registry.copy() if registry is not None else default_registry()
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
        self.emit_type_checks = emit_type_checks
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
            cached = self._model_cache.get(model, emit_type_checks=self.emit_type_checks)
            if cached is not None:
                return cached

        model_strict = bool(getattr(model, "model_config", {}).get("strict", False))
        fields: list[FieldIR] = []
        for descriptor in inspect_model(model):
            ensure_supported_type(descriptor)
            constraints = tuple(
                extract_constraints(
                    descriptor,
                    emit_type_checks=self.emit_type_checks,
                    model_strict=model_strict,
                )
            )
            fields.append(FieldIR(descriptor=descriptor, constraints=constraints))

        model_ir = ModelIR(model=model, fields=tuple(fields))
        if self.cache_enabled:
            return self._model_cache.put(model, model_ir, emit_type_checks=self.emit_type_checks)
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
            expressions: list[ColumnElement[bool]] = []
            column: ColumnElement[Any] | None = None

            for constraint in field_ir.constraints:
                # Resolve the column only when a translator will run, so
                # on_unsupported=warn|ignore can skip missing columns for
                # entirely unsupported fields (e.g. pattern-only).
                if self.registry.lookup(constraint.operator) is None:
                    self.registry.handle_missing_translator(constraint, self.context)
                    continue
                if column is None:
                    column = resolve_column(
                        descriptor.name,
                        table,
                        column_map,
                        alias=descriptor.alias,
                        aliases=descriptor.aliases,
                    )
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
        """Compile ``model`` constraints and bind them to ``table`` columns.

        Args:
            model: Pydantic ``BaseModel`` subclass whose Field metadata is
                compiled (instance values are never applied).
            table: SQLAlchemy ``Table``, selectable, ORM class, or object
                with ``.c``.
            column_map: Optional field-name or alias → column mapping.

        Returns:
            Mapping of Python field names to lists of boolean
            ``ColumnElement`` expressions. Unconstrained supported-type
            fields are omitted.

        Raises:
            InvalidModelError: ``model`` is not a usable Pydantic model.
            MissingColumnError: A constrained field could not bind.
            UnsupportedConstraintError: No translator for an operator/type,
                or ``emit_type_checks`` / ``pattern`` without a translator.
            TranslatorError: A registered translator failed at bind time.
            ConfigurationError: Invalid compiler configuration.
        """
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


def clear_model_cache() -> None:
    """Clear the process-wide default Phase-1 ``ModelIR`` cache.

    Use this when creating many ephemeral models (for example
    ``pydantic.create_model``) so cached IR does not grow without bound.
    Compilers that were given a custom ``model_cache`` are unaffected.
    """
    default_cache().clear()


def compile(
    model: type[BaseModel],
    table: Any,
    *,
    column_map: Mapping[str, ColumnElement[Any]] | None = None,
    on_unsupported: OnUnsupported = "raise",
    cache: bool = True,
    emit_type_checks: bool = False,
) -> RulesDict:
    """One-shot Application API compile (no plugins).

    Compiles **Field constraint metadata** into SQLAlchemy expressions.
    Does not apply model instance / request values.

    Creates a fresh ``Compiler`` per call so concurrent module-level
    ``compile()`` invocations do not share mutable diagnostics state.
    Phase-1 IR still uses the process-wide cache when ``cache=True``.

    Args:
        model: Pydantic ``BaseModel`` subclass.
        table: SQLAlchemy ``Table``, selectable, ORM class, or object with
            ``.c``.
        column_map: Optional field-name or alias → column mapping.
        on_unsupported: Policy for unknown **operators** (``"raise"``,
            ``"warn"``, or ``"ignore"``). Unsupported **types** always raise.
        cache: Cache Phase-1 model IR (default ``True``).
        emit_type_checks: Emit ``type_check`` IR for supported scalars
            (requires a plugin translator — use ``Compiler(plugins=...)``).

    Returns:
        Mapping of Python field names to lists of boolean
        ``ColumnElement`` expressions.

    Raises:
        InvalidModelError: ``model`` is not a usable Pydantic model.
        MissingColumnError: A constrained field could not bind.
        UnsupportedConstraintError: No translator for an operator/type.
        TranslatorError: A registered translator failed at bind time.
        ConfigurationError: Invalid ``on_unsupported`` value.

    Note:
        For plugins, construct ``Compiler(plugins=[...])`` explicitly.
    """
    return Compiler(
        on_unsupported=on_unsupported,
        cache=cache,
        emit_type_checks=emit_type_checks,
    ).compile(model, table, column_map=column_map)


def flatten(rules: RulesDict) -> list[ColumnElement[bool]]:
    """Flatten a rules dict into a single list of expressions.

    Args:
        rules: Mapping of field name to lists of boolean column elements,
            as returned by ``compile`` / ``Compiler.compile``.

    Returns:
        Concatenated list suitable for spreading into a SQLAlchemy
        ``where`` clause.
    """
    return list(chain.from_iterable(rules.values()))


def where(rules: RulesDict) -> list[ColumnElement[bool]]:
    """Flatten a rules dict for a SQLAlchemy ``where`` clause.

    Identical to :func:`flatten`. Prefer this name at call sites.

    Args:
        rules: Mapping of field name to lists of boolean column elements.

    Returns:
        Concatenated list of expressions.
    """
    return flatten(rules)
