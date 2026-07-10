# Public API

SQLRules exposes a deliberately small public surface.

## `compile`

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

Compile a constrained Pydantic model into a field-keyed rule dictionary.

| Parameter | Description |
|---|---|
| `model` | Pydantic `BaseModel` subclass |
| `table` | SQLAlchemy `Table`, alias, ORM class, or object with `.c` |
| `column_map` | Optional explicit `field_name` or alias → column mapping. If a key matches but the value is not a column, raises `MissingColumnError` (no fallthrough). |
| `on_unsupported` | `"raise"` (default), `"warn"`, or `"ignore"` for unknown **operators** only |
| `cache` | Cache Phase-1 model IR (default `True`) |

Rule dictionary keys are always the Python field names. String field aliases
(`alias`, `validation_alias`, `serialization_alias`) are used only for column
binding. Unconstrained fields are omitted and do not require a column.

Unsupported types always raise, regardless of `on_unsupported`.

Module-level `compile` does not accept plugins; use `Compiler` for extensions.

## `where` / `flatten`

```python
sqlrules.where(rules) -> list[ColumnElement[bool]]
sqlrules.flatten(rules) -> list[ColumnElement[bool]]
```

Flatten a rule dictionary into a single list of expressions suitable for
`Query.where(*expressions)` or `select(...).where(*expressions)`.

`where` and `flatten` are identical aliases.

## `Compiler`

```python
compiler = sqlrules.Compiler(
    on_unsupported="raise",
    registry=None,
    plugins=None,
    on_conflict="raise",
    dialect=None,
    cache=True,
    model_cache=None,  # optional shared ModelIRCache; default is process-wide
)
rules = compiler.compile(model, table, column_map=None)

# Two-phase (advanced):
model_ir = compiler.compile_model(model)  # also clears diagnostics
rules = compiler.bind(model_ir, table, column_map=None)

# Diagnostics from the last compile_model / compile / bind:
compiler.diagnostics
```

| Parameter | Description |
|---|---|
| `plugins` | Optional sequence of `SQLRulesPlugin` objects registered at init |
| `on_conflict` | Default conflict policy for plugin `register()`: `"raise"`, `"replace"`, or `"ignore"` |
| `dialect` | Optional string hint stored on `CompilationContext` (never auto-detected) |
| `registry` | Optional base `TranslatorRegistry`; copied when `plugins` is non-empty |

Reusable compiler instance with a fixed unsupported-constraint policy,
optional plugins, optional custom translator registry, and optional Phase-1
metadata cache.

`compile_model` / `bind` separate static IR extraction from table binding so
the same `ModelIR` can be reused across tables.

**Concurrency:** do not call `compile` / `bind` / `compile_model` concurrently
on the same `Compiler` instance (diagnostics are per-instance and not locked).
The shared Phase-1 IR cache is thread-safe for concurrent reads/writes across
instances.

## Plugins

```python
from sqlrules import PLUGIN_API_VERSION, Compiler
from sqlrules.constraints import pattern_text

class MyPlugin:
    name = "my-plugin"
    api_version = PLUGIN_API_VERSION

    def register(self, registry):
        registry.register_constraint(
            "pattern",
            lambda c, col, ctx: col.op("~")(pattern_text(c.value)[0]),
            on_conflict="replace",
        )

compiler = Compiler(plugins=[MyPlugin()])
```

Dialect markers (`JsonContains`, `ArrayContains`, …) are extracted into IR
and translated by official dialect plugins. See [PLUGIN_SYSTEM.md](PLUGIN_SYSTEM.md).
Conformance helpers live in `sqlrules.conformance`.

## Other exports

Also exported for advanced use and typing:

- `__version__`
- `PLUGIN_API_VERSION`, `SQLRulesPlugin`
- `SQLRulesWarning`
- `CompilationContext`, `Constraint`, `FieldDescriptor`, `FieldIR`, `ModelIR`,
  `Diagnostic`, `PatternSpec`
- Markers: `ConstraintMarker`, `JsonContains`, `JsonHasKey`, `ArrayContains`,
  `ArrayOverlap`, `RangeContains`, `RangeOverlap`, `FullTextMatch`

`DiagnosticsCollector` and `ModelIRCache` are internal (import from
`sqlrules.ir` / `sqlrules.cache` only if you accept instability).

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

See [ERRORS.md](ERRORS.md) for details.
