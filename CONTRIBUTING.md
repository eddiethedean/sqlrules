# Contributing

Thanks for helping improve SQLRules.

## Principles

- Keep the Application API minimal.
- Every feature must map directly to SQLAlchemy expressions.
- Unsupported Pydantic features should not be approximated.
- Prefer fail-fast behavior over silent semantic changes.
- Update relevant docs before or alongside implementation.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pip install -e packages/sqlrules-postgresql -e packages/sqlrules-sqlite \
  -e packages/sqlrules-mysql -e packages/sqlrules-mssql
pre-commit install
```

## Checks

```bash
ruff check .
ruff format --check .
mypy src/sqlrules
pytest tests packages/sqlrules-postgresql/tests packages/sqlrules-sqlite/tests \
  packages/sqlrules-mysql/tests packages/sqlrules-mssql/tests
python -m build && twine check dist/*
python -m build packages/sqlrules-postgresql --outdir dist-plugins
python -m build packages/sqlrules-sqlite --outdir dist-plugins
python -m build packages/sqlrules-mysql --outdir dist-plugins
python -m build packages/sqlrules-mssql --outdir dist-plugins
twine check dist-plugins/*
```

CI verifies core + plugin `pyproject.toml` / `__version__` sync, plugin
`LICENSE` / `py.typed`, and that built wheels import cleanly.

## Plugins

- Declare `name`, `api_version` (`PLUGIN_API_VERSION`), and `register(registry)`.
- Prefer `register_constraint(..., on_conflict=...)`.
- Use `pattern_text()` for `pattern` values (`PatternSpec` is part of API v1).
- Run `sqlrules.conformance.run_basic_conformance(plugin)` for API shape;
  add golden SQL asserts for dialect correctness.
- Official dialect packages live under `packages/`. While on 0.x they pin
  `sqlrules>=0.4,<0.5`. At 1.0 they must pin `sqlrules>=1,<2` and share the
  same release tag version as core.

## Pull requests

- Keep changes focused.
- Add or update tests for every constraint or error path you touch.
- Match existing code style and documentation tone.

## Releasing

Pushing an annotated version tag publishes **core and all four dialect
plugins** (versions must match the tag):

```bash
# Confirm pyproject / __version__ match across core + packages/*
git tag -a v0.4.1 -m "sqlrules 0.4.1"
git push origin v0.4.1
```

The [release workflow](.github/workflows/release.yml) runs CI, publishes
core, then publishes each plugin whose version equals the tag.

At 1.0, bump core and plugins together and change plugin dependency pins
to `sqlrules>=1,<2`.
