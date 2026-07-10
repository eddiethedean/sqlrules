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

- Cross-version Pydantic v2 tests via CI matrix
- SQLAlchemy Core expression construction
- SQLite dialect compilation smoke tests

## Quality gates

CI runs on Python 3.10–3.13:

- `ruff check`
- `ruff format --check`
- `mypy` (strict)
- `pytest` with coverage fail-under 95%

## Principles

- Prefer expression-shape assertions over rendered SQL when possible
- Keep tests free of database connections
- Every new translator needs success and failure cases
