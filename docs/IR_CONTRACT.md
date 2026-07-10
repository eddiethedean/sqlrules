# IR contract (Plugin API v1)

This document freezes the intermediate representation that Plugin API
version `"1"` may rely on. Semver for plugins follows
`PLUGIN_API_VERSION`, not the core package minor.

## Roots

| Type | Role |
|---|---|
| `ModelIR` | Frozen model + ordered `FieldIR` tuple |
| `FieldIR` | `FieldDescriptor` + ordered `Constraint` tuple |
| `FieldDescriptor` | Field name, annotation, metadata, aliases |
| `Constraint` | `(field, operator, value)` |
| `PatternSpec` | `(pattern: str, ignore_case: bool)` for `pattern` |
| `TypeSpec` | `(python_type, strict, allow_none)` for `type_check` |
| `CompilationContext` | `on_unsupported`, diagnostics collector, optional `dialect` hint |
| `Diagnostic` | Structured skip/warn records (Plugin-visible; prefer not to depend on fields from Application code) |

All IR dataclasses are frozen (`slots=True`). Phase-1 IR never stores
SQLAlchemy columns.

## Operators

Portable operators extracted by core: `gt`, `ge`, `lt`, `le`,
`multiple_of`, `min_length`, `max_length`, `pattern`, `literal`, `enum`.

Opt-in operator (when `emit_type_checks=True`): `type_check` with
`TypeSpec` values. Core extracts IR only — no portable translator
(same pattern as `pattern`).

Frozen marker operator names: `json_contains`, `json_has_key`,
`array_contains`, `array_overlap`, `range_contains`, `range_overlap`,
`fulltext_match`.

`pattern` values are `PatternSpec` (or legacy `str` via `pattern_text()`).
Always call `pattern_text(constraint.value)` in translators.

`type_check` values are `TypeSpec`. Always call `type_spec(constraint.value)`
in translators.

## Application vs Plugin use

- **Application:** prefer `compile` / `Compiler` / markers / exceptions.
  Treat IR types as advanced (two-phase `compile_model` / `bind`).
- **Plugin:** may depend on `Constraint`, `PatternSpec`, `TypeSpec`,
  `CompilationContext`, `ModelIR`, `TranslatorRegistry`, markers,
  `pattern_text`, and `type_spec`.

## Whole-model type matrix

Every field annotation on a compiled model must be inside the type support
matrix — including unconstrained fields. Unsupported types (for example
`timedelta`) raise even when the field has no constraints. Split filter
models from DTOs that carry unsupported types.

## Not in IR (1.0)

`max_digits` and `decimal_places` are rejected at extract time. Unknown
Field metadata keys are rejected rather than turned into invented
operators.
