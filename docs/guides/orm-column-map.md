# Bind ORM models and `column_map`

SQLRules binds each constrained field to a SQLAlchemy column. By default it
looks up columns on the object you pass as `table` (a `Table`, selectable, or
ORM class/entity). Use `column_map` when names differ or binding is ambiguous.

## Table (default)

```python
from typing import Annotated

from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, MetaData, String, Table

import sqlrules

users = Table(
    "users",
    MetaData(),
    Column("age", Integer),
    Column("full_name", String),
)

class UserFilter(BaseModel):
    age: Annotated[int, Field(ge=18)]
    name: Annotated[str, Field(min_length=1, alias="full_name")]

# String Field aliases are tried before the Python field name.
rules = sqlrules.compile(UserFilter, users)
```

## Explicit `column_map`

Pass a map from **Python field name or alias string** to a column element when
automatic lookup fails (joined tables, renamed columns, hybrid attributes):

```python
rules = sqlrules.compile(
    UserFilter,
    users,
    column_map={
        "age": users.c.age,
        "full_name": users.c.full_name,  # alias used on the Field
    },
)
```

## Declarative ORM

```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    age: Mapped[int]
    name: Mapped[str]

class UserFilter(BaseModel):
    age: Annotated[int, Field(ge=18)]
    name: Annotated[str, Field(min_length=2)]

rules = sqlrules.compile(UserFilter, User)
stmt = User.__table__.select().where(*sqlrules.where(rules))
```

If an ORM attribute is not a real column (relationship, hybrid), pass that
field through `column_map` to the underlying column, or you will get
`MissingColumnError`.

## Tips

- Rule dict keys are always **Python field names**, not aliases.
- Unconstrained supported-type fields are omitted and do not need a column.
- See [Troubleshooting](troubleshooting.md) for `MissingColumnError`.
