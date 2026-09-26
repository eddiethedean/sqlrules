# sqlrules-mssql

SQL Server backend provider for [SQLRules](https://github.com/eddiethedean/sqlrules).
The package version follows the core 2.x line.

## Install

```bash
pip install "sqlrules>=2,<3" "sqlrules-mssql>=2,<3"
```

## Use

```python
from typing import Annotated, Any

from pydantic import Field
from sqlalchemy import Column, MetaData, String, Table

from sqlrules import Compiler, JsonContains, JsonHasKey, RuleSchema, where
from sqlrules_mssql import MssqlPlugin

rows = Table(
    "rows",
    MetaData(),
    Column("name", String),
    Column("meta", String),  # SQL Server stores JSON documents in text columns.
)


class RowRules(RuleSchema):
    name: Annotated[str, Field(min_length=2, max_length=40)]
    meta: Annotated[dict[str, Any], JsonContains({"active": True}), JsonHasKey("active")]


provider = MssqlPlugin(server_version=(16, 0), compatibility_level=160)
compiled = Compiler(plugins=[provider]).compile(RowRules, rows)
statement = rows.select().where(*where(compiled))
```

## Capabilities

- SQL Server `LEN` length constraints
- Guarded JSON helpers for text columns validated with `ISJSON` (`server_version` >= 13 and explicit `compatibility_level` >= 130)
- `JsonContains` supports null, boolean, and string values; nested objects and arrays compare structurally, while numeric JSON values raise `CapabilityError` because exact numeric equality cannot be guaranteed from `OPENJSON` text values
- Safe lax text-to-int/float conversions on SQL Server 2012+
- No built-in regex translator
- Text-to-Decimal is a compile-time capability error

String Literal and Enum fields require an explicit binary or
case-sensitive collation. See the [type support matrix](https://sqlrules.readthedocs.io/en/latest/TYPE_SUPPORT.html).
