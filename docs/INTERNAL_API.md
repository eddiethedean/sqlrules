# SQLRules Internal API

## Purpose

This document describes **implementation modules** used inside SQLRules.
They are **not** part of the Application or Plugin semver contracts
unless re-exported in [API.md](API.md).

Plugin authors should import from `sqlrules` (`TranslatorRegistry`,
`pattern_text`, `Constraint`, `PatternSpec`, …), not from private
helpers.

------------------------------------------------------------------------

## Pipeline (actual modules)

``` text
compile() / Compiler
    │
    ├── inspectors.inspect_model      → FieldDescriptor[]
    ├── constraints.extract_constraints / ensure_supported_type
    ├── cache.ModelIRCache            → ModelIR (optional)
    ├── columns.resolve_column
    ├── translators.TranslatorRegistry.translate
    └── assemble dict[str, list[ColumnElement[bool]]]
```

There are no separate `IRBuilder` / `RuleAssembler` / `ModelInspector`
classes — those names are historical. Behavior lives in the modules above
plus `sqlrules.compiler`.

------------------------------------------------------------------------

## Compiler

Orchestrates the two phases: `compile_model` (IR) and `bind` (columns +
translate). See the public `Compiler` in [API.md](API.md).

------------------------------------------------------------------------

## inspectors

`inspect_model(model) -> list[FieldDescriptor]`

Enumerates fields in declaration order, including string aliases.

------------------------------------------------------------------------

## constraints

`extract_constraints` / `ensure_supported_type` / `pattern_text`

`pattern_text` is part of the **Plugin API** (also exported from
`sqlrules`). Other helpers here are internal.

------------------------------------------------------------------------

## columns

`resolve_column(...)` maps field names / aliases / `column_map` to
SQLAlchemy columns. Never treats non-column `Table` attributes as columns.

------------------------------------------------------------------------

## translators

`TranslatorRegistry` and `default_registry` are **Plugin API**.

------------------------------------------------------------------------

## cache

`ModelIRCache` — process-lifetime strong-key cache. Call `clear()` when
using many ephemeral model classes. Not a public Application export.

------------------------------------------------------------------------

## plugins / conformance

`SQLRulesPlugin`, `PLUGIN_API_VERSION`, and `sqlrules.conformance` are
Plugin API. See [PLUGIN_SYSTEM.md](PLUGIN_SYSTEM.md).

------------------------------------------------------------------------

## Design Principles

- Small Application API
- Explicit Plugin API
- Internals may change between minors
- Deterministic compilation
- No database I/O
