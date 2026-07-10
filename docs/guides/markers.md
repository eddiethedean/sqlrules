# Use dialect markers (JSON, arrays, full-text)

Markers in `sqlrules.markers` (also re-exported from `sqlrules`) attach
dialect-specific operators to a field. Core extracts them into IR; a dialect
**plugin** must register translators.

## Install and register a plugin

```bash
pip install "sqlrules-postgresql>=1,<2"
# or from this repo: make install
```

```python
from typing import Annotated, Any

from pydantic import BaseModel
from sqlalchemy import Column, MetaData, Table
from sqlalchemy.dialects.postgresql import JSONB

import sqlrules
from sqlrules import Compiler, JsonContains
from sqlrules_postgresql import PostgresPlugin

rows = Table("rows", MetaData(), Column("meta", JSONB))

class RowFilter(BaseModel):
    meta: Annotated[dict[str, Any], JsonContains({"active": True})]

compiler = Compiler(plugins=[PostgresPlugin()], dialect="postgresql")
rules = compiler.compile(RowFilter, rows)
stmt = rows.select().where(*sqlrules.where(rules))
```

`dialect=` is a **hint** for translators — it does not load plugins.

## Common markers

| Marker | Typical plugin support |
|---|---|
| `JsonContains` / `JsonHasKey` | PostgreSQL, SQLite, MySQL, MSSQL (JSON helpers) |
| `ArrayContains` / `ArrayOverlap` | PostgreSQL |
| `RangeContains` / `RangeOverlap` | PostgreSQL |
| `FullTextMatch` | MySQL |

See [DIALECT_SUPPORT](../DIALECT_SUPPORT.md) for the full matrix.

## Pattern + markers together

```python
from pydantic import Field
from sqlrules import JsonContains

class RowFilter(BaseModel):
    name: Annotated[str, Field(pattern=r"^A")]
    meta: Annotated[dict[str, Any], JsonContains({"active": True})]
```

Both need a plugin that registers `pattern` and the marker operators
(PostgreSQL does). SQL Server (`sqlrules-mssql`) does **not** register
`pattern`.

## Security note

Prefer static marker payloads and static `Field(pattern=...)` values.
Untrusted regex can be expensive once translated — see [SECURITY](../SECURITY.md).
