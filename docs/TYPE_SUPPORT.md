# SQLRules Type Support Matrix

## Purpose

This document defines which Python and Pydantic field types SQLRules
supports and how each type is translated into SQLAlchemy WHERE
expressions.

SQLRules only supports types whose constraints can be translated
deterministically into SQLAlchemy boolean expressions.

------------------------------------------------------------------------

# Guiding Principles

- Prefer deterministic translations.
- Never guess SQL semantics.
- Unsupported types always fail fast (they are not softened by
  `on_unsupported`).
- Type support is independent of database dialect whenever possible.

------------------------------------------------------------------------

# Supported Types (v0.1)

  Python Type    Supported  Notes
  ------------- ----------- -------------------------------------
  bool              ✅      Equality / literal constraints only
  int               ✅      Numeric comparisons
  float             ✅      Numeric comparisons
  Decimal           ✅      Numeric comparisons
  str               ✅      Length constraints, Literal, Enum
  date              ✅      Range comparisons
  datetime          ✅      Range comparisons
  Enum              ✅      Translated to `IN (...)`
  Literal           ✅      Translated to `IN (...)`
  UUID              ❌      Not supported in 0.1 (planned)
  time              ❌      Not supported in 0.1 (planned)
  timedelta         ❌      No deterministic SQL mapping yet

------------------------------------------------------------------------

# Numeric Types

Supported constraints:

-   gt
-   ge
-   lt
-   le
-   multiple_of

Example:

``` python
age: Annotated[int, Field(ge=18, le=65)]
```

↓

``` python
[
    users.c.age >= 18,
    users.c.age <= 65,
]
```

------------------------------------------------------------------------

# Strings

Supported constraints:

-   min_length
-   max_length

Planned:

-   pattern
-   starts_with
-   ends_with
-   contains

Example:

``` python
name: Annotated[str, Field(min_length=2)]
```

↓

``` python
func.length(users.c.name) >= 2
```

------------------------------------------------------------------------

# Boolean

Boolean fields generally do not produce rules unless constrained through
`Literal` or similar constructs.

Examples:

``` python
Literal[True]
Literal[False]
```

↓

``` python
column.in_([True])
```

------------------------------------------------------------------------

# Date and DateTime

Supported operators:

-   gt
-   ge
-   lt
-   le

No timezone conversion is performed by SQLRules.

------------------------------------------------------------------------

# Enum

Example:

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

# Literal

Example:

``` python
Literal["A", "B", "C"]
```

↓

``` python
column.in_(["A", "B", "C"])
```

------------------------------------------------------------------------

# Optional Types

`Optional[T]` is supported.

By itself, optionality does not generate SQL rules.

Future compiler options may allow generation of `IS NOT NULL`
expressions.

------------------------------------------------------------------------

# Containers

  Type     Status
  ------- --------
  list       ❌
  tuple      ❌
  set        ❌
  dict       ❌

Container validation has no direct SQL WHERE equivalent in the MVP.

------------------------------------------------------------------------

# Unsupported Pydantic Features

The following are intentionally unsupported in v0.1:

-   validators
-   field_validator
-   model_validator
-   computed_field
-   serializer hooks
-   arbitrary custom metadata
-   custom validation functions

These features require runtime execution and cannot be translated
deterministically.

------------------------------------------------------------------------

# Future Roadmap

## v0.2

-   UUID
-   time
-   regex
-   decimal precision
-   JSON fields

## v0.3

-   ARRAY support
-   PostgreSQL JSON operators
-   custom translator plugins

## Long-term

Support should expand only when the resulting SQL semantics are
well-defined across supported SQLAlchemy backends.

------------------------------------------------------------------------

# Compatibility

Target versions:

-   Python 3.10+
-   Pydantic v2
-   SQLAlchemy 2.x

------------------------------------------------------------------------

# Design Principles

-   Explicit support matrix
-   Stable translations
-   Backend-neutral semantics
-   Fail fast for unsupported types
-   Predictable compiler output
