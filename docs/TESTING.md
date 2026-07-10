# Testing Strategy

## Unit tests

- One test module per constraint family (numeric, string, literal/enum)
- 0.2 features: two-phase compile, cache, diagnostics, UUID/time, pattern IR
- Error-path coverage for missing columns, invalid models, and policies
- Helper coverage for `where` / `flatten`

## Benchmarks

Local only (not a CI gate):

```bash
python -m benchmarks.bench_compile
```

## Compatibility

- CI matrix covers Python 3.10–3.13 with current Pydantic v2 / SQLAlchemy 2.x
  from package dependencies (no separate Pydantic version matrix)
- SQLAlchemy Core expression construction in unit tests
- Occasional SQLite dialect `.compile(...)` smoke assertions in tests

## Quality gates

CI (`.github/workflows/ci.yml`) runs:

- **Lint** (Python 3.12): `ruff check`, `ruff format --check`, `mypy`,
  version sync between `pyproject.toml` and `sqlrules.__version__`
- **Test** matrix (Python 3.10–3.13): `pytest` with coverage fail-under 95%
- **Package**: `python -m build`, `twine check`, install wheel and import

Benchmarks are local-only and are not a CI gate.

## Principles

- Prefer expression-shape assertions over rendered SQL when possible
- Keep tests free of database connections
- Every new translator needs success and failure cases
