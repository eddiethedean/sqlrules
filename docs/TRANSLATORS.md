# SQLRules Translator Architecture

## Purpose

Translators convert a single normalized constraint from the compiler's
Intermediate Representation (IR) into one or more SQLAlchemy boolean
expressions.

A translator has one responsibility:

> **Constraint IR → SQLAlchemy Expression**

It does not inspect Pydantic models, execute SQL, or perform validation.

------------------------------------------------------------------------

## Translator Pipeline

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

## Translator Interface

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

## Built-in Translators

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

**`pattern` (1.0):** extracted as `PatternSpec` in core IR; **no portable
core translator**. Install `sqlrules-postgresql` / `sqlrules-sqlite` /
`sqlrules-mysql`, or register a custom translator. SQL Server
(`sqlrules-mssql`) does **not** register `pattern`.

**Not in 1.0:** `starts_with`, `ends_with`, `contains`.

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

## Date / DateTime / Time

Supported operators:

-   gt
-   ge
-   lt
-   le

Translation is identical to numeric comparison. `multiple_of` is rejected
for temporal types.

------------------------------------------------------------------------

## Translator Registry

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

## Design Rules

Each translator should:

-   perform exactly one translation
-   be deterministic
-   never mutate compiler state
-   never inspect unrelated fields
-   never execute SQL

------------------------------------------------------------------------

## Unsupported Constraints

If no translator exists, behavior depends on the compiler policy.

-   raise
-   warn
-   ignore

------------------------------------------------------------------------

## Custom Translators

Applications may register additional translators on a
`TranslatorRegistry` and pass it to `Compiler(registry=...)`, or use the
plugin API:

``` python
from sqlrules import Compiler, PLUGIN_API_VERSION
from sqlrules.constraints import pattern_text
from sqlrules.translators import default_registry

registry = default_registry()
registry.register_constraint(
    "pattern",
    lambda constraint, column, context: column.op("~")(
        pattern_text(constraint.value)[0]
    ),
    on_conflict="replace",
)
compiler = Compiler(registry=registry)
```

``` python
class PatternPlugin:
    name = "pattern"
    api_version = PLUGIN_API_VERSION

    def register(self, registry):
        registry.register_constraint(
            "pattern",
            lambda c, col, ctx: col.op("~")(pattern_text(c.value)[0]),
            on_conflict="replace",
        )

compiler = Compiler(plugins=[PatternPlugin()])
```

------------------------------------------------------------------------

## Dialect Overrides

Some SQL constructs differ by backend. Official packages:

-   `sqlrules-postgresql` — `~` / `~*`, JSONB, ARRAY, range
-   `sqlrules-sqlite` — REGEXP helper + JSON
-   `sqlrules-mysql` — REGEXP, JSON, full-text
-   `sqlrules-mssql` — JSON + `LEN` length overrides

A dialect plugin overrides the default translator while preserving the
same IR. See [PLUGIN_SYSTEM.md](PLUGIN_SYSTEM.md) and
[DIALECT_SUPPORT.md](DIALECT_SUPPORT.md).

------------------------------------------------------------------------

## Testing Requirements

Every translator should have tests for:

-   successful translation
-   invalid input
-   edge values
-   deterministic output
-   SQLAlchemy expression type

One translator should never rely on another translator's implementation.

------------------------------------------------------------------------

## Design Principles

-   Small, composable classes or functions
-   One constraint per translator
-   Pure transformations
-   Easy to extend
-   Easy to unit test
-   Backend-independent IR
