# SQLRules

**Compile constrained Pydantic models into SQLAlchemy WHERE-rule dictionaries.**

One package. One job. Deterministic output. Zero database dependency.

```python
from typing import Annotated
from pydantic import BaseModel, Field
from sqlalchemy import Table, Column, Integer, String, MetaData

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

rules = sqlrules.compile(UserFilter, users)
# {
#     "age": [users.c.age >= 18, users.c.age <= 65],
#     "name": [func.length(users.c.name) >= 2],
# }

stmt = users.select().where(*sqlrules.where(rules))
```

## Install

```bash
pip install sqlrules
```

Requires Python 3.10+, Pydantic v2, and SQLAlchemy 2.x.

## Supported constraints (0.1)

| Constraint | SQLAlchemy expression |
|---|---|
| `gt` / `ge` / `lt` / `le` | `column > / >= / < / <= value` |
| `multiple_of` | `column % value == 0` |
| `min_length` / `max_length` | `func.length(column) >= / <= value` |
| `Literal[...]` | `column.in_(...)` |
| `Enum` | `column.in_(...)` |

Unsupported constraints raise `UnsupportedConstraintError` by default.
Use `on_unsupported="warn"` or `"ignore"` to change that policy for unknown
constraint operators (unsupported types always raise).

## Public API

```python
sqlrules.compile(model, table, *, column_map=None, on_unsupported="raise")
sqlrules.where(rules)    # flatten all expressions
sqlrules.flatten(rules)  # alias of where()
```

## Non-goals

SQLRules is not an ORM, validator, query builder, SQL string generator,
migration tool, or database client. It only compiles supported Pydantic
constraints into SQLAlchemy expressions.

## Documentation

See [`docs/index.md`](docs/index.md) for the full documentation set,
including the [spec](docs/SPEC.md), [API](docs/API.md),
[architecture](docs/ARCHITECTURE.md), and [roadmap](docs/ROADMAP.md).

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
mypy src/sqlrules
```

## License

MIT
