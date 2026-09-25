# Support and compatibility

## Support posture

Community support is best-effort through
[GitHub Issues](https://github.com/eddiethedean/sqlrules/issues). Check the
[FAQ](../guides/faq.md) and [Troubleshooting](../guides/troubleshooting.md)
before opening an issue.

## Compatibility and pinning

| Surface | Stability |
|---|---|
| Application API (`RuleSchema`, `Compiler`, `where`, `notwhere`, conversion) | Semver — 2.x contract |
| Plugin API (`PLUGIN_API_VERSION`, provider hooks, IR, registry) | Exact `api_version` match |
| Internal modules | Unstable — may change without notice |

Install core and a matching official provider from the same major line:

```bash
pip install "sqlrules>=2,<3" "sqlrules-postgresql>=2,<3"
```

The four official providers are released in lockstep with core. See [API
tiers](../API.md) and [Security](../SECURITY.md).

## Supported versions

| Version line | Status |
|---|---|
| 2.x | Current implementation and release target |
| 1.x | Previous stable line; use the 1.x to 2.x migration guide |
| 0.x | Historical |

The semantic profile uses Pydantic 2.13.4 as its conformance reference while
the runtime dependency accepts Pydantic v2. SQLAlchemy 2.x and Python 3.10+
are supported.

## Security reports

Use a [GitHub security advisory](https://github.com/eddiethedean/sqlrules/security/advisories/new)
for vulnerabilities. Do not file public issues for undisclosed problems. See
[SECURITY](../SECURITY.md) for the trust model.

## Code of conduct

Participation follows the project's
[Code of Conduct](https://github.com/eddiethedean/sqlrules/blob/main/CODE_OF_CONDUCT.md).
