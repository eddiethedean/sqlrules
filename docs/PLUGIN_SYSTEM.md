# SQLRules Plugin System

> **Status: future design (not available in 0.2).**
> SQLRules 0.2 has no plugin hook. Use `Compiler(registry=...)` to supply
> custom translators (including `pattern`). This document describes the
> planned extension model.

## Purpose

The SQLRules plugin system will allow applications and libraries to extend
the compiler without modifying SQLRules itself.

Plugins may register:

- New constraint translators
- New type translators
- Dialect-specific translators
- Compiler passes
- Validation hooks (compile-time only)

The core package should remain small while advanced functionality lives
in plugins.

------------------------------------------------------------------------

# Design Goals

- Zero-cost when unused
- Deterministic compilation
- Stable public extension API
- No monkey-patching
- Explicit registration

------------------------------------------------------------------------

# Architecture

``` text
                SQLRules Compiler
                       │
             ┌─────────┴─────────┐
             ▼                   ▼
      Built-in Registry    Plugin Registry
             │                   │
             └─────────┬─────────┘
                       ▼
              Translator Dispatch
                       ▼
           SQLAlchemy Expressions
```

------------------------------------------------------------------------

# Plugin Interface

A plugin is a Python object that exposes a registration method.

``` python
class SQLRulesPlugin:
    def register(self, registry):
        ...
```

The compiler calls `register()` during initialization.

------------------------------------------------------------------------

# Registry API

Example:

``` python
registry.register_constraint(
    operator="between",
    translator=BetweenTranslator(),
)
```

Additional registration methods may include:

``` python
registry.register_type(...)
registry.register_dialect(...)
registry.register_compiler_pass(...)
```

------------------------------------------------------------------------

# Translator Plugins

Translator plugins add support for new constraints.

Example:

``` python
class BetweenTranslator:
    operator = "between"

    def translate(self, constraint, column, context):
        lower, upper = constraint.value
        return column.between(lower, upper)
```

------------------------------------------------------------------------

# Dialect Plugins

Some SQL constructs are database-specific.

Examples:

-   PostgreSQL regular expressions
-   PostgreSQL ARRAY operators
-   PostgreSQL JSONB operators
-   SQLite REGEXP extension
-   MySQL full-text search

Dialect plugins override or supplement built-in translators while
preserving the same intermediate representation (IR).

------------------------------------------------------------------------

# Compiler Pass Plugins

Future versions may expose compiler passes.

Example pipeline:

``` text
Constraint IR
      │
Normalize Pass
      │
Optimize Pass
      │
Translator Dispatch
```

Compiler passes must be pure transformations.

------------------------------------------------------------------------

# Discovery

SQLRules will not auto-discover plugins in the MVP.

Applications register plugins explicitly.

``` python
compiler = Compiler(
    plugins=[
        PostgresPlugin(),
        CompanyPlugin(),
    ]
)
```

Future versions may support Python entry points.

------------------------------------------------------------------------

# Conflict Resolution

When two plugins register the same operator:

Default behavior:

-   raise RegistryError

Optional policies:

-   replace
-   ignore
-   namespace

Explicit behavior is preferred over implicit overrides.

------------------------------------------------------------------------

# Version Compatibility

Plugins declare the SQLRules API version they support.

Example:

``` python
API_VERSION = "1"
```

Major API changes increment the plugin API version.

------------------------------------------------------------------------

# Testing

Every plugin should provide:

-   Unit tests
-   Translation tests
-   Compatibility tests
-   Deterministic output tests

SQLRules should include a plugin conformance test suite.

------------------------------------------------------------------------

# Security

Plugins execute Python code.

SQLRules does not sandbox plugins.

Applications should install only trusted plugins.

------------------------------------------------------------------------

# Non-Goals

The plugin system does not support:

-   Runtime SQL execution
-   Database connections
-   Automatic package downloads
-   Dynamic code generation

------------------------------------------------------------------------

# Future Ecosystem

Potential official plugins:

-   sqlrules-postgresql
-   sqlrules-sqlite
-   sqlrules-mysql
-   sqlrules-mssql
-   sqlrules-json
-   sqlrules-array
-   sqlrules-geo

These packages can evolve independently while the core compiler remains
small, stable, and focused.

------------------------------------------------------------------------

# Design Principles

-   Small core
-   Extensible architecture
-   Explicit registration
-   Stable plugin API
-   Pure compiler extensions
-   Deterministic behavior
