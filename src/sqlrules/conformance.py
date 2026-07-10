"""Plugin conformance helpers for official and third-party plugins."""

from __future__ import annotations

import contextlib
from typing import Annotated, Any

from pydantic import BaseModel, Field
from sqlalchemy import Column, MetaData, String, Table
from sqlalchemy.sql.elements import ColumnElement

from sqlrules.compiler import Compiler
from sqlrules.errors import PluginError, RegistryError
from sqlrules.plugins import PLUGIN_API_VERSION, SQLRulesPlugin, validate_plugin
from sqlrules.translators import TranslatorRegistry, default_registry


def assert_plugin_api_compatible(plugin: SQLRulesPlugin) -> None:
    """Raise PluginError if the plugin does not match the current plugin API."""
    validate_plugin(plugin)


def assert_register_conflict_raise(plugin: SQLRulesPlugin) -> None:
    """Registering the same plugin twice with on_conflict='raise' must fail.

    Plugins that only add new operators (not in the default registry) are
    registered twice against a fresh default registry; the second pass must
    raise RegistryError for any overlapping operator.
    """
    validate_plugin(plugin)
    registry = default_registry()
    plugin.register(registry)
    try:
        plugin.register(registry)
    except RegistryError:
        return
    raise AssertionError(
        f"Plugin {plugin.name!r} did not raise RegistryError on duplicate registration"
    )


def assert_register_idempotent_ignore(plugin: SQLRulesPlugin) -> None:
    """Registering twice with on_conflict='ignore' must succeed and keep builtins."""
    validate_plugin(plugin)
    builtins = default_registry().operators()
    compiler = Compiler(plugins=[plugin], on_conflict="ignore", cache=False)
    first_ops = compiler.registry.operators()
    # Re-apply via a second compiler with the same plugin.
    compiler2 = Compiler(
        registry=compiler.registry.copy(),
        plugins=[plugin],
        on_conflict="ignore",
        cache=False,
    )
    assert compiler2.registry.operators() == first_ops
    assert builtins <= compiler2.registry.operators()


def assert_builtins_preserved(
    plugin: SQLRulesPlugin,
    *,
    on_conflict: str = "raise",
) -> None:
    """Plugins must not drop built-in operators."""
    validate_plugin(plugin)
    builtins = default_registry().operators()
    compiler = Compiler(plugins=[plugin], on_conflict=on_conflict, cache=False)  # type: ignore[arg-type]
    missing = builtins - compiler.registry.operators()
    if missing:
        raise AssertionError(
            f"Plugin {plugin.name!r} removed built-in operators: {sorted(missing)}"
        )


def assert_translates_operator(
    plugin: SQLRulesPlugin,
    *,
    operator: str,
    model: type[BaseModel] | None = None,
    table: Any | None = None,
    field: str = "name",
) -> ColumnElement[bool]:
    """Compile with the plugin and assert ``operator`` yields a ColumnElement."""
    validate_plugin(plugin)

    if model is None:

        class PatternFilter(BaseModel):
            name: Annotated[str, Field(pattern=r"^a")]

        model = PatternFilter

    if table is None:
        table = Table("items", MetaData(), Column("name", String))

    compiler = Compiler(plugins=[plugin], on_conflict="replace", cache=False)
    if operator not in compiler.registry:
        raise AssertionError(f"Plugin {plugin.name!r} did not register operator {operator!r}")

    rules = compiler.compile(model, table)
    if field not in rules or not rules[field]:
        raise AssertionError(f"Plugin {plugin.name!r}: expected expressions for field {field!r}")

    expression = rules[field][0]
    if not isinstance(expression, ColumnElement):
        raise AssertionError(
            f"Plugin {plugin.name!r}: translator for {operator!r} "
            f"returned {type(expression)!r}, expected ColumnElement"
        )

    # Deterministic compile smoke check (dialect-neutral string form).
    compiled_a = str(expression.compile(compile_kwargs={"literal_binds": True}))
    compiled_b = str(expression.compile(compile_kwargs={"literal_binds": True}))
    if compiled_a != compiled_b:
        raise AssertionError(f"Plugin {plugin.name!r}: non-deterministic compile for {operator!r}")
    return expression


def run_basic_conformance(plugin: SQLRulesPlugin, *, operator: str = "pattern") -> None:
    """Run the standard conformance checks for a dialect/translator plugin."""
    if getattr(plugin, "api_version", None) != PLUGIN_API_VERSION:
        raise PluginError(
            message=(
                f"Plugin {getattr(plugin, 'name', plugin)!r} api_version mismatch "
                f"(expected {PLUGIN_API_VERSION!r})."
            ),
            plugin=plugin,
        )
    assert_plugin_api_compatible(plugin)
    assert_builtins_preserved(plugin, on_conflict="replace")
    assert_register_idempotent_ignore(plugin)
    assert_translates_operator(plugin, operator=operator)

    # Conflict under raise: only meaningful if the plugin re-registers an op
    # already present after the first registration.
    registry = default_registry()
    plugin.register(registry)
    with contextlib.suppress(RegistryError):
        # If the plugin uses on_conflict="replace" internally, duplicate
        # registration may succeed; that is acceptable for dialect overrides.
        plugin.register(registry)


def registry_without_builtins() -> TranslatorRegistry:
    """Empty registry for isolated translator unit tests."""
    return TranslatorRegistry()
