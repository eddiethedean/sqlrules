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
pip install -e ".[docs]"   # optional: Sphinx / Read the Docs local builds
pip install -e packages/sqlrules-postgresql -e packages/sqlrules-sqlite \
  -e packages/sqlrules-mysql -e packages/sqlrules-mssql
pre-commit install
```

## Checks

```bash
ruff check .
ruff format --check .
mypy src/sqlrules
mypy --disable-error-code=redundant-cast \
  packages/sqlrules-postgresql/src packages/sqlrules-sqlite/src \
  packages/sqlrules-mysql/src packages/sqlrules-mssql/src
python scripts/check_versions.py
pytest tests packages/sqlrules-postgresql/tests packages/sqlrules-sqlite/tests \
  packages/sqlrules-mysql/tests packages/sqlrules-mssql/tests
sphinx-build -W -b html docs docs/_build/html
python -m build && twine check dist/*
python -m build packages/sqlrules-postgresql --outdir dist-plugins
python -m build packages/sqlrules-sqlite --outdir dist-plugins
python -m build packages/sqlrules-mysql --outdir dist-plugins
python -m build packages/sqlrules-mssql --outdir dist-plugins
twine check dist-plugins/*
```

CI enforces core ↔ plugin version lockstep, extras pins, plugin `LICENSE` /
`py.typed`, mypy on plugins, and wheel import + conformance smoke tests.

## Plugins

- Declare `name`, `api_version` (`PLUGIN_API_VERSION`), and `register(registry)`.
- Prefer `register_constraint(..., on_conflict=...)`.
- Use `pattern_text()` for `pattern` values (`PatternSpec` is part of API v1).
- Run `sqlrules.conformance.run_basic_conformance(plugin)` for API shape;
  add golden SQL asserts for dialect correctness.
- Official dialect packages live under `packages/`. They pin
  `sqlrules>=1,<2` and must share the same release tag version as core.

## Pull requests

- Keep changes focused.
- Add or update tests for every constraint or error path you touch.
- Match existing code style and documentation tone.

## Releasing (1.0+)

1. Bump **all five** packages together (`pyproject.toml` + `__version__`).
2. Keep pins on the major line: plugins `sqlrules>=1,<2`; core extras
   `sqlrules-*>=1,<2`.
3. Run `python scripts/check_versions.py` and the full check list above.
4. Configure **PyPI Trusted Publishing** (OIDC) for `sqlrules` and each
   `sqlrules-*` project: publisher = GitHub, repository =
   `eddiethedean/sqlrules`, workflow = `release.yml`, environment empty
   unless you add one. Do **not** rely on a long-lived `PYPI_API_TOKEN`.
5. Tag and push:

```bash
git tag -a v1.0.1 -m "sqlrules 1.0.1"
git push origin v1.0.1
```

The [release workflow](https://github.com/eddiethedean/sqlrules/blob/main/.github/workflows/release.yml)
runs CI, builds **core + all plugins**, then uploads every artifact in one
all-or-nothing publish step (Trusted Publishing).
