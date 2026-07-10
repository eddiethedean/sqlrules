# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0/).

## [Unreleased]

### Added

- `examples/` runnable scripts; Makefile (`install` / `test` / `docs` / `dist`)
- Root `SECURITY.md`, `CODE_OF_CONDUCT.md`, `RELEASING.md`; GitHub issue templates
- Docs: Application vs Plugin autodoc pages; pattern footgun in getting started

### Changed

- README copy-paste complete snippets, repo map, `pattern` callout, prefer `where`
- CONTRIBUTING focused on contributors; release steps moved to RELEASING.md
- Docs sidebar nests design/architecture under “Internals and design”

### Added

- Application API `clear_model_cache()` for the process-wide Phase-1 IR cache
- `docs/IR_CONTRACT.md` — frozen Plugin API v1 IR appendix
- `scripts/check_versions.py` — core/plugin lockstep + extras pin checks
- All-or-nothing PyPI publish via Trusted Publishing (OIDC)
- Plugin wheel install + conformance smoke in CI; mypy on dialect packages

### Changed

- **Stable 1.0** release: Application + Plugin APIs frozen; classifiers
  `Production/Stable`
- Core and dialect packages versioned `1.0.0` in lockstep; pins
  `sqlrules>=1,<2` / extras `sqlrules-*>=1,<2`
- Builtin translator registry built once per process; module `compile()`
  reuses shared default `Compiler` instances
- `max_digits` / `decimal_places` and unknown Field metadata keys rejected at
  extract (no invented operators)
- Elevated pattern/ReDoS guidance in SECURITY and dialect READMEs
- Core sdist no longer bundles `/packages`
- `annotated-types` upper-bounded (`>=0.6,<1`)

### Docs

- Whole-model type matrix documented as intentional 1.0 contract
- Registry mutation after `Compiler` init documented as unsupported
- Prefer `register_constraint` in Plugin docs

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

[1.0.0]: https://github.com/eddiethedean/sqlrules/releases/tag/v1.0.0
[0.4.0]: https://github.com/eddiethedean/sqlrules/releases/tag/v0.4.0
[0.3.0]: https://github.com/eddiethedean/sqlrules/releases/tag/v0.3.0
[0.2.0]: https://github.com/eddiethedean/sqlrules/releases/tag/v0.2.0
[0.1.0]: https://github.com/eddiethedean/sqlrules/releases/tag/v0.1.0
