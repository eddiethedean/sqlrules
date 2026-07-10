# Contributing

Thanks for helping improve SQLRules.

## Principles

- Keep the public API minimal.
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

CI also verifies `pyproject.toml` / `__version__` sync and that the built
wheel imports cleanly.

## Plugins

- Declare `name`, `api_version` (`PLUGIN_API_VERSION`), and `register(registry)`.
- Prefer `register_constraint(..., on_conflict=...)`.
- Run `sqlrules.conformance.run_basic_conformance(plugin)`.
- Official dialect packages live under `packages/` and should track the
  core minor (`sqlrules>=0.4,<0.5` while `PLUGIN_API_VERSION == "1"`).

## Pull requests

- Keep changes focused.
- Add or update tests for every constraint or error path you touch.
- Match existing code style and documentation tone.

## Releasing

Releases are published to PyPI by pushing a version tag. Before tagging:

1. Confirm `pyproject.toml` and `sqlrules.__version__` match the changelog.
2. Run the full check suite (`ruff`, `mypy`, `pytest`).
3. Ensure CI is green on `main`.

Then create and push the tag (example for 0.4.0):

```bash
git tag -a v0.4.0 -m "sqlrules 0.4.0"
git push origin v0.4.0
```

The [release workflow](.github/workflows/release.yml) runs CI, verifies the
tag matches `pyproject.toml` / `__version__`, builds the sdist/wheel, and
publishes **core** `sqlrules` with `PYPI_API_TOKEN`.

Dialect plugin packages under `packages/` are versioned independently and
are **not** published by the core release workflow. Publish them separately
after core `0.4.0` is on PyPI (they depend on `sqlrules>=0.4,<0.5`):

```bash
python -m build packages/sqlrules-postgresql --outdir dist-plugins
python -m build packages/sqlrules-sqlite --outdir dist-plugins
python -m build packages/sqlrules-mysql --outdir dist-plugins
python -m build packages/sqlrules-mssql --outdir dist-plugins
twine upload dist-plugins/*
```
