# Getting started

SQLRules compiles the supported fields in a RuleSchema into one total
SQLAlchemy predicate. RuleSchema is also a normal Pydantic v2 model.

## 1. Install

~~~bash
pip install "sqlrules>=2,<3" "sqlrules-postgresql>=2,<3"
~~~

Choose the dialect package for the database you query. Core never discovers
or selects a backend from a connection.

## 2. Define a schema and table

~~~python
from typing import Annotated

from pydantic import ConfigDict, Field, StringConstraints
from sqlalchemy import Column, Integer, MetaData, String, Table

from sqlrules import RuleSchema

users = Table(
    "users",
    MetaData(),
    Column("id", Integer),
    Column("age", Integer),
    Column("name", String),
)


class UserRules(RuleSchema):
    model_config = ConfigDict(strict=False)

    id: int
    age: int | None = Field(ge=18, le=120)
    name: Annotated[str, StringConstraints(min_length=2)]
~~~

The Pydantic constraints are imported directly. The scalar annotation itself
creates a database type rule, so id must match the selected backend's int
profile even without a Field constraint.

## 3. Validate and compile

~~~python
from sqlrules import Compiler, notwhere, where
from sqlrules_postgresql import PostgresPlugin

request = UserRules.model_validate({"id": "42", "age": "21", "name": "Ada"})
assert request.id == 42

compiler = Compiler(plugins=[PostgresPlugin(server_version=(16, 0))])
compiled = compiler.compile(UserRules, users)

matches = users.select().where(*where(compiled))
fails = users.select().where(*notwhere(compiled))
~~~

where() returns a one-item list containing the complete root predicate.
notwhere() returns the complement and selects every row that fails one or more
rules. SQLRules performs no database I/O.

## 4. Convert an existing Pydantic model

Use from_pydantic() for a Pydantic model that includes features outside the
SQLRules declaration subset:

~~~python
from pydantic import BaseModel, Field
from sqlrules.integrations.pydantic import from_pydantic


class ApiFilter(BaseModel):
    age: int = Field(ge=18)


conversion = from_pydantic(ApiFilter, on_incompatible="warn")
RulesModel = conversion.model
print(conversion.report)
~~~

The converter strips unsupported behavior according to the selected policy
and reports changed, unknown, or dropped semantics. It never runs validators,
serializers, or default factories to infer SQL.

## 5. Patterns and markers

Patterns and JSON/array/range operators need a plugin for the selected
database. Select one backend provider:

~~~python
compiler = Compiler(plugins=[PostgresPlugin(server_version=(16, 0))])
compiled = compiler.compile(NameRules, users)
~~~

SQLite text coercion and pattern matching use REGEXP, and string length rules
use a Python-compatible Unicode code-point counter. Register
`sqlrules_sqlite.register_sqlite_functions()` on each SQLite connection when
those rules are used. The
[support matrix](../TYPE_SUPPORT.md) describes source types, conversions,
server versions, and compile-time capability errors.

## Next steps

- [Migration from 1.x](upgrade-1x.md)
- [Dialect markers](markers.md)
- [ORM and column mapping](orm-column-map.md)
- [Plugin API v2](../PLUGIN_SYSTEM.md)
- [Troubleshooting](troubleshooting.md)
