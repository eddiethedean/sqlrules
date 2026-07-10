# Security Policy

SQLRules is a pure compiler: it does not connect to databases or execute SQL.
It depends on Pydantic and SQLAlchemy for types and expression objects only.

**Trust summary**

- No database I/O during compile.
- Dialect **plugins are arbitrary Python** — treat them like any dependency.
- `Field(pattern=...)` / REGEXP can be expensive (ReDoS / CPU); prefer static
  patterns. SQLite REGEXP runs Python `re` in-process after
  `register_regexp(connection)`.

Full trust model and guidance:

**[docs/SECURITY.md](https://sqlrules.readthedocs.io/en/latest/SECURITY.html)**
(source: [`docs/SECURITY.md`](docs/SECURITY.md))

## Supported versions

| Version line | Security updates |
|---|---|
| 1.x | Current — yes |
| 0.x | No — upgrade to 1.x |

## Reporting a vulnerability

Please open a
[GitHub security advisory](https://github.com/eddiethedean/sqlrules/security/advisories/new).
Do not file a public issue for undisclosed vulnerabilities.

There is no separate security email or guaranteed SLA; reports are handled
best-effort by maintainers. See
[Support & compatibility](https://sqlrules.readthedocs.io/en/latest/project/support.html).
