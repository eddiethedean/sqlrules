# SQLRules Plugin System

Plugin API v2 separates backend source preparation from constraint
translation. The application chooses one backend explicitly; SQLRules does
not inspect connections or discover packages automatically.

## Plugin types

A constraint plugin implements name, api_version, and register(registry). A
backend provider implements those methods plus prepare_value() and
capabilities(). One provider is required when a schema is bound to a table.
Additional constraint plugins may be registered with that provider.

The exact API version is available as PLUGIN_API_VERSION:

~~~python
from sqlrules import PLUGIN_API_VERSION, TranslatorRegistry, pattern_text


class PatternPlugin:
    name = "my-patterns"
    api_version = PLUGIN_API_VERSION

    def register(self, registry: TranslatorRegistry) -> None:
        registry.register_constraint(
            "pattern",
            lambda constraint, value, context: value.op("~")(pattern_text(constraint.value)[0]),
            on_conflict="replace",
        )
~~~

The translator's second argument is the backend-prepared SQL expression, not
the raw bound column. It must return one SQLAlchemy boolean expression.
Unsupported retained rules are errors; translators must not silently omit
them.

## Backend provider contract

A backend provider exposes:

- name: stable backend identifier.
- api_version: exact match with sqlrules.PLUGIN_API_VERSION.
- server_version: configured server version, or None when the feature does not
  require one.
- capabilities(): immutable-looking metadata describing supported source
  types, versions, and assumptions.
- prepare_value(column, field, context): return a PreparedValue with source,
  normalized value, total validity, null state, logical type, coercion, and
  capability information.
- register(registry): install backend-specific constraint translators.

Preparation must make conversions safe for every stored value. A database row
that fails a known type or constraint rule evaluates to false. If the provider
cannot prove the requested conversion or source type, it raises
CapabilityError before returning SQL.

## Register a backend and compile

~~~python
from sqlrules import Compiler, where
from sqlrules_postgresql import PostgresPlugin

compiler = Compiler(plugins=[PostgresPlugin(server_version=(16, 0))])
compiled = compiler.compile(UserRules, users)
statement = users.select().where(*where(compiled))
~~~

Pass exactly one backend provider. Passing multiple providers is an error.
The optional dialect argument is only an assertion against the selected
provider name; it never selects a backend.

## Registry

The registry starts with SQLRules portable comparison, length, and domain
translators. Plugins may add or replace translators with:

~~~python
registry.register_constraint(
    operator="pattern",
    translator=translate_pattern,
    on_conflict="replace",
)
~~~

Conflict policies are raise, replace, and ignore. Compiler(on_conflict=...)
provides the default policy for plugins that do not pass an explicit
on_conflict value. The compiler freezes a private registry snapshot; reading
compiler.registry returns a copy.

## Official packages

- sqlrules-postgresql: regex, JSONB, arrays, ranges, PostgreSQL 16+ safe text
  parsing.
- sqlrules-sqlite: runtime type checks, REGEXP, Python-compatible string
  length, and JSON helpers.
- sqlrules-mysql: regex, JSON, full-text, and MySQL 8.0+ integer text parsing.
- sqlrules-mssql: JSON on SQL Server 2016+ with database compatibility level
  130+, LEN string behavior, and SQL Server 2012+ TRY_CAST.

All official packages must share a version line with the core package. The
[dialect support matrix](DIALECT_SUPPORT.md) lists capabilities and limits.

## Version compatibility

Plugin api_version must exactly match PLUGIN_API_VERSION, currently 2. API v1
plugins must be adapted: the API v2 backend provider prepares values and
reports capabilities before translators run. A core package minor release
does not change the plugin API.

## Security

Plugins execute Python code and SQLAlchemy expression constructors. SQLRules
does not sandbox plugins. Install only trusted packages and use static regular
expressions where possible.
