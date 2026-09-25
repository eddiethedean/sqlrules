# sqlrules-postgresql

PostgreSQL backend provider for [SQLRules](https://github.com/eddiethedean/sqlrules).
The package version follows the core 2.x line.

## Install

```bash
pip install "sqlrules>=2,<3" "sqlrules-postgresql>=2,<3"
```

## Use

```python
from typing import Annotated, Any

from pydantic import Field
from sqlalchemy import Column, MetaData, String, Table
from sqlalchemy.dialects.postgresql import ARRAY, INT4RANGE, JSONB

from sqlrules import ArrayContains, Compiler, JsonContains, RangeContains, RuleSchema, where
from sqlrules_postgresql import PostgresPlugin

rows = Table(
    "rows",
    MetaData(),
    Column("name", String),
    Column("meta", JSONB),
    Column("tags", ARRAY(String)),
    Column("span", INT4RANGE),
)


class RowRules(RuleSchema):
    name: Annotated[str, Field(pattern=r"^A")]
    meta: Annotated[dict[str, Any], JsonContains({"active": True})]
    tags: Annotated[list[str], ArrayContains(["admin"])]
    span: Annotated[int, RangeContains(5)]


compiled = Compiler(plugins=[PostgresPlugin(server_version=(16, 0))]).compile(
    RowRules, rows
)
statement = rows.select().where(*where(compiled))
```

## Capabilities

- `pattern`: PostgreSQL `~` / `~*`
- JSONB containment and key membership
- ARRAY containment and overlap
- Range containment and overlap
- Safe lax text-to-int/float/Decimal parsing on PostgreSQL 16+

String Literal and Enum fields require a column with `C` or `POSIX`
collation. Review the [type support matrix](https://sqlrules.readthedocs.io/en/latest/TYPE_SUPPORT.html)
for the exact conversion profile and limitations.

## Pattern cost

Untrusted regular expressions can cause expensive engine-side evaluation.
Prefer patterns authored with the rule model. See the SQLRules
[security notes](https://sqlrules.readthedocs.io/en/latest/SECURITY.html).
