# Troubleshooting

## RuleSchema declaration errors

RuleSchema checks supported types and metadata during class creation. Remove
custom validators, serializers, computed fields, unsupported Pydantic options,
general unions, or unsupported type/constraint combinations. To use a full
Pydantic model that contains those features, convert it with from_pydantic()
and inspect its report.

## CapabilityError

The selected backend cannot prove the bound column's logical type or safely
implement the requested conversion. Check the source SQLAlchemy type,
configured server_version, SQLite storage class, and collation requirements
in [TYPE_SUPPORT](../TYPE_SUPPORT.md). A known row mismatch is a non-match;
an unavailable backend capability is a compile-time error.

## MissingColumnError

Every field, including a type-only field, needs a bound SQLAlchemy column.
Use column_map keyed by the Python field name, Field(column="..."), or a
matching database column.

## Pattern unsupported on SQL Server

Expected: sqlrules-mssql does not register pattern. Select a provider that
supports the pattern semantics or remove the pattern declaration.

## SQLite REGEXP errors

SQLite does not provide REGEXP by default, and its built-in `length(TEXT)`
stops at an embedded NUL. Register `sqlrules_sqlite.register_sqlite_functions()`
on each connection when patterns, textual coercions, or string length
constraints are used. `register_regexp()` remains a backward-compatible alias.

## Plugin registration conflicts

Two translators claim one operator. Set on_conflict="replace" or "ignore" on
Compiler or the individual register_constraint() call. Exactly one backend
provider must be selected.

## Plugin API mismatch

api_version must equal sqlrules.PLUGIN_API_VERSION (currently 2). API v1
plugins need a backend preparation hook and capability report before they can
be used with 2.0.

## Rows match unexpectedly

Inspect compiled.explain() for the bound columns, logical types, coercion
profile, and backend assumptions. Use notwhere(compiled) to query failing
rows. Defaults and values on a Python model instance never become SQL
predicates.

## More help

[FAQ](faq.md) · [Errors](../ERRORS.md) · [Support matrix](../TYPE_SUPPORT.md)
