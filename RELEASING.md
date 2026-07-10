# Releasing SQLRules

Maintainer checklist for publishing core + dialect plugins in lockstep.

## Preflight

1. **Cut the changelog.** Move shipped items from `## [Unreleased]` into a
   dated `## [1.x.y] - YYYY-MM-DD` section. Leave Unreleased empty (or with
   only truly unreleased work). Ensure the footer link `[1.x.y]: ...` exists.
2. **Bump all five packages** together (`pyproject.toml` + `__version__` in
   core and each `packages/sqlrules-*`).
3. **Keep pins on the major line:** plugins `sqlrules>=1,<2`; core extras
   `sqlrules-*>=1,<2`.
4. Run version sync locally:

```bash
python scripts/check_versions.py
```

5. Run the full local gate (matches CI lint/test/docs + packaging):

```bash
make check
make dist
```

6. Confirm **PyPI credentials** for publishing:
   - **API token** (current path): repository secret `PYPI_API_TOKEN` with
     upload rights (can create new dialect projects on first upload), **or**
   - **Trusted Publishing** (OIDC): configure a publisher on each of
     `sqlrules`, `sqlrules-postgresql`, `sqlrules-sqlite`, `sqlrules-mysql`,
     `sqlrules-mssql` for workflow `release.yml`, then remove the
     `password:` input from the publish step so OIDC is used.

## Tag and publish

```bash
git tag -a v1.0.0 -m "sqlrules 1.0.0"
git push origin v1.0.0
```

The [release workflow](.github/workflows/release.yml) runs CI, builds
**core + all plugins**, then uploads every artifact from `dist/` and
`dist-plugins/` in one publish step.

## Post-publish verification

1. Confirm five PyPI project pages show the new version:
   - https://pypi.org/project/sqlrules/
   - https://pypi.org/project/sqlrules-postgresql/
   - https://pypi.org/project/sqlrules-sqlite/
   - https://pypi.org/project/sqlrules-mysql/
   - https://pypi.org/project/sqlrules-mssql/
2. Smoke-install in a clean venv:

```bash
pip install "sqlrules==1.0.0" "sqlrules-postgresql==1.0.0"
python -c "import sqlrules; from sqlrules_postgresql import PostgresPlugin; print(sqlrules.__version__)"
```

3. Create a GitHub Release for the tag (notes can summarize the CHANGELOG
   section).

## Failure / recovery

- If Trusted Publishing is missing for one project, that upload fails while
  others may succeed — fix the publisher config and re-run / upload the
  missing artifacts carefully (avoid yanking unless necessary).
- Do **not** retag the same version with different wheels. Bump to a new
  patch if a bad build was published.
- Dry-run builds anytime with `make dist` (no upload). TestPyPI is optional
  and not wired into the default workflow.
