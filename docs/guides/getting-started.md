# Getting started

Compile a constrained Pydantic model into SQLAlchemy WHERE expressions in a
few minutes.

**Requires** Python {{ python_requires }}, Pydantic v2, and SQLAlchemy 2.x.

## 1. Install

```bash
pip install sqlrules
```

Optional dialect plugins (regex, JSON, arrays, and related operators):

```bash
pip install sqlrules-postgresql   # or sqlite / mysql / mssql
# or: pip install "sqlrules[dialects]"
```

## 2. Define a filter model and a table

```python
from typing import Annotated

from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, MetaData, String, Table

import sqlrules

metadata = MetaData()
users = Table(
    "users",
    metadata,
    Column("age", Integer),
    Column("name", String),
)

class UserFilter(BaseModel):
    age: Annotated[int, Field(ge=18, le=65)]
    name: Annotated[str, Field(min_length=2)]
```

## 3. Compile and apply

```python
rules = sqlrules.compile(UserFilter, users)
# {
#     "age": [users.c.age >= 18, users.c.age <= 65],
#     "name": [func.length(users.c.name) >= 2],
# }

stmt = users.select().where(*sqlrules.where(rules))
```

**Success check:** `rules` is a `dict[str, list[...]]` keyed by Python field
names. Unconstrained fields are omitted. `sqlrules.where(rules)` flattens all
expressions for `.where(...)`.

## 4. What compiled (and what did not)

| Constraint | Core behavior |
|---|---|
| `gt` / `ge` / `lt` / `le` | Comparison on the bound column |
| `multiple_of` | Modulo equality |
| `min_length` / `max_length` | `func.length(column)` |
| `Literal[...]` / `Enum` | `column.in_(...)` |
| `pattern` | Extracted to IR only — needs a dialect plugin or custom translator |

Unsupported **operators** raise by default. Use
`on_unsupported="warn"` or `"ignore"` to skip unknown operators. Unsupported
**types** always raise — including on unconstrained fields (whole-model type
matrix).

Untrusted `Field(pattern=...)` values are a CPU/ReDoS cost risk once a dialect
plugin translates them; prefer static patterns. See
[SECURITY](../SECURITY.md).

## Next steps

- [Constraint map](../CONSTRAINTS.md) — full operator → expression table
- [Plugin system](../PLUGIN_SYSTEM.md) — dialect packages and custom translators
- [Public API](../API.md) — `Compiler`, two-phase compile, API tiers
- [FAQ](faq.md) · [Troubleshooting](troubleshooting.md)

:::{admonition} Not a query builder
:class: note

SQLRules only compiles constraints into expressions. You still compose,
dialect-select, and execute queries with SQLAlchemy. See
[design philosophy](design-philosophy.md).
:::
