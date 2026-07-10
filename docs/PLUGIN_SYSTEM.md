# SQLRules Plugin System

## Purpose

The SQLRules plugin system allows applications and libraries to extend
the compiler without modifying SQLRules itself.

Plugins may register:

- New constraint translators
- Dialect-specific translators (overrides for the same IR operators)

The core package remains small while advanced functionality lives in
plugins. Compiler passes, type registration, and entry-point discovery
are reserved for later releases.

------------------------------------------------------------------------

# Design Goals

- Zero-cost when unused
- Deterministic compilation
- Stable public extension API (`PLUGIN_API_VERSION`)
- No monkey-patching
- Explicit registration

------------------------------------------------------------------------

# Architecture

``` text
                SQLRules Compiler
                       │
             ┌─────────┴─────────┐
             ▼                   ▼
      Built-in Registry    Plugin register()
             │                   │
             └─────────┬─────────┘
                       ▼
              Translator Dispatch
                       ▼
           SQLAlchemy Expressions
```

------------------------------------------------------------------------

# Plugin Interface

A plugin is a Python object that exposes `name`, `api_version`, and
`register(registry)`.

``` python
from sqlrules import PLUGIN_API_VERSION
from sqlrules.constraints import pattern_text
from sqlrules.translators import TranslatorRegistry

class CompanyPlugin:
    name = "company"
    api_version = PLUGIN_API_VERSION

    def register(self, registry: TranslatorRegistry) -> None:
        registry.register_constraint(
            "pattern",
            lambda c, col, ctx: col.op("~")(pattern_text(c.value)[0]),
            on_conflict="replace",
        )
```

`api_version` must equal `sqlrules.PLUGIN_API_VERSION` (`"1"` in 0.4).

------------------------------------------------------------------------

# Markers

Dialect-oriented constraints use `sqlrules.markers` (for example
`JsonContains`, `ArrayContains`). Markers implement the
`ConstraintMarker` protocol (`operator`, `value`) and are extracted into
IR. Plugins register translators for those operator names.

------------------------------------------------------------------------

# Registry API

``` python
registry.register_constraint(
    operator="pattern",
    translator=translate_pattern,
    on_conflict="raise",  # or "replace" / "ignore"
)
```

Legacy alias:

``` python
registry.register("pattern", translate_pattern, replace=False)
```

Introspection: `registry.operators()`, `operator in registry`, `registry.copy()`.

Invalid translators raise `InvalidTranslatorError`. Duplicate operators
raise `RegistryError` unless `on_conflict` / `replace` allows otherwise.

`register_type`, `register_dialect`, and `register_compiler_pass` are
not implemented (reserved).

------------------------------------------------------------------------

# Using Plugins

SQLRules does not auto-discover plugins. Register them explicitly:

``` python
from sqlrules import Compiler
from sqlrules_postgresql import PostgresPlugin

compiler = Compiler(
    plugins=[PostgresPlugin()],
    dialect="postgresql",  # optional hint for translators
    on_conflict="raise",   # default when plugins call register()
)
rules = compiler.compile(MyModel, table)
```

Module-level `sqlrules.compile(...)` does not accept plugins; use
`Compiler` when you need extensions.

When `plugins=` is set, the compiler copies the base registry first so
caller-owned registries are never mutated.

------------------------------------------------------------------------

# Dialect Plugins

Official packages (monorepo under `packages/`):

- `sqlrules-postgresql` — regex, JSONB, ARRAY, range
- `sqlrules-sqlite` — REGEXP helper + JSON
- `sqlrules-mysql` — REGEXP, JSON, full-text
- `sqlrules-mssql` — JSON + `LEN` length overrides

------------------------------------------------------------------------

# Conflict Resolution

`Compiler(on_conflict=...)` sets the default for plugin `register()` calls:

| Mode | Behavior |
|---|---|
| `raise` | `RegistryError` on duplicate (default) |
| `replace` | Overwrite existing translator |
| `ignore` | Keep the existing translator |

Plugins may still pass an explicit `on_conflict=` to
`register_constraint`.

------------------------------------------------------------------------

# Version Compatibility

``` python
from sqlrules import PLUGIN_API_VERSION  # "1"
```

Major plugin API changes increment this value. Mismatched plugins raise
`PluginError` at compiler construction.

------------------------------------------------------------------------

# Conformance Testing

``` python
from sqlrules.conformance import run_basic_conformance
from sqlrules_postgresql import PostgresPlugin

run_basic_conformance(PostgresPlugin(), operator="pattern")
```

Helpers also cover API version checks, builtin preservation, and
deterministic translation. Pass `model=` / `table=` / `field=` when
conformance-checking non-`pattern` operators.

------------------------------------------------------------------------

# Security

Plugins execute Python code. SQLRules does not sandbox plugins.
Install only trusted plugins.

------------------------------------------------------------------------

# Non-Goals

The plugin system does not support:

- Runtime SQL execution
- Database connections
- Automatic package downloads / entry-point discovery
- Dynamic code generation
- Compiler pass plugins (future)

------------------------------------------------------------------------

# Design Principles

- Small core
- Extensible architecture
- Explicit registration
- Stable plugin API
- Pure compiler extensions
- Deterministic behavior
