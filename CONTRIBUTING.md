# Contributing

Thanks for helping improve SQLRules.

**Requires** Python 3.10+.

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

`pre-commit` runs **Ruff** only (format/lint). It does **not** replace CI —
still run the checks below before opening a PR.

## Day-to-day checks (match CI)

```bash
make check   # ruff, mypy, version sync, pytest, sphinx -W
make dist    # build + twine check core and dialect plugins (CI package job)
```

Equivalents:

```bash
make test      # lint + types + version sync + pytest (no docs)
make docs      # sphinx-build -W
```

**Coverage:** core `sqlrules` is gated at ≥95% (`--cov-fail-under=95`).
Dialect packages are tested but not included in that fail-under.

## Pull requests

- Keep changes focused.
- Add or update tests for every constraint or error path you touch.
- Update docs (and CHANGELOG under `[Unreleased]` for user-visible changes).
- Run `make check` and `make dist` so local gates match CI
  (lint / test / docs / package).
- Issue templates label `bug` / `enhancement` / `question`; starter tasks may
  also use `good first issue` when maintainers apply that label.

## Plugins

- Declare `name`, `api_version` (`PLUGIN_API_VERSION`), and `register(registry)`.
- Prefer `register_constraint(..., on_conflict=...)`.
- Use `pattern_text()` for `pattern` values (`PatternSpec` is part of API v1).
- Use `type_spec()` / `TypeSpec` when implementing `type_check` translators.
- Run `sqlrules.conformance.run_basic_conformance(plugin)` for API shape;
  add golden SQL asserts for dialect correctness.
- Official dialect packages live under `packages/`. They pin
  `sqlrules>=1,<2` and must share the same release tag version as core.
- Develop from the monorepo with `make install`; see each package README for
  operators, and [PLUGIN_SYSTEM](https://sqlrules.readthedocs.io/en/latest/PLUGIN_SYSTEM.html)
  for the full contract.

## Maintainers

Release process (CHANGELOG cut, Trusted Publishing, tags, lockstep bumps):
see [RELEASING.md](https://github.com/eddiethedean/sqlrules/blob/main/RELEASING.md).
