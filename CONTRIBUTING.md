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
pre-commit install
```

## Checks

```bash
ruff check .
ruff format --check .
mypy src/sqlrules
pytest
python -m build && twine check dist/*
```

CI also verifies `pyproject.toml` / `__version__` sync and that the built
wheel imports cleanly.

## Pull requests

- Keep changes focused.
- Add or update tests for every constraint or error path you touch.
- Match existing code style and documentation tone.

## Releasing

Releases are published to PyPI by pushing a version tag. Before tagging:

1. Confirm `pyproject.toml` and `sqlrules.__version__` match the changelog.
2. Run the full check suite (`ruff`, `mypy`, `pytest`).
3. Ensure CI is green on `main`.

Then create and push the tag (example for 0.2.0):

```bash
git tag -a v0.2.0 -m "sqlrules 0.2.0"
git push origin v0.2.0
```

The [release workflow](.github/workflows/release.yml) runs CI, builds the
sdist/wheel, and publishes with `PYPI_API_TOKEN`.
