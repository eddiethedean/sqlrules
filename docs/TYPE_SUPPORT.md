# SQLRules Type Support Matrix

## Purpose

This document defines which Python and Pydantic field types SQLRules
supports and how each type is translated into SQLAlchemy WHERE
expressions.

SQLRules only supports types whose constraints can be translated
deterministically into SQLAlchemy boolean expressions.

------------------------------------------------------------------------

## Guiding Principles

- Prefer deterministic translations.
- Never guess SQL semantics.
- Unsupported types always fail fast (they are not softened by
  `on_unsupported`).
- Type support is independent of database dialect whenever possible.

------------------------------------------------------------------------

## Supported types (1.0)

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

## Numeric Types

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

## Strings

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

## Boolean

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

## Date, DateTime, and Time

Supported operators:

-   gt
-   ge
-   lt
-   le

`multiple_of` is rejected for temporal types.

No timezone conversion is performed by SQLRules. Aware and naive
`datetime` values are passed through unchanged.

------------------------------------------------------------------------

## UUID

Supported:

-   Unconstrained fields (skipped; no column required)
-   `Literal[...]` / `Enum`

Rejected:

-   length constraints
-   numeric comparisons

------------------------------------------------------------------------

## Enum

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

## Literal

Example:

``` python
Literal["A", "B", "C"]
```

↓

``` python
column.in_(["A", "B", "C"])
```

------------------------------------------------------------------------

## Optional Types

`Optional[T]` / `T | None` is supported.

By itself, optionality does not generate SQL rules unless
`emit_type_checks=True`, in which case `TypeSpec.allow_none` is set and
dialect translators emit `(column IS NULL) OR <type predicate>`.

------------------------------------------------------------------------

## Type checks (`emit_type_checks`)

Opt-in: `Compiler(emit_type_checks=True)` or
`sqlrules.compile(..., emit_type_checks=True)`.

When enabled, supported **scalar** annotations emit a `type_check`
constraint with `TypeSpec(python_type, strict, allow_none)`:

- Strictness from `Field(strict=…)`, `Strict()`, then
  `model_config = ConfigDict(strict=…)`
- `Literal` / `Enum` / `list` / `dict` do **not** get `type_check`
  (domain already covered or marker-only)

Core extracts IR only — there is **no portable translator**. Install a
dialect plugin (or register a custom `type_check` translator).

Approximations are dialect-specific and intentionally incomplete versus
full Pydantic coercion. Unsupported `(type, strict)` pairs raise
`UnsupportedConstraintError` rather than guessing. See dialect plugin
READMEs for the matrix.

Example:

```python
from sqlrules import Compiler
from sqlrules_postgresql import PostgresPlugin

class Filter(BaseModel):
    age: int

compiler = Compiler(plugins=[PostgresPlugin()], emit_type_checks=True)
rules = compiler.compile(Filter, users)
```

------------------------------------------------------------------------

## Containers

  Type     Status
  ------- --------
  list       ✅     Marker-driven fields only (e.g. `ArrayContains`)
  dict       ✅     Marker-driven fields only (e.g. `JsonContains`)
  tuple      ❌
  set        ❌

Portable constraints (`gt`, `min_length`, `pattern`, …) on `list` / `dict`
still raise. Use `sqlrules.markers` with a dialect plugin.

------------------------------------------------------------------------

## Unsupported Pydantic Features

The following are intentionally unsupported:

-   validators
-   field_validator
-   model_validator
-   computed_field
-   serializer hooks
-   arbitrary custom metadata (except `ConstraintMarker` instances)
-   custom validation functions
-   `max_digits` / `decimal_places` (deferred; no deterministic WHERE map)

These features require runtime execution or lack portable SQL semantics.

------------------------------------------------------------------------

## Post-1.0 expansion

Historical 0.2–0.4 delivery notes live in [MILESTONES](MILESTONES.md), not
here. This matrix is the **1.0** contract.

Planned *after* 1.0 (not available yet) only if SQL semantics are
deterministic: `starts_with` / `ends_with` / `contains`, decimal precision
constraints. See the project roadmap.

Support should expand only when the resulting SQL semantics are
well-defined across supported SQLAlchemy backends.

------------------------------------------------------------------------

## Compatibility

Target versions:

-   Python 3.10+
-   Pydantic v2
-   SQLAlchemy 2.x

------------------------------------------------------------------------

## Design Principles

-   Explicit support matrix
-   Stable translations
-   Backend-neutral semantics
-   Fail fast for unsupported types
-   Predictable compiler output
