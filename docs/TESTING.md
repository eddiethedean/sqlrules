# Testing Strategy

## Unit tests

- One test module per constraint family (numeric, string, literal/enum)
- Two-phase compile, cache, diagnostics, UUID/time, pattern IR
- Plugins, registry conflicts, diagnostic codes, conformance
- Markers / dialect packages under `packages/*/tests`
- Opt-in `emit_type_checks` / `TypeSpec`
- Error-path coverage for missing columns, invalid models, and policies
- Helper coverage for `where` / `flatten`

## Plugin packages

```bash
pytest tests \
  packages/sqlrules-postgresql/tests \
  packages/sqlrules-sqlite/tests \
  packages/sqlrules-mysql/tests \
  packages/sqlrules-mssql/tests
```

Or simply `make test` (also runs lint, mypy, and version sync).

Use `sqlrules.conformance.run_basic_conformance(plugin)` in package tests.

**Coverage:** core package (`sqlrules`) is gated at ≥95% via pytest
`--cov-fail-under=95`. Dialect plugin packages are tested but are **not**
included in that fail-under gate.

## Benchmarks

Local only (not a CI gate):

```bash
python -m benchmarks.bench_compile
```

## Compatibility

- CI matrix covers Python 3.10–3.13 with current Pydantic v2 / SQLAlchemy 2.x
  from package dependencies (no separate Pydantic version matrix)
- SQLAlchemy Core expression construction in unit tests
- Occasional SQLite / PostgreSQL dialect `.compile(...)` smoke assertions

## Quality gates

CI (`.github/workflows/ci.yml`) runs:

- **Lint** (Python 3.12): `ruff check`, `ruff format --check`, `mypy`,
  version sync between `pyproject.toml` and `sqlrules.__version__`
- **Test** matrix (Python 3.10–3.13): core + dialect plugin tests,
  coverage fail-under 95% (core only)
- **Docs**: `sphinx-build -W`
- **Package**: build/twine-check core and dialect plugins; import wheel

Locally, match CI with:

```bash
make check   # lint + types + tests + docs
make dist    # packaging smoke
```

Benchmarks are local-only and are not a CI gate.

## Principles

- Prefer expression-shape assertions over rendered SQL when possible
- Keep tests free of database connections
- Every new translator needs success and failure cases
- Plugins must preserve built-in operators unless explicitly replacing
