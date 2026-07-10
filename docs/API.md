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
) -> dict[str, list[ColumnElement[bool]]]
```

| Parameter | Description |
|---|---|
| `model` | Pydantic `BaseModel` subclass |
| `table` | SQLAlchemy `Table`, alias, ORM class, or object with `.c` |
| `column_map` | Optional explicit field/alias → column mapping |
| `on_unsupported` | `"raise"` (default), `"warn"`, or `"ignore"` for unknown **operators** |
| `cache` | Cache Phase-1 model IR (default `True`) |

Rule dictionary keys are always the Python field names. String field aliases
are used only for column binding. Unconstrained fields are omitted.

Unsupported **types** always raise, regardless of `on_unsupported`.

Module-level `compile` does not accept plugins; use `Compiler`.

### `where` / `flatten`

```python
sqlrules.where(rules) -> list[ColumnElement[bool]]
sqlrules.flatten(rules) -> list[ColumnElement[bool]]
```

Identical aliases. Both are part of the stable Application API.

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
| `on_conflict` | Default for plugin `register()`: `"raise"`, `"replace"`, `"ignore"` |
| `dialect` | **Hint only** for custom translators on `CompilationContext`. Does **not** load plugins or change built-ins. Pass `plugins=[...]` explicitly. |
| `registry` | Optional base `TranslatorRegistry`; always **copied** into the compiler |

**Concurrency:** do not call `compile` / `bind` / `compile_model` concurrently
on the same `Compiler` instance. The shared Phase-1 IR cache is thread-safe
across instances; call `ModelIRCache.clear()` if you create many ephemeral models.

------------------------------------------------------------------------

## Plugin API (stable)

For dialect packages and custom translators. Import from `sqlrules`:

| Symbol | Role |
|---|---|
| `PLUGIN_API_VERSION` | Contract version string (`"1"`) |
| `SQLRulesPlugin` | Protocol: `name`, `api_version`, `register(registry)` |
| `TranslatorRegistry` | Register / lookup / copy translators |
| `default_registry` | Built-in portable translators |
| `pattern_text` | Unpack `PatternSpec` or `str` → `(pattern, ignore_case)` |
| `Constraint`, `PatternSpec`, `CompilationContext` | IR types used by translators |
| `ModelIR` | Two-phase / caching IR root |
| `ConstraintMarker` + marker dataclasses | Dialect operator metadata |
| `sqlrules.conformance` | Test helpers for plugin authors (supported) |

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

Version `"1"` includes `PatternSpec` for `pattern` values. Always use
`pattern_text(constraint.value)` — do not assume a bare `str`.

Bump `PLUGIN_API_VERSION` when changing translator signatures, registry
methods, or IR value types for built-in operators. See
[PLUGIN_SYSTEM.md](PLUGIN_SYSTEM.md).

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

See [ERRORS.md](ERRORS.md).
