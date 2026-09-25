# IR contract (Plugin API v2)

This page describes the stable intermediate representation available to
Plugin API version 2. The exact compatibility value is
sqlrules.PLUGIN_API_VERSION.

## Schema IR

| Type | Role |
|---|---|
| SchemaSpec | RuleSchema class, ordered fields, empty-schema policy, provenance |
| RuleField | Name, annotation, logical type, nullability, strictness, constraints, metadata |
| Constraint | Field name, stable operator name, normalized value |

Schema IR is independent of table bindings. It contains no SQLAlchemy
expressions. RuleField values preserve Python field order and source model
metadata. The compiler normalizes each class per compile, so mutable extension
payloads cannot leave stale process-wide schema IR.

## Backend preparation

| Type | Role |
|---|---|
| PreparedValue | Source column, normalized SQL value, total validity, null identity, logical type, coercion, capability |
| CompilationContext | Backend name, configured server version, assumptions, diagnostics |
| Diagnostic | Compile-scoped structured result message |

BackendProvider.prepare_value(column, field, context) returns PreparedValue.
Every conversion must be safe for malformed and out-of-range row values even
if a database changes predicate evaluation order. Validity is total and does
not rely on a CAST being guarded by a separate AND expression.

Constraint translators receive the normalized PreparedValue.value expression
as their SQLAlchemy expression argument. They do not reimplement source
coercion or infer stored Python types.

## Result IR

| Type | Role |
|---|---|
| FieldResult | Ordered bound field predicate and source/capability summary |
| CompiledRules | Complete root predicate, fields, diagnostics, backend, and assumptions |

CompiledRules.predicate is the authoritative complete predicate. It evaluates
to SQL TRUE or FALSE. where(compiled) returns a one-item list with the root;
notwhere(compiled) returns a one-item list with its complement. flatten()
aliases where(). Empty schemas are accepted only when explicitly configured;
their root is TRUE.

## Operators

Portable core operators are gt, ge, lt, le, multiple_of, min_length,
max_length, literal, and enum. Pattern and dialect markers remain plugin
operators.

Frozen marker operator names are json_contains, json_has_key, array_contains,
array_overlap, range_contains, range_overlap, and fulltext_match.

The opt-in type_check / TypeSpec IR from API v1 is removed from the 2.0
compiler path. Scalar annotations now produce a backend-prepared type rule
automatically.

## Plugin compatibility

API v2 plugins must expose the exact api_version string. Backend providers
must expose prepare_value() and capabilities(). The compiler requires exactly
one provider when binding a schema. Constraint plugins can be included with
that provider and register translators through TranslatorRegistry.

See [PLUGIN_SYSTEM](PLUGIN_SYSTEM.md) for translator examples.
