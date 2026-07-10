# Support and compatibility

## License

SQLRules is released under the [MIT License](https://github.com/eddiethedean/sqlrules/blob/main/LICENSE).

## Support posture

Community support is **best-effort** via
[GitHub Issues](https://github.com/eddiethedean/sqlrules/issues). There is no
commercial SLA, paid support contract, or guaranteed response time.

Before opening an issue, check the [FAQ](../guides/faq.md) and
[Troubleshooting](../guides/troubleshooting.md).

## Compatibility and pinning

| Surface | Stability |
|---|---|
| Application API (`compile`, `where`, `Compiler`, …) | Semver — stable in 1.x |
| Plugin API (`PLUGIN_API_VERSION`, IR, registry) | Semver + exact `api_version` match |
| Internal modules | Unstable — may change without notice |

Recommended pins for applications:

```bash
pip install "sqlrules>=1,<2"
pip install "sqlrules-postgresql>=1,<2"   # if needed
```

Official dialect plugins are released in **lockstep** with core on the same
major line. See [API tiers](../API.md) and [Security](../SECURITY.md).

## Security reports

Please open a
[GitHub security advisory](https://github.com/eddiethedean/sqlrules/security/advisories/new)
for vulnerabilities. Do not file public issues for undisclosed security
problems. See [SECURITY](../SECURITY.md) for the trust model (no DB I/O;
plugins are arbitrary code; pattern/ReDoS cost).

## Supported versions

| Version line | Status |
|---|---|
| 1.x | Current stable |
| 0.x | Historical — upgrade to 1.x |

Security fixes target the current 1.x line. Older 0.x releases are not
actively maintained.

## Code of conduct

Participation is governed by the
[Code of Conduct](https://github.com/eddiethedean/sqlrules/blob/main/CODE_OF_CONDUCT.md).
