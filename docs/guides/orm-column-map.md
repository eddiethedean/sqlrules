# ORM and column mapping

Every RuleSchema field binds to a database column. The binding precedence is:

1. Explicit column_map entry keyed by the Python field name.
2. SQLRules Field(column=...) metadata.
3. A column whose name matches the Python field.

Pydantic aliases affect validation and serialization, but never choose a
database column automatically.

## Explicit column_map

~~~python
from sqlrules import Compiler, RuleSchema
from sqlrules_postgresql import PostgresPlugin


class UserRules(RuleSchema):
    display_name: str
    minimum_age: int


compiled = Compiler(plugins=[PostgresPlugin(server_version=(16, 0))]).compile(
    UserRules,
    users,
    column_map={
        "display_name": User.display_name,
        "minimum_age": User.age,
    },
)
~~~

Values in column_map must be SQLAlchemy expressions or ORM attributes that
expose a SQL expression. Each expression still needs source type evidence from
the selected provider.

## Field(column=...)

~~~python
from sqlrules import Field, RuleSchema


class UserRules(RuleSchema):
    display_name: str = Field(column="name")
~~~

The custom Field wrapper retains all standard Pydantic Field behavior. The
column name is separate from Pydantic aliases and serialized field names.

## ORM models

Mapped ORM attributes can be passed directly as the table argument when the
model exposes SQLAlchemy attributes with matching names. Use column_map when a
rule field intentionally refers to a different mapped attribute.

Missing bindings raise MissingColumnError during compilation, including for
type-only annotations with no value constraints.
