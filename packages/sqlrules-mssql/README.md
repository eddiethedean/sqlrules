# sqlrules-mssql

SQL Server dialect plugin for [SQLRules](https://github.com/eddiethedean/sqlrules).

## Install

```bash
pip install sqlrules-mssql
```

## Usage

```python
from typing import Annotated, Any

from pydantic import BaseModel, Field

from sqlrules import Compiler, JsonContains, JsonHasKey
from sqlrules_mssql import MssqlPlugin

class RowFilter(BaseModel):
    name: Annotated[str, Field(min_length=2, max_length=40)]
    meta: Annotated[dict[str, Any], JsonContains({"active": True}), JsonHasKey("active")]

compiler = Compiler(plugins=[MssqlPlugin()], dialect="mssql")
```

## Operators

| IR operator | Notes |
|---|---|
| `min_length` / `max_length` | `LEN(column)` instead of portable `length()` |
| `type_check` | Limited shape checks (typed columns; LIKE for some String forms) |
| `json_contains` | Shallow `JSON_VALUE` / `JSON_QUERY` checks |
| `json_has_key` | `JSON_VALUE` / `JSON_QUERY` IS NOT NULL |

`pattern` is intentionally not registered — prefer a custom translator over
guessing LIKE semantics.
