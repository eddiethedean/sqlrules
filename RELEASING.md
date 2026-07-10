# Releasing SQLRules

Maintainer checklist for publishing core + dialect plugins.

1. Bump **all five** packages together (`pyproject.toml` + `__version__`).
2. Keep pins on the major line: plugins `sqlrules>=1,<2`; core extras
   `sqlrules-*>=1,<2`.
3. Run `make check` (or the full list in [CONTRIBUTING.md](CONTRIBUTING.md)).
4. Configure **PyPI Trusted Publishing** (OIDC) for `sqlrules` and each
   `sqlrules-*` project: publisher = GitHub, repository =
   `eddiethedean/sqlrules`, workflow = `release.yml`.
5. Tag and push:

```bash
git tag -a v1.0.1 -m "sqlrules 1.0.1"
git push origin v1.0.1
```

The [release workflow](.github/workflows/release.yml) runs CI, builds
**core + all plugins**, then uploads every artifact in one all-or-nothing
publish step.
