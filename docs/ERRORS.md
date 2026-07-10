# SQLRules Error Handling

## Philosophy

SQLRules follows a fail-fast approach. If a Pydantic constraint cannot
be translated into a deterministic SQLAlchemy expression, the compiler
should report the problem immediately rather than silently producing
incomplete rules.

Goals:

- Clear exception hierarchy
- Helpful error messages
- Deterministic behavior
- Configurable handling for unsupported **constraint operators**
- Structured diagnostics for skipped constraints

------------------------------------------------------------------------

# Exception Hierarchy

``` text
SQLRulesError
├── InvalidModelError
├── MissingColumnError
├── UnsupportedConstraintError
├── TranslatorError
├── InvalidTranslatorError   (reserved in 0.2)
├── RegistryError
├── ConfigurationError
└── InternalCompilerError    (reserved in 0.2)
```

All public exceptions inherit from `SQLRulesError`.

------------------------------------------------------------------------

# InvalidModelError

Raised when the input is not a supported Pydantic model.

Examples:

- Not a BaseModel subclass

------------------------------------------------------------------------

# MissingColumnError

Raised when a constrained model field cannot be matched to a SQLAlchemy
column. Unconstrained fields are skipped and do not trigger this error.

Non-column table attributes (for example `Table.name`) are never treated
as columns.

Example message:

    No SQLAlchemy column found for field 'age'. Provide a matching table
    column, ORM attribute, or column_map entry.

------------------------------------------------------------------------

# UnsupportedConstraintError

Raised when SQLRules encounters a constraint operator with no translator,
an unsupported type, or an invalid operator/type combination.

Examples:

- `pattern` (no core translator), `max_digits`, `decimal_places`
- custom validators / `Strict`
- unsupported types (containers, `timedelta`)
- `multiple_of <= 0`
- length constraints on non-`str` fields

Example:

    Field 'name': constraint 'pattern' is not supported by SQLRules.
    Remove the constraint, or set on_unsupported='warn'/'ignore'.

------------------------------------------------------------------------

# TranslatorError

Raised when a registered translator fails while generating a SQLAlchemy
expression (unexpected SQLAlchemy errors wrapped by the registry).

------------------------------------------------------------------------

# InvalidTranslatorError

Reserved for future validation of custom translators. Not raised by the
0.2 compiler path.

------------------------------------------------------------------------

# RegistryError

Raised for translator registry failures.

Examples:

- Duplicate registrations without `replace=True`

Missing operators raise `UnsupportedConstraintError`, not `RegistryError`.

------------------------------------------------------------------------

# ConfigurationError

Raised when compiler configuration is inconsistent.

In 0.2 this is raised for an invalid `on_unsupported` mode only.

------------------------------------------------------------------------

# InternalCompilerError

Reserved for unexpected internal failures. Not raised by the 0.2
compiler path.

------------------------------------------------------------------------

# Compiler Policies

The compiler supports three behaviors for unsupported **constraint
operators**:

## raise (default)

Immediately raises `UnsupportedConstraintError`.

## warn

Emits a `SQLRulesWarning`, records a `Diagnostic`, and skips the
constraint.

## ignore

Records a `Diagnostic` and silently skips unsupported constraints.

Unsupported **types** always raise, regardless of `on_unsupported`.

------------------------------------------------------------------------

# Structured Diagnostics

After `compile` / `bind` / `compile_model`, inspect skipped constraints:

```python
compiler = sqlrules.Compiler(on_unsupported="warn")
rules = compiler.compile(Model, table)
for diag in compiler.diagnostics:
    print(diag.severity, diag.field, diag.operator, diag.message)
```

`Diagnostic` fields: `severity` (`"warning"` | `"info"`), `field`,
`operator`, `value`, `message`.

`compile_model` clears diagnostics. Diagnostics are separate from
exceptions and do not change the rules dict return type.

Do not call `compile` / `bind` concurrently on the same `Compiler`
instance; diagnostics collection is not locked.

------------------------------------------------------------------------

# Error Message Guidelines

Every public exception should include:

- field name (when applicable)
- constraint/operator
- offending value (when applicable)
- suggested resolution

------------------------------------------------------------------------

# Logging

SQLRules does not log by default.

Applications decide how to handle exceptions, warnings, and diagnostics.

------------------------------------------------------------------------

# Testing

Each actively raised exception should have tests covering:

- expected trigger
- message contents
- inheritance from SQLRulesError
- policy interactions (where applicable)

------------------------------------------------------------------------

# Design Principles

- Fail fast
- Never silently change semantics
- Preserve deterministic compilation
- Prefer explicit errors over implicit behavior
- Keep exceptions stable across minor releases
