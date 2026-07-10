# sqlrules-postgresql

PostgreSQL dialect plugin for [SQLRules](https://github.com/eddiethedean/sqlrules).

## Install

```bash
pip install sqlrules-postgresql
```

## Usage

```python
import re
from typing import Annotated, Any

from pydantic import BaseModel, Field
from sqlalchemy import Column, MetaData, Table
from sqlalchemy.dialects.postgresql import ARRAY, INT4RANGE, JSONB, TEXT

from sqlrules import ArrayContains, Compiler, JsonContains, RangeContains
from sqlrules_postgresql import PostgresPlugin

class RowFilter(BaseModel):
    name: Annotated[str, Field(pattern=re.compile(r"^a", re.I))]
    meta: Annotated[dict[str, Any], JsonContains({"active": True})]
    tags: Annotated[list[str], ArrayContains(["admin"])]
    span: Annotated[int, RangeContains(5)]

table = Table(
    "rows",
    MetaData(),
    Column("name", TEXT),
    Column("meta", JSONB),
    Column("tags", ARRAY(TEXT)),
    Column("span", INT4RANGE),
)

compiler = Compiler(plugins=[PostgresPlugin()], dialect="postgresql")
rules = compiler.compile(RowFilter, table)
```

## Operators

| IR operator | SQLAlchemy / PostgreSQL |
|---|---|
| `pattern` | `~` or `~*` (when `PatternSpec.ignore_case`) |
| `type_check` | Shape/type predicates from `TypeSpec` (see matrix below) |
| `json_contains` | JSONB `contains` / `@>` |
| `json_has_key` | JSONB `has_key` / `?` |
| `array_contains` | array `contains` |
| `array_overlap` | array `overlap` / `&&` |
| `range_contains` | range `@>` |
| `range_overlap` | range `&&` |

### `type_check` matrix (approximate)

Enable with `Compiler(..., emit_type_checks=True)`. Not full Pydantic
parity — inexpressible pairs raise.

| Python type | Lax | Strict |
|---|---|---|
| `int` | Integer column; String `~` digit pattern; numeric whole-number | Integer column only |
| `bool` | unsupported (raise) | Boolean `IN (true, false)` |
| `str` | String/Text `IS NOT NULL` | same |
| `float` / `Decimal` | numeric column; String float-ish `~` | numeric column |
| `date` / `datetime` / `time` / `UUID` | typed column or String format `~` | typed column |

`Optional[T]` → `(column IS NULL) OR <predicate>`.

## Security note

`pattern` becomes a PostgreSQL regex (`~` / `~*`). Untrusted pattern strings
can cause expensive engine-side evaluation (ReDoS-class cost). Prefer
static/allowlisted patterns. See
[SECURITY](https://sqlrules.readthedocs.io/en/latest/SECURITY.html).
