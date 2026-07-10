# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-07-10

### Added

- Public API: `compile()`, `where()`, `flatten()`, and `Compiler`
- Constraint support: `gt`, `ge`, `lt`, `le`, `multiple_of`, `min_length`,
  `max_length`, `Literal`, and `Enum`
- Unsupported-constraint policies: `raise` (default), `warn`, and `ignore`
- Exception hierarchy rooted at `SQLRulesError`
- Column resolution for SQLAlchemy `Table` objects, ORM attributes, and
  explicit `column_map`
- Documentation for the compiler, translators, errors, types, and roadmap
