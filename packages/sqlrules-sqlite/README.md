# sqlrules-sqlite

SQLite dialect plugin for [SQLRules](https://github.com/eddiethedean/sqlrules).

## Install

```bash
pip install sqlrules-sqlite
```

## Usage

```python
import sqlite3
from typing import Annotated, Any

from pydantic import BaseModel, Field
from sqlalchemy import Column, MetaData, String, Table, create_engine, text

from sqlrules import Compiler, JsonContains, JsonHasKey
from sqlrules_sqlite import SQLitePlugin, register_regexp

class RowFilter(BaseModel):
    name: Annotated[str, Field(pattern=r"^A")]
    meta: Annotated[dict[str, Any], JsonContains({"active": True}), JsonHasKey("active")]

table = Table(
    "rows",
    MetaData(),
    Column("name", String),
    Column("meta", String),
)

compiler = Compiler(plugins=[SQLitePlugin()], dialect="sqlite")
rules = compiler.compile(RowFilter, table)

engine = create_engine("sqlite://")
with engine.raw_connection() as conn:
    # SQLAlchemy 2 may wrap the DBAPI connection; unwrap if needed.
    dbapi = conn.driver_connection if hasattr(conn, "driver_connection") else conn
    register_regexp(dbapi)
```

## Operators

| IR operator | Notes |
|---|---|
| `pattern` | `column REGEXP pattern`; call `register_regexp(connection)` |
| `json_contains` | JSON1 `json_extract` equality for object keys |
| `json_has_key` | `json_type(column, '$.key') IS NOT NULL` |

Case-insensitive patterns (`re.IGNORECASE` / `PatternSpec.ignore_case`) are
encoded with a `(?i)` prefix understood by `register_regexp`.

## Security note

`register_regexp` installs a Python `re.search` UDF. Untrusted
`Field(pattern=...)` values can cause **CPU denial of service** (ReDoS) in
your process — not SQL injection. Prefer static/allowlisted patterns. See
[SECURITY](https://sqlrules.readthedocs.io/en/latest/SECURITY.html).
