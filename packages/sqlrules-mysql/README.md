# sqlrules-mysql

MySQL / MariaDB dialect plugin for [SQLRules](https://github.com/eddiethedean/sqlrules).

## Install

```bash
pip install sqlrules-mysql
```

## Usage

```python
from typing import Annotated, Any

from pydantic import BaseModel, Field

from sqlrules import Compiler, FullTextMatch, JsonContains
from sqlrules_mysql import MysqlPlugin

class RowFilter(BaseModel):
    name: Annotated[str, Field(pattern=r"^A")]
    meta: Annotated[dict[str, Any], JsonContains({"active": True})]
    body: Annotated[str, FullTextMatch("sqlrules")]

compiler = Compiler(plugins=[MysqlPlugin()], dialect="mysql")
```

## Operators

| IR operator | Notes |
|---|---|
| `pattern` | `REGEXP` (case-insensitive under typical collations) |
| `json_contains` | `JSON_CONTAINS(column, payload) = 1` |
| `json_has_key` | `JSON_CONTAINS_PATH(column, 'one', '$.key') = 1` |
| `fulltext_match` | `MATCH(column) AGAINST (value)` — requires a FULLTEXT index |
