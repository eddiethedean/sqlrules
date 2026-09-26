# Testing Strategy

## Test layers

- RuleSchema declaration and normal Pydantic validation behavior
- Pydantic conversion policies, reports, aliases, defaults, and callback loss
- Compiler result grouping, explicit backend selection, column binding, and
  capability errors
- SQLite execution with malformed values, strict/lax types, SQL NULL, and the
  `where()` / `notwhere()` partition
- Dialect translation and provider conformance for PostgreSQL, MySQL, and SQL
  Server
- Live database execution conformance for all four official backends in CI
- Version synchronization, docs, package builds, wheel imports, lint, and types

Run the fast suite with:

```bash
pytest tests \
  packages/sqlrules-postgresql/tests \
  packages/sqlrules-sqlite/tests \
  packages/sqlrules-mysql/tests \
  packages/sqlrules-mssql/tests
```

Live conformance tests use the `SQLRULES_TEST_*_URL` environment variables and
are skipped locally when no database URL is configured. CI starts PostgreSQL,
MySQL, and SQL Server services and exercises their text-to-integer and
nullable-complement behavior. SQLite tests execute in memory.

## Pydantic reference

The semantic profile is compared against Pydantic **2.13.4**. The runtime
dependency permits the Pydantic v2 line; CI pins the reference job to this
version so coercion changes are deliberate and reviewable.

## CI gates

CI (`.github/workflows/ci.yml`) runs:

- Ruff lint and formatting, mypy, and version synchronization
- Core and dialect package tests on Python 3.10–3.13 with an 80% combined
  statement and branch coverage floor for the rewritten 2.0 core
- Live backend execution conformance on PostgreSQL, MySQL, and SQL Server
- Sphinx with warnings treated as errors
- Core and dialect wheel builds, Twine checks, and installed-wheel imports

## Principles

- Test behavior through model validation and executed SQL where possible.
- Compile-time SQL assertions supplement database execution tests.
- Every retained rule must either translate or raise a stable capability
  error; warning and ignore policies must not silently omit it.
- Every live fixture proves that `where(compiled)` and `notwhere(compiled)`
  select disjoint sets whose union is the full fixture set.
