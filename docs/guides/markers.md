# Use dialect markers

Markers in sqlrules.markers attach a database-specific operator to a
RuleSchema field. The selected backend must support both the marker and the
bound SQL column type.

## Select a plugin

~~~bash
pip install "sqlrules>=2,<3" "sqlrules-postgresql>=2,<3"
~~~

~~~python
from typing import Annotated, Any

from sqlalchemy import Column, MetaData, Table
from sqlalchemy.dialects.postgresql import JSONB

from sqlrules import Compiler, JsonContains, RuleSchema, where
from sqlrules_postgresql import PostgresPlugin

rows = Table("rows", MetaData(), Column("meta", JSONB))


class RowRules(RuleSchema):
    meta: Annotated[dict[str, Any], JsonContains({"active": True})]


compiler = Compiler(plugins=[PostgresPlugin(server_version=(16, 0))])
compiled = compiler.compile(RowRules, rows)
statement = rows.select().where(*where(compiled))
~~~

## Common markers

| Marker | Typical plugin support |
|---|---|
| JsonContains / JsonHasKey | PostgreSQL, SQLite, MySQL, SQL Server JSON helpers |
| ArrayContains / ArrayOverlap | PostgreSQL |
| RangeContains / RangeOverlap | PostgreSQL |
| FullTextMatch | MySQL |

List and dict fields require a compatible marker. Markers express database
operators; they do not validate nested Python items or JSON schemas.

## Patterns and markers

~~~python
from typing import Annotated, Any
from pydantic import Field
from sqlrules import JsonContains, RuleSchema


class RowRules(RuleSchema):
    name: Annotated[str, Field(pattern="^A")]
    meta: Annotated[dict[str, Any], JsonContains({"active": True})]
~~~

The selected provider must register both pattern and JSON operations.
PostgreSQL does; SQL Server does not register pattern.

SQLite emits REGEXP for pattern and selected text coercions. String length
constraints use a registered Python-compatible code-point counter. Register
`sqlrules_sqlite.register_sqlite_functions()` on each SQLite connection when
those expressions are used. The older `register_regexp()` helper remains an
alias.

Prefer static marker payloads and pattern values. See [SECURITY](../SECURITY.md).
