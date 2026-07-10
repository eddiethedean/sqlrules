"""SQLRules 0.3 plugin system tests."""

from __future__ import annotations

from typing import Annotated, Any

import pytest
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Table
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.sql.elements import ColumnElement

import sqlrules
from sqlrules.conformance import (
    assert_builtins_preserved,
    assert_plugin_api_compatible,
    assert_register_idempotent_ignore,
    assert_translates_operator,
    run_basic_conformance,
)
from sqlrules.ir import CompilationContext, Constraint, DiagnosticsCollector
from sqlrules.plugins import PLUGIN_API_VERSION, validate_plugin
from sqlrules.translators import TranslatorRegistry, default_registry


class _PatternPlugin:
    name = "test-pattern"
    api_version = PLUGIN_API_VERSION

    def register(self, registry: TranslatorRegistry) -> None:
        registry.register_constraint(
            "pattern",
            lambda c, col, ctx: col.op("~")(c.value),
            on_conflict="replace",
        )


class _BadVersionPlugin:
    name = "bad-version"
    api_version = "999"

    def register(self, registry: TranslatorRegistry) -> None:
        return None


class _OverrideGtPlugin:
    name = "override-gt"
    api_version = PLUGIN_API_VERSION

    def register(self, registry: TranslatorRegistry) -> None:
        registry.register("gt", lambda c, col, ctx: col > c.value)


def test_plugin_api_version_constant() -> None:
    assert PLUGIN_API_VERSION == "1"
    assert sqlrules.PLUGIN_API_VERSION == "1"


def test_validate_plugin_rejects_bad_version() -> None:
    with pytest.raises(sqlrules.PluginError, match="api_version"):
        validate_plugin(_BadVersionPlugin())


def test_validate_plugin_rejects_non_plugin() -> None:
    with pytest.raises(sqlrules.PluginError, match="SQLRulesPlugin"):
        validate_plugin(object())


def test_compiler_plugins_register_pattern(items: Table) -> None:
    class Filter(BaseModel):
        name: Annotated[str, Field(pattern=r"^a")]

    compiler = sqlrules.Compiler(plugins=[_PatternPlugin()], cache=False)
    rules = compiler.compile(Filter, items)
    assert "name" in rules
    compiled = str(rules["name"][0].compile(dialect=postgresql.dialect()))
    assert "~" in compiled


def test_compiler_on_conflict_raise() -> None:
    with pytest.raises(sqlrules.RegistryError):
        sqlrules.Compiler(plugins=[_OverrideGtPlugin()], on_conflict="raise", cache=False)


def test_compiler_on_conflict_replace() -> None:
    compiler = sqlrules.Compiler(
        plugins=[_OverrideGtPlugin()],
        on_conflict="replace",
        cache=False,
    )
    assert "gt" in compiler.registry


def test_compiler_on_conflict_ignore() -> None:
    captured: list[Any] = []

    class Override:
        name = "override-gt"
        api_version = PLUGIN_API_VERSION

        def register(self, registry: TranslatorRegistry) -> None:
            def alt(
                c: Constraint, col: ColumnElement[Any], ctx: CompilationContext
            ) -> ColumnElement[bool]:
                return col > c.value

            captured.append(alt)
            registry.register("gt", alt)

    compiler = sqlrules.Compiler(
        plugins=[Override()],
        on_conflict="ignore",
        cache=False,
    )
    assert captured
    assert compiler.registry.lookup("gt") is not captured[0]


def test_invalid_on_conflict() -> None:
    with pytest.raises(sqlrules.ConfigurationError, match="on_conflict"):
        sqlrules.Compiler(on_conflict="explode")  # type: ignore[arg-type]


def test_invalid_translator_not_callable() -> None:
    registry = TranslatorRegistry()
    with pytest.raises(sqlrules.InvalidTranslatorError):
        registry.register("custom", None)  # type: ignore[arg-type]


def test_invalid_translator_arity() -> None:
    registry = TranslatorRegistry()

    def bad(a: Any, b: Any) -> Any:
        return a

    with pytest.raises(sqlrules.InvalidTranslatorError):
        registry.register("custom", bad)  # type: ignore[arg-type]


def test_register_constraint_ignore() -> None:
    registry = default_registry()
    first = registry.lookup("gt")
    registry.register_constraint(
        "gt",
        lambda c, col, ctx: col > c.value,
        on_conflict="ignore",
    )
    assert registry.lookup("gt") is first


def test_register_constraint_replace() -> None:
    registry = default_registry()

    def alt(c: Constraint, col: ColumnElement[Any], ctx: CompilationContext) -> ColumnElement[bool]:
        return col > c.value

    registry.register_constraint("gt", alt, on_conflict="replace")
    assert registry.lookup("gt") is alt


def test_registry_copy_and_operators() -> None:
    registry = default_registry()
    clone = registry.copy()
    assert clone.operators() == registry.operators()
    assert "gt" in clone
    clone.register_constraint(
        "pattern",
        lambda c, col, ctx: col.op("~")(c.value),
        on_conflict="raise",
    )
    assert "pattern" in clone
    assert "pattern" not in registry


def test_plugins_do_not_mutate_external_registry() -> None:
    external = default_registry()
    before = external.operators()
    sqlrules.Compiler(registry=external, plugins=[_PatternPlugin()], cache=False)
    assert external.operators() == before
    assert "pattern" not in external


def test_dialect_hint_on_context(items: Table) -> None:
    seen: list[str | None] = []

    class CapturePlugin:
        name = "capture"
        api_version = PLUGIN_API_VERSION

        def register(self, registry: TranslatorRegistry) -> None:
            def translate(
                constraint: Constraint,
                column: ColumnElement[Any],
                context: CompilationContext,
            ) -> ColumnElement[bool]:
                seen.append(context.dialect)
                return column.op("~")(constraint.value)

            registry.register_constraint("pattern", translate, on_conflict="replace")

    class Filter(BaseModel):
        name: Annotated[str, Field(pattern=r"^x")]

    compiler = sqlrules.Compiler(
        plugins=[CapturePlugin()],
        dialect="postgresql",
        cache=False,
    )
    compiler.compile(Filter, items)
    assert seen == ["postgresql"]


def test_diagnostic_code_on_warn(items: Table) -> None:
    class Filter(BaseModel):
        name: Annotated[str, Field(pattern=r"^a")]

    compiler = sqlrules.Compiler(on_unsupported="warn", cache=False)
    with pytest.warns(sqlrules.SQLRulesWarning):
        compiler.compile(Filter, items)
    assert compiler.diagnostics[0].code == "unsupported_constraint"


def test_diagnostic_code_on_ignore() -> None:
    collector = DiagnosticsCollector()
    registry = TranslatorRegistry()
    registry.translate(
        Constraint("name", "pattern", r"^A"),
        Column("name", String),
        CompilationContext(on_unsupported="ignore", collector=collector),
    )
    assert collector.snapshot()[0].code == "unsupported_constraint"


def test_conformance_helpers(items: Table) -> None:
    plugin = _PatternPlugin()
    assert_plugin_api_compatible(plugin)
    assert_builtins_preserved(plugin, on_conflict="replace")
    assert_register_idempotent_ignore(plugin)
    expr = assert_translates_operator(plugin, operator="pattern", table=items)
    assert isinstance(expr, ColumnElement)
    run_basic_conformance(plugin, operator="pattern")


def test_validate_plugin_rejects_empty_name() -> None:
    class EmptyName:
        name = ""
        api_version = PLUGIN_API_VERSION

        def register(self, registry: TranslatorRegistry) -> None:
            return None

    with pytest.raises(sqlrules.PluginError, match="non-empty"):
        validate_plugin(EmptyName())


def test_validate_plugin_rejects_non_callable_register() -> None:
    class BadRegister:
        name = "bad"
        api_version = PLUGIN_API_VERSION
        register = "nope"  # type: ignore[assignment]

    with pytest.raises(sqlrules.PluginError, match="callable register"):
        validate_plugin(BadRegister())


def test_register_constraint_invalid_on_conflict() -> None:
    registry = TranslatorRegistry()
    with pytest.raises(sqlrules.RegistryError, match="on_conflict"):
        registry.register_constraint(
            "x",
            lambda c, col, ctx: col == c.value,
            on_conflict="nope",  # type: ignore[arg-type]
        )


def test_configuration_error_generic_option() -> None:
    err = sqlrules.ConfigurationError(option="dialect", value=123)
    assert "dialect" in str(err)


def test_conformance_conflict_raise_helper() -> None:
    from sqlrules.conformance import assert_register_conflict_raise

    class DupPlugin:
        name = "dup"
        api_version = PLUGIN_API_VERSION

        def register(self, registry: TranslatorRegistry) -> None:
            # Use raise (default) so second registration conflicts.
            registry.register_constraint(
                "pattern",
                lambda c, col, ctx: col.op("~")(c.value),
            )

    assert_register_conflict_raise(DupPlugin())


def test_conformance_assert_conflict_raises_on_replace_plugin() -> None:
    from sqlrules.conformance import assert_register_conflict_raise

    with pytest.raises(AssertionError, match="did not raise"):
        assert_register_conflict_raise(_PatternPlugin())


def test_plugin_error_str() -> None:
    err = sqlrules.PluginError(message="boom", plugin=None)
    assert str(err) == "boom"


def test_validate_translator_varargs() -> None:
    registry = TranslatorRegistry()

    def flexible(*args: Any) -> Any:
        constraint, column, _context = args
        return column == constraint.value

    registry.register("eq_custom", flexible)
    assert "eq_custom" in registry


def test_plugin_aware_register_constraint_default() -> None:
    """Compiler adapter applies on_conflict when register_constraint omits it."""

    class SoftPlugin:
        name = "soft"
        api_version = PLUGIN_API_VERSION

        def register(self, registry: TranslatorRegistry) -> None:
            registry.register_constraint(
                "pattern",
                lambda c, col, ctx: col.op("~")(c.value),
            )

    # First registration ok; second compiler with ignore should not error.
    sqlrules.Compiler(plugins=[SoftPlugin()], on_conflict="raise", cache=False)
    sqlrules.Compiler(plugins=[SoftPlugin()], on_conflict="ignore", cache=False)


def test_module_compile_stays_plugin_free(items: Table) -> None:
    class Filter(BaseModel):
        name: Annotated[str, Field(pattern=r"^a")]

    with pytest.raises(sqlrules.UnsupportedConstraintError):
        sqlrules.compile(Filter, items)


def test_sqlite_compile_smoke_with_custom_pattern(items: Table) -> None:
    class Filter(BaseModel):
        name: Annotated[str, Field(pattern=r"^a")]

    class SqliteLikePlugin:
        name = "sqlite-like"
        api_version = PLUGIN_API_VERSION

        def register(self, registry: TranslatorRegistry) -> None:
            registry.register_constraint(
                "pattern",
                lambda c, col, ctx: col.op("REGEXP")(c.value),
                on_conflict="replace",
            )

    rules = sqlrules.Compiler(plugins=[SqliteLikePlugin()], cache=False).compile(Filter, items)
    compiled = str(rules["name"][0].compile(dialect=sqlite.dialect()))
    assert "REGEXP" in compiled
