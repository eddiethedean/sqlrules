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
make install
pre-commit install
```

`make install` editable-installs core (`dev` + `docs` extras) and the four
dialect packages under `packages/`.

## Day-to-day checks

```bash
make test      # ruff, mypy, version sync, pytest
make docs      # sphinx-build -W
```

For a full packaging smoke (builds + twine):

```bash
make dist
```

## Pull requests

- Keep changes focused.
- Add or update tests for every constraint or error path you touch.
- Match existing code style and documentation tone.
- Look for issues labeled `good first issue` if you want a starter task.

## Plugins

- Declare `name`, `api_version` (`PLUGIN_API_VERSION`), and `register(registry)`.
- Prefer `register_constraint(..., on_conflict=...)`.
- Use `pattern_text()` for `pattern` values (`PatternSpec` is part of API v1).
- Run `sqlrules.conformance.run_basic_conformance(plugin)` for API shape;
  add golden SQL asserts for dialect correctness.
- Official dialect packages live under `packages/`. They pin
  `sqlrules>=1,<2` and must share the same release tag version as core.

## Maintainers

Release process (Trusted Publishing, tags, lockstep bumps): see
[RELEASING.md](https://github.com/eddiethedean/sqlrules/blob/main/RELEASING.md).
