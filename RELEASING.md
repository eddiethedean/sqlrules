# Releasing SQLRules

Maintainer checklist for publishing core and all four dialect plugins in
lockstep. The release workflow is tag-driven; pushing a release tag publishes
the five distributions to PyPI.

## Preflight

1. Confirm the release commit is on `main`, its CI run is green, and the
   checkout is clean.
2. Cut the changelog: move shipped entries from `[Unreleased]` into a dated
   version section and leave `[Unreleased]` empty. Add the matching footer link.
3. Set the same version in the core package and all four plugins. Keep each
   plugin dependency pin and core extra on the corresponding major line.
4. Run the version check and local release gates:

   ```bash
   python scripts/check_versions.py
   make check
   make dist
   make examples
   ```

   The project requires Twine 7.0 or newer because current Hatchling builds
   use Core Metadata 2.5.

5. Confirm the repository secret `PYPI_API_TOKEN` is configured with upload
   rights. The release workflow currently publishes with this token. If moving
   to Trusted Publishing, configure it for all five PyPI projects and update
   the publish step to omit its password input before the release.

## Tag and publish

For the prepared 2.0.0 release:

```bash
git switch main
git pull --ff-only
git tag -a v2.0.0 -m "sqlrules 2.0.0"
git push origin v2.0.0
```

The [release workflow](.github/workflows/release.yml) runs CI, verifies the
tag and lockstep versions, builds and checks core plus every plugin, then
publishes the artifacts to PyPI. It skips files already uploaded so a failed
partial upload can be retried by rerunning the workflow for the same tag.

## Post-publish verification

1. Confirm all five PyPI project pages show the new version:
   - https://pypi.org/project/sqlrules/
   - https://pypi.org/project/sqlrules-postgresql/
   - https://pypi.org/project/sqlrules-sqlite/
   - https://pypi.org/project/sqlrules-mysql/
   - https://pypi.org/project/sqlrules-mssql/
2. Smoke-install in a clean environment:

   ```bash
   pip install "sqlrules==2.0.0" "sqlrules-postgresql==2.0.0"
   python -c "import sqlrules; from sqlrules_postgresql import PostgresPlugin; print(sqlrules.__version__)"
   ```

3. Create a GitHub Release for the tag using the 2.0.0 changelog section.

## Failure / recovery

- If publishing fails after some files or packages were uploaded, fix the
  reported cause and rerun the tag's Release workflow. `skip-existing: true`
  makes that retry safe for already published files.
- Do not retag a version with different artifacts. If incorrect artifacts
  were published, follow PyPI's recovery guidance and prepare a new version.
- `make dist` builds and checks the artifacts without uploading them.
