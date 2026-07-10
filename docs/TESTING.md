# Testing Strategy

## Unit tests

- One test module per constraint family (numeric, string, literal/enum)
- 0.2 features: two-phase compile, cache, diagnostics, UUID/time, pattern IR
- 0.3 features: plugins, registry conflicts, diagnostic codes, conformance
- Error-path coverage for missing columns, invalid models, and policies
- Helper coverage for `where` / `flatten`

## Plugin packages

```bash
pytest tests packages/sqlrules-postgresql/tests packages/sqlrules-sqlite/tests
```

Use `sqlrules.conformance.run_basic_conformance(plugin)` in package tests.

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
  coverage fail-under 95%
- **Package**: build/twine-check core and dialect plugins; import wheel

Benchmarks are local-only and are not a CI gate.

## Principles

- Prefer expression-shape assertions over rendered SQL when possible
- Keep tests free of database connections
- Every new translator needs success and failure cases
- Plugins must preserve built-in operators unless explicitly replacing
