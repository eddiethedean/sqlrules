# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0/).

## [Unreleased]

### Added

- Documented Application / Plugin / Internal API tiers in `docs/API.md`
- Re-exported Plugin API symbols: `pattern_text`, `TranslatorRegistry`,
  `default_registry`
- `docs/SECURITY.md` (plugin trust model, ReDoS notes)
- Core optional extras: `postgresql`, `sqlite`, `mysql`, `mssql`, `dialects`
- Plugin packages: `LICENSE`, `py.typed`, richer metadata; release workflow
  publishes plugins on the same version tag as core
- CI checks plugin version sync and packaging files

### Changed

- `Compiler` always copies the base registry (caller-owned registries are
  never mutated, with or without plugins)
- `ModelIRCache` uses a strong `dict` (documented process-lifetime cache;
  call `clear()` for ephemeral models) — `WeakKeyDictionary` could not
  evict because `ModelIR` retains the model class
- `dialect=` documented as a translator hint only (does not load plugins)
- Core dependencies upper-bounded: `pydantic>=2,<3`, `sqlalchemy>=2,<3`
- Roadmap / milestones: 1.0 is API freeze; former 0.5–0.8 moved post-1.0
- Performance docs no longer claim CI regression gates

## [0.4.0] - 2026-07-10

### Added

- `ConstraintMarker` protocol and shared markers in `sqlrules.markers`:
  `JsonContains`, `JsonHasKey`, `ArrayContains`, `ArrayOverlap`,
  `RangeContains`, `RangeOverlap`, `FullTextMatch`
- `PatternSpec` IR value for `pattern` (preserves `ignore_case` from
  `re.Pattern` flags); `pattern_text()` helper for plugins
- `list` / `dict` annotations for marker-driven fields (portable
  constraints on containers still raise)
- Expanded dialect plugins:
  - `sqlrules-postgresql` — `~` / `~*`, JSONB, ARRAY, range operators
  - `sqlrules-sqlite` — `register_regexp()`, flag-aware REGEXP, JSON helpers
  - `sqlrules-mysql` — REGEXP, JSON, `fulltext_match`
  - `sqlrules-mssql` — JSON helpers, `LEN` overrides for length constraints
- Conformance helpers accept optional `model` / `table` / `field` for
  non-`pattern` operators

### Changed

- Package version bumped to 0.4.0
- Official plugin packages depend on `sqlrules>=0.4,<0.5`

## [0.3.0] - 2026-07-10

### Added

- Versioned plugin API: `SQLRulesPlugin`, `PLUGIN_API_VERSION` (`"1"`),
  and `PluginError`
- `Compiler(plugins=..., on_conflict=..., dialect=...)` for explicit
  plugin registration (no auto-discovery)
- Expanded registry API: `register_constraint`, conflict policies
  (`raise` / `replace` / `ignore`), `copy()`, `operators()`, and
  `__contains__`
- `InvalidTranslatorError` raised for non-callable or wrong-arity
  translators at registration time
- `Diagnostic.code` (e.g. `unsupported_constraint` on warn/ignore skips)
- Optional `CompilationContext.dialect` hint (never auto-detected)
- Plugin conformance helpers in `sqlrules.conformance`
- Official starter dialect packages:
  - `sqlrules-postgresql` (`pattern` → `~`)
  - `sqlrules-sqlite` (`pattern` → `REGEXP`)

### Changed

- Package version bumped to 0.3.0

## [0.2.0] - 2026-07-10

### Added

- Two-phase compilation: `Compiler.compile_model()` (static IR) and
  `Compiler.bind()` (column resolve + translate)
- In-process metadata cache for Phase-1 `ModelIR` (default on; disable with
  `cache=False`)
- Structured diagnostics: public `Diagnostic` via `compiler.diagnostics` for
  skipped constraints under `on_unsupported="warn"` / `"ignore"`
- Type support for `UUID` and `time` (range comparisons for `time`;
  Literal/Enum for `UUID`)
- First-class `pattern` constraint IR (no portable core translator; register
  a custom translator or use a future dialect plugin)
- IR types: `ModelIR`, `FieldIR`, `Diagnostic`
- Local benchmark suite: `python -m benchmarks.bench_compile`

### Changed

- Unsupported-constraint error messages no longer hard-code a release version
- `CompilationContext` carries an optional diagnostics collector
- Unconstrained `UUID` / `time` fields are skipped (no longer type-rejected);
  `timedelta` and containers still always raise
- Validation-only metadata flags (`strip_whitespace`, `allow_inf_nan`, …) are
  ignored when extracting constraints
- `pattern` values from `re.Pattern` are normalized to strings in IR
- Invalid `column_map` entries raise instead of falling through to table columns

### Fixed

- Reject `multiple_of` on `date` / `datetime` / `time` (previously emitted
  nonsensical modulo SQL)
- Module-level `sqlrules.compile(..., on_unsupported="warn")` now attributes
  warnings to the caller, not `compiler.py`
- `compile_model` clears stale diagnostics from prior binds

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

[0.4.0]: https://github.com/eddiethedean/sqlrules/releases/tag/v0.4.0
[0.3.0]: https://github.com/eddiethedean/sqlrules/releases/tag/v0.3.0
[0.2.0]: https://github.com/eddiethedean/sqlrules/releases/tag/v0.2.0
[0.1.0]: https://github.com/eddiethedean/sqlrules/releases/tag/v0.1.0
