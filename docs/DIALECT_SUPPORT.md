# SQLRules Dialect Support

## Purpose

SQLRules compiles Pydantic constraints into SQLAlchemy expressions.
SQLAlchemy already abstracts many database differences, but some
operators and functions have dialect-specific behavior. This document
defines how SQLRules handles those differences while keeping the
compiler deterministic.

------------------------------------------------------------------------

# Philosophy

1.  Prefer portable SQLAlchemy constructs.
2.  Keep the core compiler dialect-neutral.
3.  Isolate database-specific behavior behind dialect extensions.
4.  Never silently change semantics based on the active database.

------------------------------------------------------------------------

# Support Levels

  Level          Meaning
  -------------- -------------------------------------------------
  Core           Uses only portable SQLAlchemy expressions.
  Enhanced       Uses optional dialect-specific translators.
  Experimental   Feature exists but semantics differ by backend.

------------------------------------------------------------------------

# Dialects

Core emits portable SQLAlchemy Core expressions. The table below describes
**intended** dialect posture, not a certified multi-backend test matrix.

  Dialect             Status        Notes
  ------------ -------------------- --------------------------------
  SQLite             Core + plugin  `sqlrules-sqlite` — REGEXP + JSON
  PostgreSQL         Core + plugin  `sqlrules-postgresql` — regex, JSONB, ARRAY, range
  MySQL              Core + plugin  `sqlrules-mysql` — REGEXP, JSON, full-text
  MariaDB            Core + plugin  Follows MySQL plugin where practical
  SQL Server         Core + plugin  `sqlrules-mssql` — JSON + `LEN`
  Oracle             Planned        Core support after 1.0

------------------------------------------------------------------------

# Core Portable Constraints

These should compile identically across supported databases:

-   gt
-   ge
-   lt
-   le
-   multiple_of
-   min_length
-   max_length
-   Literal
-   Enum

------------------------------------------------------------------------

# Shared dialect markers

Dialect-oriented operators are expressed with `sqlrules.markers` and
extracted into IR. Core does not translate them; plugins register
translators for the stable operator names:

-   `JsonContains` → `json_contains`
-   `JsonHasKey` → `json_has_key`
-   `ArrayContains` → `array_contains`
-   `ArrayOverlap` → `array_overlap`
-   `RangeContains` → `range_contains`
-   `RangeOverlap` → `range_overlap`
-   `FullTextMatch` → `fulltext_match`

`list` / `dict` field annotations are allowed for marker-driven fields.
Portable constraints on containers still raise.

------------------------------------------------------------------------

# PostgreSQL

Package: `sqlrules-postgresql`

-   `pattern` → `~` or `~*` (`PatternSpec.ignore_case`)
-   JSONB containment / key checks
-   ARRAY contains / overlap
-   range `@>` / `&&`

------------------------------------------------------------------------

# SQLite

Package: `sqlrules-sqlite`

-   `pattern` via `REGEXP` — call `register_regexp(connection)`
-   Case-insensitive patterns use a `(?i)` prefix understood by the helper
-   JSON helpers via JSON1 `json_extract` / `json_type`

------------------------------------------------------------------------

# MySQL / MariaDB

Package: `sqlrules-mysql`

-   `pattern` → `REGEXP`
-   JSON operators (`JSON_CONTAINS`, `JSON_CONTAINS_PATH`)
-   `fulltext_match` → `MATCH ... AGAINST` (requires FULLTEXT index)

------------------------------------------------------------------------

# SQL Server

Package: `sqlrules-mssql`

-   `min_length` / `max_length` → `LEN`
-   JSON helpers via `JSON_VALUE` / `JSON_QUERY`
-   `pattern` is not registered (no deterministic portable regex)

------------------------------------------------------------------------

# Oracle

Long-term goals:

-   Oracle-specific translators
-   Optimized string semantics
-   Date/time enhancements

------------------------------------------------------------------------

# Translator Selection

The compiler dispatches through a registry.

``` text
Constraint IR
      │
      ▼
Core Translator
      │
      ├── Portable implementation
      │
      └── Dialect override (optional)
```

If no override exists, the portable translator is used.

------------------------------------------------------------------------

# Plugin Packages

Official plugins:

-   sqlrules-postgresql
-   sqlrules-sqlite
-   sqlrules-mysql
-   sqlrules-mssql

Each package registers only the translators relevant to its backend.

------------------------------------------------------------------------

# Testing Strategy

Every supported dialect should include:

-   Unit tests
-   SQL compilation tests
-   Regression tests

The same Pydantic model should produce equivalent logical behavior
across supported databases whenever a portable translation exists.

------------------------------------------------------------------------

# Compatibility Policy

Minor SQLRules releases may add dialect features.

Major releases may change plugin APIs but should preserve the behavior
of portable translators whenever possible.

------------------------------------------------------------------------

# Non-Goals

SQLRules will not:

-   Open database connections
-   Detect the active database automatically
-   Rewrite SQL generated by SQLAlchemy
-   Emulate unsupported database features

Applications remain responsible for selecting the correct dialect
plugin.

------------------------------------------------------------------------

# Design Principles

-   Portable by default
-   Explicit dialect extensions
-   Stable compiler behavior
-   No hidden database assumptions
-   Maximum SQLAlchemy compatibility
