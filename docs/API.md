# Public API

SQLRules exposes three stability tiers. Semver applies to the
**Application** and **Plugin** tiers. The **Internal** tier may change
in minor releases without notice.

------------------------------------------------------------------------

## Application API (stable)

Primary surface for application code:

| Symbol | Role |
|---|---|
| `compile` | One-shot compile (no plugins) |
| `where` / `flatten` | Flatten a rules dict (identical aliases; both supported) |
| `Compiler` | Reusable compiler with plugins / registry / cache |
| `clear_model_cache` | Clear the process-wide default Phase-1 IR cache |
| Exception hierarchy under `SQLRulesError` | Fail-fast errors |
| `__version__` | Package version |
| Markers (`JsonContains`, …) | `Annotated` metadata for dialect operators |

```python
sqlrules.compile(
    model,
    table,
    *,
    column_map=None,
    on_unsupported="raise",
    cache=True,
    emit_type_checks=False,
) -> dict[str, list[ColumnElement[bool]]]
```

| Parameter | Description |
|---|---|
| `model` | Pydantic `BaseModel` subclass |
| `table` | SQLAlchemy `Table`, alias, ORM class, or object with `.c` |
| `column_map` | Optional explicit field/alias → column mapping |
| `on_unsupported` | `"raise"` (default), `"warn"`, or `"ignore"` for unknown **operators** |
| `cache` | Cache Phase-1 model IR (default `True`) |
| `emit_type_checks` | When `True`, emit `type_check` IR for supported scalars (needs a plugin translator) |

Rule dictionary keys are always the Python field names. String field aliases
are used only for column binding. Unconstrained fields are omitted from the
rules dict (unless `emit_type_checks=True`) but **must still use a supported
type annotation**.

Unsupported **types** always raise, regardless of `on_unsupported`.

Module-level `compile` does not accept plugins; use `Compiler`.

**Raises** (typical): `InvalidModelError`, `MissingColumnError`,
`UnsupportedConstraintError`, `TranslatorError`, `ConfigurationError`.
See [ERRORS](ERRORS.md).

### `where` / `flatten`

```python
sqlrules.where(rules) -> list[ColumnElement[bool]]
sqlrules.flatten(rules) -> list[ColumnElement[bool]]
```

Identical aliases. Both are part of the stable Application API.

### `clear_model_cache`

```python
sqlrules.clear_model_cache() -> None
```

Clears the process-wide default Phase-1 `ModelIR` cache. Call this when
creating many ephemeral models (for example `pydantic.create_model`) so
cached IR does not grow without bound. Compilers constructed with a custom
`model_cache=` are unaffected.

### `Compiler`

```python
compiler = sqlrules.Compiler(
    on_unsupported="raise",
    registry=None,
    plugins=None,
    on_conflict="raise",
    dialect=None,
    cache=True,
    model_cache=None,
    emit_type_checks=False,
)
rules = compiler.compile(model, table, column_map=None)

# Two-phase (advanced Application API):
model_ir = compiler.compile_model(model)
rules = compiler.bind(model_ir, table, column_map=None)
compiler.diagnostics  # from the last bind/compile (translate phase)
```

| Parameter | Description |
|---|---|
| `plugins` | Optional `SQLRulesPlugin` instances registered at init |
| `on_conflict` | Default for plugin `register()` / `register_constraint()`: `"raise"`, `"replace"`, `"ignore"` |
| `dialect` | **Hint only** for custom translators on `CompilationContext`. Does **not** load plugins or change built-ins. Pass `plugins=[...]` explicitly. |
| `registry` | Optional base `TranslatorRegistry`; always **copied** into the compiler |
| `emit_type_checks` | Opt-in `type_check` IR from scalar annotations (`TypeSpec`) |

**Mutation:** do not call `compiler.registry.register(...)` (or
`register_constraint`) after construction. Register translators via
`plugins=` at init.

**Concurrency:** do not call `compile` / `bind` / `compile_model` concurrently
on the same `Compiler` instance. The shared Phase-1 IR cache is thread-safe
across instances; call `clear_model_cache()` if you create many ephemeral
models.

------------------------------------------------------------------------

## Plugin API (stable)

For dialect packages and custom translators. Import from `sqlrules`:

| Symbol | Role |
|---|---|
| `PLUGIN_API_VERSION` | Contract version string (`"1"`) — exact match required |
| `SQLRulesPlugin` | Protocol: `name`, `api_version`, `register(registry)` |
| `TranslatorRegistry` | Register / lookup / copy translators |
| `default_registry` | Copy of built-in portable translators |
| `pattern_text` | Unpack `PatternSpec` or `str` → `(pattern, ignore_case)` |
| `type_spec` / `TypeSpec` | Helpers for `type_check` IR (opt-in `emit_type_checks`) |
| `Constraint`, `PatternSpec`, `CompilationContext` | IR types used by translators |
| `ModelIR` | Two-phase / caching IR root |
| `ConstraintMarker` + marker dataclasses | Dialect operator metadata |
| `SQLRulesWarning` | Warning class used by `on_unsupported="warn"` |
| `sqlrules.conformance` | Test helpers for plugin authors (supported) |

Prefer `registry.register_constraint(..., on_conflict=...)`.
`register(..., replace=)` remains as a thin compatibility alias.

```python
from sqlrules import (
    PLUGIN_API_VERSION,
    Compiler,
    TranslatorRegistry,
    pattern_text,
)

class MyPlugin:
    name = "my-plugin"
    api_version = PLUGIN_API_VERSION

    def register(self, registry: TranslatorRegistry) -> None:
        registry.register_constraint(
            "pattern",
            lambda c, col, ctx: col.op("~")(pattern_text(c.value)[0]),
            on_conflict="replace",
        )

compiler = Compiler(plugins=[MyPlugin()], dialect="postgresql")
```

### `PLUGIN_API_VERSION` policy

Version `"1"` requires an **exact** string match (`api_version == "1"`).
It includes `PatternSpec` for `pattern` values. Always use
`pattern_text(constraint.value)` — do not assume a bare `str`.

Bump `PLUGIN_API_VERSION` to a new string (for example `"2"`) only when
changing translator signatures, registry methods, or IR value types for
built-in operators. See [PLUGIN_SYSTEM.md](PLUGIN_SYSTEM.md) and
[IR_CONTRACT.md](IR_CONTRACT.md).

Frozen marker operator names: `json_contains`, `json_has_key`,
`array_contains`, `array_overlap`, `range_contains`, `range_overlap`,
`fulltext_match`.

`register_type`, `register_dialect`, and `register_compiler_pass` are
**not** present on `TranslatorRegistry` in API v1 — do not probe with
`hasattr`.

------------------------------------------------------------------------

## Internal API (unstable)

Not covered by semver. Prefer Application/Plugin imports.

- `sqlrules.inspectors`, `sqlrules.columns`, `sqlrules.cache` helpers
- `DiagnosticsCollector`, private translator factories
- Module layout details

See [INTERNAL_API.md](INTERNAL_API.md).

------------------------------------------------------------------------

## Exceptions

All public exceptions inherit from `SQLRulesError`:

- `InvalidModelError`
- `MissingColumnError`
- `UnsupportedConstraintError`
- `TranslatorError`
- `InvalidTranslatorError`
- `RegistryError`
- `ConfigurationError`
- `PluginError`
- `InternalCompilerError` (reserved)

`SQLRulesWarning` is used when `on_unsupported="warn"`.

See [ERRORS.md](ERRORS.md).
