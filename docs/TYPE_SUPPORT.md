# SQLRules 2.0 Type and Coercion Support

This page defines the logical values accepted by RuleSchema and the source
representations that each official backend can safely prepare for SQL
constraints. Compilation never probes a database connection. A caller selects
one backend provider and supplies server-version information when a capability
depends on it.

## Logical types

RuleSchema supports bool, int, float, Decimal, str, date, datetime, time, UUID,
homogeneous Literal domains, and Enum domains with one supported scalar value
type. Optional annotations add a SQL NULL branch. List and dict fields are
marker-driven and do not validate nested values or collection items.

Every scalar annotation produces a type rule, even when it has no other
constraints. The supported Pydantic declarations include Field constraints,
ConfigDict strictness, strict aliases, supported constrained aliases, and
compatible Annotated markers.

## Coercion profile

Lax mode follows this SQLRules profile rather than relying on implicit database
casts:

| Source representation | Target | 2.0 behavior |
|---|---|---|
| Matching native logical type | Same type | Match, then apply constraints |
| Integer | float or Decimal | Lax conversion where the backend can represent the full signed 64-bit source range; see the backend matrix |
| Float or Decimal | int | Lax conversion only when the value is an exact integer in signed 64-bit range |
| Numeric text | int | Signed decimal digits with optional surrounding whitespace; accepted magnitude is limited by the backend profile |
| Numeric text | float | Decimal/exponent grammar where the backend has a safe parser |
| Numeric text | Decimal | PostgreSQL 16+ only |
| Any known mismatched type in strict mode | Any other type | Non-match |
| Unknown SQLAlchemy type or unavailable evidence | Any target | CapabilityError |

SQLRules integer coercion uses a signed 64-bit target range because the
supported SQL backends do not share Python's unbounded integer arithmetic.
SQLite and MySQL text-to-int conversion conservatively accepts at most 18
digits. The SQLRules profile rejects fractional values for integer fields and
does not coerce numbers to strings. Textual date, datetime, time, and UUID
parsing is not part of 2.0.

Pydantic and SQLRules validation are intentionally close for supported
annotations, but database storage only exposes database logical types. SQLRules
does not claim to recover the Python object originally inserted into a row.

## Backend matrix

The following matrix describes compile-time support in the implementation.
Execution evidence is provided by CI's [live database conformance job](../.github/workflows/ci.yml)
and its [shared backend corpus](../tests/test_live_backend_conformance.py),
which run against PostgreSQL 16, MySQL 8.0, and SQL Server 2022. The corpus
checks malformed text, integer overflow, fractional and strict mismatches,
SQL NULL, native scalar constraints, UUID where native storage exists, and the
`where()`/`notwhere()` partition. SQLite execution coverage is in the regular
suite's [storage and JSON tests](../tests/test_sqlite_execution.py) and
[plugin tests](../packages/sqlrules-sqlite/tests/test_sqlite_plugin.py). The
2.0.0 implementation's live database conformance job passed on
[the merged main commit](https://github.com/eddiethedean/sqlrules/actions/runs/36252286710).

| Backend | Native scalar source types | Lax conversions | Important limitations |
|---|---|---|---|
| PostgreSQL 16+ | bool, int, float, Decimal, str, date, datetime, time, UUID | text to int/float/Decimal; int or Decimal to float; integral float/Decimal to int | Pass server_version for text conversions. String Literal/Enum requires collation C or POSIX. |
| SQLite 3.x | runtime integer, real, and text classes | text to int/float; integral real to int; integer to float; lax bool from integer 0/1 | Strict bool, Decimal, date/time, and UUID require storage mappings and raise CapabilityError. Text checks and string length constraints require `register_sqlite_functions()`. Text-to-int is limited to 18 digits. |
| MySQL 8.0+ | Boolean (0/1 checked), integer, float, Decimal, text, date/time | text to int; integer/Decimal to float; integral float/Decimal to int | UUID storage is not treated as native evidence. Text-to-float and text-to-Decimal are rejected. Integer-to-Decimal is rejected because the default cast precision is too small for every signed 64-bit integer. String Literal/Enum requires an explicit `_bin` collation; membership checks character length to account for PAD SPACE collations. `CHAR` columns are rejected because trailing-space retrieval depends on a session mode. |
| SQL Server 2012+ | bit, integer, float, Decimal, text, date/time, uniqueidentifier | text to int/float; integer/Decimal to float; integral float/Decimal to int | Text-to-Decimal and integer-to-Decimal are rejected because a default cast precision cannot represent the full source domain. JSON markers additionally require SQL Server 2016+ and explicit database `compatibility_level >= 130` because they use `OPENJSON`; `JsonContains` supports object payloads and structurally compared arrays, rejects top-level scalar payloads, and rejects numeric JSON comparisons because `OPENJSON` exposes numbers as text and no lossless general conversion is available. String Literal/Enum requires an explicit `_BIN2` collation; membership also checks byte length to account for padded string equality. Regex pattern translation is unavailable. |

The provider capability report lists the configured version and assumptions.
If the source SQLAlchemy type does not establish the required logical type,
compilation raises CapabilityError instead of emitting a guessed predicate.

SQLite uses typeof() at runtime because column affinity does not prove the
storage class of an individual row. Its integer storage class cannot
distinguish a Python bool from a Python int, so strict bool is unavailable
without an explicit mapping. SQLite NUMERIC affinity cannot prove exact
Decimal precision. SQLAlchemy Date, DateTime, Time, and UUID representations
are emulated on SQLite and are not treated as native logical types.

## Constraints and domains

Portable scalar constraints are gt, ge, lt, le, multiple_of, min_length,
max_length, Literal membership, and Enum membership. Pattern is available only
when the selected backend registers a translator. The SQL Server plugin has no
pattern translator.

String Literal and Enum membership requires comparisons with case-sensitive
semantics. PostgreSQL requires C or POSIX collation, SQLite uses BINARY, and
MySQL requires an explicit `_bin` collation and SQL Server requires `_BIN2`.
Their string-domain predicates additionally compare candidate and column lengths
so trailing spaces cannot make distinct Python strings match.
This prevents server-default case folding from silently broadening a domain.

The type and constraint combination is checked when RuleSchema is created.
Duplicate constraints, contradictory bounds, unsupported metadata, arbitrary
validators, serializers, computed fields, and normalization transforms are
rejected. A full Pydantic model can still use those features outside SQLRules;
from_pydantic() reports and removes unsupported behavior before compilation.

## Nulls and complements

For a field, SQLRules computes:

~~~text
SQL NULL -> match only when the annotation is nullable
non-NULL -> type/coercion validity AND every field constraint
~~~

Each field result and the complete root predicate are normalized to SQL TRUE
or FALSE. where(compiled) returns a one-element list containing the complete
predicate. notwhere(compiled) returns its complement, so every row is selected
by exactly one side. An explicitly allowed empty schema compiles to TRUE and
its notwhere() complement is FALSE.

## Deferred capabilities

2.0 does not translate general unions, recursive types, nested JSON schemas,
collection item validation, cross-field rules, arbitrary Python callbacks,
named transforms, or custom storage mappings. Later 2.x phases build on the
prepared-value and capability contracts defined here.

Requires Python 3.10+, Pydantic v2, and SQLAlchemy 2.x.
