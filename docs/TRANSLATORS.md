# SQLRules Translator Architecture

## Purpose

Translators convert a single normalized constraint from the compiler's
Intermediate Representation (IR) into one or more SQLAlchemy boolean
expressions.

A translator has one responsibility:

> **Constraint IR → SQLAlchemy Expression**

It does not inspect Pydantic models, execute SQL, or perform validation.

------------------------------------------------------------------------

# Translator Pipeline

``` text
Constraint IR
      │
      ▼
Translator Registry
      │
      ▼
Constraint Translator
      │
      ▼
SQLAlchemy Expression
```

------------------------------------------------------------------------

# Translator Interface

Every translator implements a common interface.

``` python
translate(
    constraint,
    column,
    context,
) -> ColumnElement[bool]
```

Parameters:

-   `constraint` --- normalized IR object
-   `column` --- SQLAlchemy column
-   `context` --- compiler settings, dialect hints, registry

Returns:

-   SQLAlchemy boolean expression

------------------------------------------------------------------------

# Built-in Translators

## Numeric

  Constraint    Translation
  ------------- -----------------------
  gt            `column > value`
  ge            `column >= value`
  lt            `column < value`
  le            `column <= value`
  multiple_of   `column % value == 0`

------------------------------------------------------------------------

## String

  Constraint   Translation
  ------------ --------------------------------
  min_length   `func.length(column) >= value`
  max_length   `func.length(column) <= value`

Future:

-   pattern (IR in 0.2; translators via custom registry / dialect plugins)
-   starts_with
-   ends_with
-   contains

------------------------------------------------------------------------

## Literal

``` python
Literal["A", "B"]
```

↓

``` python
column.in_(["A", "B"])
```

------------------------------------------------------------------------

## Enum

``` python
class Status(Enum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
```

↓

``` python
column.in_(["ACTIVE", "DISABLED"])
```

------------------------------------------------------------------------

## Date / DateTime

Supported operators:

-   gt
-   ge
-   lt
-   le

Translation is identical to numeric comparison.

------------------------------------------------------------------------

# Translator Registry

The compiler owns a registry mapping IR operators to translators.

``` text
"gt"            -> GreaterThanTranslator
"ge"            -> GreaterEqualTranslator
"lt"            -> LessThanTranslator
"le"            -> LessEqualTranslator
"min_length"    -> MinLengthTranslator
"max_length"    -> MaxLengthTranslator
"literal"       -> LiteralTranslator
"enum"          -> EnumTranslator
```

The registry is responsible for dispatch only.

------------------------------------------------------------------------

# Design Rules

Each translator should:

-   perform exactly one translation
-   be deterministic
-   never mutate compiler state
-   never inspect unrelated fields
-   never execute SQL

------------------------------------------------------------------------

# Unsupported Constraints

If no translator exists, behavior depends on the compiler policy.

-   raise
-   warn
-   ignore

------------------------------------------------------------------------

# Custom Translators (Future)

Applications may register additional translators.

``` python
registry.register(
    operator="between",
    translator=BetweenTranslator(),
)
```

Custom translators should coexist with built-in translators without
requiring compiler changes.

------------------------------------------------------------------------

# Dialect Overrides (Future)

Some SQL constructs differ by backend.

Examples:

-   PostgreSQL regex
-   SQLite regex extensions
-   JSON operators
-   ARRAY operators

A dialect-specific registry may override the default translator while
preserving the same IR.

------------------------------------------------------------------------

# Testing Requirements

Every translator should have tests for:

-   successful translation
-   invalid input
-   edge values
-   deterministic output
-   SQLAlchemy expression type

One translator should never rely on another translator's implementation.

------------------------------------------------------------------------

# Design Principles

-   Small, composable classes or functions
-   One constraint per translator
-   Pure transformations
-   Easy to extend
-   Easy to unit test
-   Backend-independent IR
