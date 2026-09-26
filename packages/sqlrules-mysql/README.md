# sqlrules-mysql

MySQL backend provider for [SQLRules](https://github.com/eddiethedean/sqlrules).
This official provider first shipped with [SQLRules 2.0.0](https://github.com/eddiethedean/sqlrules/releases/tag/v2.0.0)
on 2026-09-26. Official dialect packages share core's release version.

This provider targets MySQL 8.0+. MariaDB is outside the supported server
matrix because its regular-expression function API differs from MySQL's.

## Install

```bash
pip install "sqlrules>=2,<3" "sqlrules-mysql>=2,<3"
```

## Use

```python
from typing import Annotated, Any

from pydantic import Field
from sqlalchemy import Column, JSON, MetaData, String, Table

from sqlrules import Compiler, FullTextMatch, JsonContains, RuleSchema, where
from sqlrules_mysql import MysqlPlugin

rows = Table(
    "rows",
    MetaData(),
    Column("name", String),
    Column("meta", JSON),
    Column("body", String),
)


class RowRules(RuleSchema):
    name: Annotated[str, Field(pattern=r"^A")]
    meta: Annotated[dict[str, Any], JsonContains({"active": True})]
    body: Annotated[str, FullTextMatch("sqlrules")]


provider = MysqlPlugin(server_version=(8, 0, 36))
compiled = Compiler(plugins=[provider]).compile(RowRules, rows)
statement = rows.select().where(*where(compiled))
```

## Capabilities

- `pattern`: MySQL `REGEXP`
- JSON containment and key lookup
- Full-text matching (requires a matching FULLTEXT index)
- Safe lax text-to-int conversion on MySQL 8.0+

Text-to-float and text-to-Decimal are compile-time capability errors. String
Literal and Enum fields need an explicit binary or case-sensitive collation.
See the [type support matrix](https://sqlrules.readthedocs.io/en/latest/TYPE_SUPPORT.html).

## Pattern cost

Untrusted regular expressions and full-text queries can be expensive. Prefer
static or allowlisted values. See the SQLRules
[security notes](https://sqlrules.readthedocs.io/en/latest/SECURITY.html).
