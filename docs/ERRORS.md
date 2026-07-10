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

------------------------------------------------------------------------

# Exception Hierarchy

``` text
SQLRulesError
├── InvalidModelError
├── MissingColumnError
├── UnsupportedConstraintError
├── TranslatorError
├── InvalidTranslatorError   (reserved in 0.1)
├── RegistryError
├── ConfigurationError
└── InternalCompilerError    (reserved in 0.1)
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

- `pattern`, `max_digits`, `decimal_places`
- custom validators / `Strict`
- unsupported types (`UUID`, containers, `time`, `timedelta`)
- `multiple_of <= 0`
- length constraints on non-`str` fields

Example:

    Field 'name': constraint 'pattern' is not supported by SQLRules 0.1.
    Remove the constraint, or set on_unsupported='warn'/'ignore'.

------------------------------------------------------------------------

# TranslatorError

Raised when a registered translator fails while generating a SQLAlchemy
expression (unexpected SQLAlchemy errors wrapped by the registry).

------------------------------------------------------------------------

# InvalidTranslatorError

Reserved for future validation of custom translators. Not raised by the
0.1 compiler path.

------------------------------------------------------------------------

# RegistryError

Raised for translator registry failures.

Examples:

- Duplicate registrations without `replace=True`

Missing operators raise `UnsupportedConstraintError`, not `RegistryError`.

------------------------------------------------------------------------

# ConfigurationError

Raised when compiler configuration is inconsistent.

In 0.1 this is raised for an invalid `on_unsupported` mode only.

------------------------------------------------------------------------

# InternalCompilerError

Reserved for unexpected internal failures. Not raised by the 0.1
compiler path.

------------------------------------------------------------------------

# Compiler Policies

The compiler supports three behaviors for unsupported **constraint
operators**:

## raise (default)

Immediately raises `UnsupportedConstraintError`.

## warn

Emits a `SQLRulesWarning` and skips the constraint.

## ignore

Silently skips unsupported constraints.

Unsupported **types** always raise, regardless of `on_unsupported`.

------------------------------------------------------------------------

# Error Message Guidelines

Every public exception should include:

- field name (when applicable)
- constraint/operator
- offending value (when applicable)
- suggested resolution

Example:

    Field 'age': constraint 'between' is not supported by SQLRules 0.1.

------------------------------------------------------------------------

# Logging

SQLRules does not log by default.

Applications decide how to handle exceptions and warnings.

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
