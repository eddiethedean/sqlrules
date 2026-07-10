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

# Supported Types (v0.2)

  Python Type    Supported  Notes
  ------------- ----------- -------------------------------------
  bool              ✅      Equality / literal constraints only
  int               ✅      Numeric comparisons
  float             ✅      Numeric comparisons
  Decimal           ✅      Numeric comparisons (`max_digits` /
                            `decimal_places` still unsupported)
  str               ✅      Length constraints, Literal, Enum;
                            `pattern` IR only
  date              ✅      Range comparisons
  datetime          ✅      Range comparisons (no TZ conversion)
  time              ✅      Range comparisons
  Enum              ✅      Translated to `IN (...)`
  Literal           ✅      Translated to `IN (...)`
  UUID              ✅      Literal / Enum only
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

IR only (no portable translator in core):

-   pattern

Planned (later milestones):

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

# Date, DateTime, and Time

Supported operators:

-   gt
-   ge
-   lt
-   le

`multiple_of` is rejected for temporal types.

No timezone conversion is performed by SQLRules. Aware and naive
`datetime` values are passed through unchanged.

------------------------------------------------------------------------

# UUID

Supported:

-   Unconstrained fields (skipped; no column required)
-   `Literal[...]` / `Enum`

Rejected:

-   length constraints
-   numeric comparisons

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

Container validation has no direct SQL WHERE equivalent.

------------------------------------------------------------------------

# Unsupported Pydantic Features

The following are intentionally unsupported:

-   validators
-   field_validator
-   model_validator
-   computed_field
-   serializer hooks
-   arbitrary custom metadata
-   custom validation functions
-   `max_digits` / `decimal_places` (deferred; no deterministic WHERE map)

These features require runtime execution or lack portable SQL semantics.

------------------------------------------------------------------------

# Future Roadmap

## v0.3 ✅

-   translator / dialect plugins
-   pattern translators via `sqlrules-postgresql` / `sqlrules-sqlite`

## Later

-   decimal precision (if a clear WHERE semantics emerges)
-   JSON / ARRAY (dialect plugins)

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
