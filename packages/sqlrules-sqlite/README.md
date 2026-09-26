# sqlrules-sqlite

SQLite backend provider for [SQLRules](https://github.com/eddiethedean/sqlrules).
This official provider first shipped with [SQLRules 2.0.0](https://github.com/eddiethedean/sqlrules/releases/tag/v2.0.0)
on 2026-09-26. Official dialect packages share core's release version.

## Install

```bash
pip install "sqlrules>=2,<3" "sqlrules-sqlite>=2,<3"
```

## Use

```python
from typing import Annotated, Any

from pydantic import Field
from sqlalchemy import Column, JSON, MetaData, String, Table, create_engine, event

from sqlrules import Compiler, JsonContains, RuleSchema, where
from sqlrules_sqlite import SQLitePlugin, register_sqlite_functions

rows = Table("rows", MetaData(), Column("name", String), Column("meta", JSON))


class RowRules(RuleSchema):
    name: Annotated[str, Field(pattern=r"^A")]
    meta: Annotated[dict[str, Any], JsonContains({"active": True})]


engine = create_engine("sqlite:///app.db")
event.listen(
    engine,
    "connect",
    lambda dbapi_connection, _: register_sqlite_functions(dbapi_connection),
)
compiled = Compiler(plugins=[SQLitePlugin()]).compile(RowRules, rows)
statement = rows.select().where(*where(compiled))
```

## Capabilities

- Runtime `typeof()` checks for SQLite integer, real, and text storage classes
- Lax text-to-int/float coercion and bool values stored as integer 0 or 1
- JSON1 helpers that treat malformed documents as non-matches
- `REGEXP` pattern matching and Unicode-aware string length through
  `register_sqlite_functions()`

Strict bool, exact Decimal, and SQLAlchemy-emulated date/time/UUID values need
explicit storage adapters and raise `CapabilityError`. Text coercion, patterns,
and string length constraints require the registered SQLRules SQLite functions
on each connection. `register_regexp()` remains as a backward-compatible alias.
See the
[type support matrix](https://sqlrules.readthedocs.io/en/latest/TYPE_SUPPORT.html).

## Pattern cost

`register_sqlite_functions()` runs Python's `re.search` for each regex row and
Python's `len()` for each length-checked string row. Untrusted patterns can
cause CPU denial of service through catastrophic backtracking. Prefer static
or allowlisted patterns. See the SQLRules
[security notes](https://sqlrules.readthedocs.io/en/latest/SECURITY.html).
