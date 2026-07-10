# SQLRules Error Handling

## Philosophy

SQLRules follows a fail-fast approach. If a Pydantic constraint cannot
be translated into a deterministic SQLAlchemy expression, the compiler
should report the problem immediately rather than silently producing
incomplete rules.

Goals:

-   Clear exception hierarchy
-   Helpful error messages
-   Deterministic behavior
-   Configurable handling for unsupported constraints

------------------------------------------------------------------------

# Exception Hierarchy

``` text
SQLRulesError
├── InvalidModelError
├── MissingColumnError
├── UnsupportedConstraintError
├── TranslatorError
├── InvalidTranslatorError
├── RegistryError
├── ConfigurationError
└── InternalCompilerError
```

All public exceptions inherit from `SQLRulesError`.

------------------------------------------------------------------------

# InvalidModelError

Raised when the input is not a supported Pydantic model.

Examples:

-   Not a BaseModel subclass
-   Generic model not yet supported
-   Invalid model definition

------------------------------------------------------------------------

# MissingColumnError

Raised when a model field cannot be matched to a SQLAlchemy column.

Example message:

    No SQLAlchemy column found for field 'age'.

------------------------------------------------------------------------

# UnsupportedConstraintError

Raised when SQLRules encounters a valid Pydantic constraint with no
translator.

Examples:

-   max_digits
-   decimal_places
-   custom validators
-   computed fields

Example:

    Constraint 'pattern' is not supported by SQLRules 0.1.

------------------------------------------------------------------------

# TranslatorError

Raised when a translator fails while generating a SQLAlchemy expression.

Possible causes:

-   Invalid constraint values
-   Unexpected SQLAlchemy objects
-   Dialect incompatibilities

------------------------------------------------------------------------

# InvalidTranslatorError

Raised when a registered translator does not implement the required
interface or returns an invalid object.

------------------------------------------------------------------------

# RegistryError

Raised for translator registry failures.

Examples:

-   Duplicate registrations
-   Missing translator
-   Invalid operator name

------------------------------------------------------------------------

# ConfigurationError

Raised when compiler configuration is inconsistent.

Examples:

-   Invalid `on_unsupported` mode
-   Invalid column mapping
-   Unsupported compiler options

------------------------------------------------------------------------

# InternalCompilerError

Raised only for unexpected internal failures that indicate a bug in
SQLRules.

Users encountering this error should report it.

------------------------------------------------------------------------

# Compiler Policies

The compiler supports three behaviors for unsupported constraints:

## raise (default)

Immediately raises `UnsupportedConstraintError`.

## warn

Emits a warning and skips the constraint.

## ignore

Silently skips unsupported constraints.

------------------------------------------------------------------------

# Error Message Guidelines

Every public exception should include:

-   field name
-   constraint/operator
-   offending value (when applicable)
-   suggested resolution

Example:

    Field 'age': constraint 'between' is not supported.

------------------------------------------------------------------------

# Logging

SQLRules should not log by default.

Applications decide how to handle exceptions and warnings.

------------------------------------------------------------------------

# Testing

Each exception should have tests covering:

-   expected trigger
-   message contents
-   inheritance from SQLRulesError
-   policy interactions

------------------------------------------------------------------------

# Design Principles

-   Fail fast
-   Never silently change semantics
-   Preserve deterministic compilation
-   Prefer explicit errors over implicit behavior
-   Keep exceptions stable across minor releases
