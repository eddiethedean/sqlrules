# SQLRules 2.0 Dialect Support

SQLRules requires the caller to select one backend provider. A dialect name
alone never changes compilation behavior, and the compiler does not inspect a
live connection.

## Official providers

| Package | Provider | Backend-specific rules |
|---|---|---|
| sqlrules-postgresql | PostgresPlugin | Regex, JSONB, ARRAY, range, and safe text parsing on PostgreSQL 16+ |
| sqlrules-sqlite | SQLitePlugin | Runtime storage-class checks, REGEXP, JSON helpers |
| sqlrules-mysql | MysqlPlugin | REGEXP, JSON, full-text, and safe integer text conversion on MySQL 8.0+ |
| sqlrules-mssql | MssqlPlugin | JSON at SQL Server 2016+ / compatibility level 130+, SQL Server LEN behavior, and TRY_CAST conversions on SQL Server 2012+ |

Select exactly one backend provider, optionally with constraint plugins:

~~~python
from sqlrules import Compiler
from sqlrules_postgresql import PostgresPlugin

compiler = Compiler(plugins=[PostgresPlugin(server_version=(16, 0))])
compiled = compiler.compile(UserRules, users)
~~~

Each provider separates source preparation from constraint translation. It
reports capabilities and produces a PreparedValue containing the original
source, normalized SQL expression, null state, validity predicate, and
coercion description. Constraint translators operate on the prepared
expression. The compiler combines the complete field rules under one total
root predicate.

## Capability rules

- A known row mismatch becomes a non-match.
- A source representation the provider cannot safely inspect or convert raises
  CapabilityError during compilation.
- Retained rules are never skipped by warn or ignore policies.
- The provider does not emit casts that can throw for malformed row data.
- Server versions, database compatibility levels, and storage assumptions are
  visible in capabilities() and CompiledRules.explain().

See [TYPE_SUPPORT](TYPE_SUPPORT.md) for the type, conversion, collation, null,
and version matrix.

## Markers

Dialect markers are declared with sqlrules.markers. The official plugins keep
the stable operators json_contains, json_has_key, array_contains,
array_overlap, range_contains, range_overlap, and fulltext_match where the
backend has an applicable type.

Container item validation and nested JSON schemas are not part of 2.0.
RuleSchema accepts list/dict annotations only for supported marker-driven
fields. A backend still requires an actual JSON, array, or range source type.

## Plugin API v2

Custom constraint plugins implement SQLRulesPlugin with name, api_version,
and register(registry). Backend providers also implement prepare_value() and
capabilities(). The exact version string is exported as PLUGIN_API_VERSION.
Plugins written for API v1 must be adapted because they do not expose source
preparation or backend capabilities.

See [PLUGIN_SYSTEM](PLUGIN_SYSTEM.md) for the registry and translator contract.
