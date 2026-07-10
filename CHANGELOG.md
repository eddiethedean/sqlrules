# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0/).

## [0.1.0] - 2026-07-10

### Added

- Public API: `compile()`, `where()`, `flatten()`, and `Compiler`
- Constraint support: `gt`, `ge`, `lt`, `le`, `multiple_of`, `min_length`,
  `max_length`, `Literal`, and `Enum`
- Equivalent Pydantic forms: `Interval`, `conint`/`constr`, `Len`, and
  `StringConstraints` (supported attributes only)
- Fail-fast handling for unsupported metadata (`pattern`, validators,
  decimal precision) and unsupported types (containers, UUID, time,
  timedelta)
- Field alias resolution when binding SQLAlchemy columns (`alias`,
  `validation_alias`, and `serialization_alias` string forms)
- Unsupported-constraint policies: `raise` (default), `warn`, and `ignore`
  for unknown **operators** (unsupported types always raise)
- Exception hierarchy rooted at `SQLRulesError`
- Column resolution for SQLAlchemy `Table` objects, ORM attributes, and
  explicit `column_map`
- Documentation for the compiler, translators, errors, types, and roadmap

### Fixed

- Column resolution no longer treats non-column `Table` attributes (such as
  `name` or `is_selectable`) as columns, which previously produced invalid
  SQL or Python `bool` values in the rules dict
- `Annotated[T, ...] | None` / `Optional[Annotated[T, ...]]` now unwraps
  nested metadata correctly
- String `validation_alias` / `serialization_alias` participate in column
  binding
- `multiple_of` values `<= 0` are rejected
- Length constraints on non-`str` fields and numeric constraints on `str` /
  `bool` fields are rejected

### Changed

- Alias candidates are preferred over the Python field name when binding
  columns
- Unconstrained fields are skipped and no longer require a matching column
- Packaging URLs point at `eddiethedean/sqlrules`
- Docs clarify that `on_unsupported` does not soften unsupported types;
  plugin / two-phase compile designs are marked as future
