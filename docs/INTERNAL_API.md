# SQLRules Internal API

This document describes implementation modules. They are not covered by the
Application or Plugin API compatibility contracts unless explicitly re-exported
from `sqlrules`.

## Compilation pipeline

```text
RuleSchema class
    └── models.normalize_schema       → immutable SchemaSpec
          └── Compiler.bind          → resolve columns and select provider
                ├── backend provider → PreparedValue with safe type evidence
                ├── TranslatorRegistry → constraint predicates
                └── CompiledRules    → total root predicate + plan metadata
```

`compile_model()` normalizes one schema without binding it to a table.
`bind()` resolves the declared columns, asks the selected backend provider to
prepare each source value, translates every retained constraint, and returns a
`CompiledRules` object. The compiler does not connect to a database or execute
SQL.

## Modules

- `sqlrules.models` defines `RuleSchema`, the SQLRules `Field()` helper,
  `RuleConfig`, and schema normalization. It accepts compatible Pydantic field
  declarations and rejects declarations that cannot be represented as SQL
  predicates.
- `sqlrules.integrations.pydantic` implements `from_pydantic()` and conversion
  reports. It is public through the `sqlrules` package re-exports.
- `sqlrules.backend` prepares safe scalar expressions for providers. It is an
  implementation module; provider authors implement the public `BackendProvider`
  protocol instead of importing its private helpers.
- `sqlrules.columns` binds `RuleSchema` field names, aliases, explicit
  `Field(column=...)` metadata, and `column_map` entries to SQLAlchemy columns.
- `sqlrules.constraints` extracts compatible normalized constraints.
- `sqlrules.ir` contains schema, prepared-value, compiled-result, and translator
  data types. The public subset is re-exported from `sqlrules`.
- `sqlrules.translators` provides the public translator registry and built-in
  operator translators.
- `sqlrules.conformance` contains helpers used to check plugin contracts.

## State and caching

SQLRules does not maintain a process-wide strong-reference cache of model
classes. `RuleSchema` declarations are normalized when compiled. The legacy
`Compiler(cache=...)` argument and `clear_model_cache()` helper remain as
compatibility shims; neither changes caching behavior in 2.0. SQLAlchemy
columns and compiled predicates are always specific to a bind operation.

## Plugin boundary

Plugin authors should import the supported contracts from `sqlrules`:
`SQLRulesPlugin`, `BackendProvider`, `PLUGIN_API_VERSION`, `TranslatorRegistry`,
`Constraint`, `PatternSpec`, `PreparedValue`, `CompilationContext`, and marker
types. See [PLUGIN_SYSTEM.md](PLUGIN_SYSTEM.md) and
[IR_CONTRACT.md](IR_CONTRACT.md).

## Design constraints

- Every retained rule must translate or raise an actionable capability error.
- Type conversion and validation must not rely on database predicate
  evaluation order.
- Model validation remains ordinary Pydantic behavior; SQL compilation only
  consumes the supported SQLRules subset.
- Internal module names and helpers may change without a Plugin API version
  bump.
