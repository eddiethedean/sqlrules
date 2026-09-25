# SQLRules Compiler Architecture

The compiler normalizes SQLRules-owned Pydantic schemas, asks one explicitly
selected backend to prepare each bound column, translates retained constraints,
and combines the results into one total predicate. It does not connect to a
database or execute SQL.

## Pipeline

```text
RuleSchema declaration
        │ class-time validation and metadata normalization
        ▼
Immutable SchemaSpec / RuleField values
        │ bind field names to SQLAlchemy expressions
        ▼
Backend PreparedValue(source, value, valid, is_null)
        │ translate constraints over the prepared value
        ▼
Field predicates
        │ AND + SQL NULL normalization
        ▼
CompiledRules.predicate
```

`RuleSchema` subclasses retain Pydantic construction and validation behavior.
Unsupported declarations fail when the class is created. Full Pydantic models
are accepted through `from_pydantic()`, which returns a generated rule model
and a conversion report.

## Schema representation

`SchemaSpec` and `RuleField` contain table-independent information: field
order, annotation, logical type, nullability, strictness, constraints,
defaults, descriptive metadata, SQL column name, and conversion provenance.
They contain no table-bound SQL expressions. Every declared field must bind;
an annotation alone is a rule.

The normalizer reads public Pydantic field information and an explicit metadata
allowlist. It does not execute validators, serializers, or default factories.
The compiler normalizes at each compile call so rule compilation does not rely
on mutable shared diagnostics or cached SQL expressions.

## Source preparation and predicate grouping

Each backend provider returns a `PreparedValue` containing the original
column, a safe normalized expression, a type/coercion validity predicate, a
SQL NULL test, and capability details. Bounds, lengths, patterns, and domains
consume the normalized expression.

For a required field:

```text
column IS NOT NULL AND valid AND every constraint(value)
```

For a nullable field, SQL NULL is an allowed branch; a failed conversion that
produces NULL remains distinguishable from an original SQL NULL. The compiler
normalizes the result to SQL TRUE/FALSE, then ANDs all fields into
`CompiledRules.predicate`. `notwhere()` complements that total root.

The backend must make conversions safe regardless of SQL predicate evaluation
order. Unsupported representations raise `CapabilityError` during compile;
invalid row values become false predicates.

## Translators and providers

Portable translators handle scalar operators such as `ge`, `multiple_of`, and
`min_length`. Plugins add backend operators such as JSON containment, arrays,
ranges, regex, or full text. Backend providers implement source preparation
and capability reporting in addition to registering translators.

`Compiler(plugins=[...])` requires exactly one backend provider. Its translator
registry is a private snapshot; compile calls keep their diagnostics local.
The `dialect=` option is only a compatibility consistency check and never
selects or discovers a backend.

## Result API

`CompiledRules` contains the full predicate, per-field results, diagnostics,
backend version, assumptions, and conversion provenance. Its `explain()` method
returns a structured compile plan without running database `EXPLAIN`.

`where()` and `flatten()` return `[compiled.predicate]` to preserve the
spread-style SQLAlchemy call. `notwhere()` returns its total complement.

## Errors

- `InvalidModelError`: an unrestricted Pydantic model was passed directly.
- `UnsupportedConstraintError`: a declaration has no accepted SQL meaning.
- `MissingColumnError`: a declared rule field cannot be bound.
- `CapabilityError`: the selected provider cannot safely implement a retained
  type conversion or operator.
- `PluginError` / `RegistryError`: a provider or translator contract is invalid.

## Build extension

Custom operators register a translator accepting `(constraint, prepared_value,
context)` and returning a SQLAlchemy boolean expression. Backend providers may
implement `prepare_value()` and `capabilities()` to establish source type
evidence and safe conversions. See [PLUGIN_SYSTEM](PLUGIN_SYSTEM.md).
