# Getting started

Compile a constrained Pydantic model into SQLAlchemy WHERE expressions in a
few minutes.

**Requires** Python {{ python_requires }}, Pydantic v2, and SQLAlchemy 2.x.

## 1. Install

```bash
pip install sqlrules
# or: uv add sqlrules
```

Optional dialect plugins (regex, JSON, arrays, and related operators):

```bash
pip install sqlrules-postgresql   # or sqlite / mysql / mssql
# or: pip install "sqlrules[postgresql]" / "sqlrules[dialects]"
```

## 2. Define a filter model and a table

```python
from typing import Annotated

from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, MetaData, String, Table

import sqlrules

users = Table(
    "users",
    MetaData(),
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
#     "name": [length(users.c.name) >= 2],
# }

stmt = users.select().where(*sqlrules.where(rules))
```

Prefer `sqlrules.where(rules)` (identical alias: `flatten`).

**Success check:** `rules` is a `dict[str, list[...]]` keyed by Python field
names. Unconstrained fields are omitted.

## 4. The `pattern` footgun (and fix)

`Field(pattern=...)` is extracted into IR, but **core has no portable regex
translator**. This fails on purpose:

```python
class NameFilter(BaseModel):
    name: Annotated[str, Field(pattern=r"^A")]

sqlrules.compile(NameFilter, users)  # UnsupportedConstraintError
```

Install a dialect plugin and pass it to `Compiler`:

```python
from sqlrules import Compiler
from sqlrules_postgresql import PostgresPlugin

compiler = Compiler(plugins=[PostgresPlugin()], dialect="postgresql")
rules = compiler.compile(NameFilter, users)
```

`dialect=` is a **hint only** — it does not load plugins. See
[`examples/postgresql_pattern.py`](https://github.com/eddiethedean/sqlrules/blob/main/examples/postgresql_pattern.py).

## 5. What compiled (and what did not)

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

## When *not* to use SQLRules

Two static filters you will never share with a Pydantic model? Write the
SQLAlchemy expressions by hand. SQLRules helps when the model is the shared
source of truth.

## Next steps

- [Examples on GitHub](https://github.com/eddiethedean/sqlrules/tree/main/examples)
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
