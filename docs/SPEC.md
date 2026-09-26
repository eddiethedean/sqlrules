# SQLRules 2.0 Specification

## Public contract

`RuleSchema` is a Pydantic v2 `BaseModel` subclass whose accepted fields have
SQL meaning. It remains a normal Pydantic model: callers can instantiate it,
call `model_validate()` and `model_dump()`, and use it as a FastAPI model.
Unrestricted application models remain supported through the explicit
`from_pydantic()` converter.

Every supported scalar annotation creates a type rule, whether or not the
field has another constraint. The caller selects exactly one backend provider:

~~~python
from sqlalchemy import Column, Integer, MetaData, Table

from sqlrules import Compiler, RuleSchema, notwhere, where
from sqlrules_postgresql import PostgresPlugin

users = Table("users", MetaData(), Column("id", Integer), Column("age", Integer))


class UserRules(RuleSchema):
    id: int
    age: int | None


compiled = Compiler(plugins=[PostgresPlugin()]).compile(UserRules, users)
statement = users.select().where(*where(compiled))
failures = users.select().where(*notwhere(compiled))
print("compiled fields:", [field.name for field in compiled.fields])
print("match/failure predicates:", len(where(compiled)), len(notwhere(compiled)))
~~~

Output:

~~~text
compiled fields: ['id', 'age']
match/failure predicates: 1 1
~~~

Compilation performs no database I/O. It returns a `CompiledRules` instance
containing one total root predicate, per-field results, capability assumptions,
diagnostics, and `explain()` output.

## Predicate helpers

- `where(compiled)` returns a one-item list containing the complete predicate.
- `flatten(compiled)` is an alias for `where(compiled)`.
- `notwhere(compiled)` returns a one-item list containing the exact complement.

The predicate is always SQL TRUE or FALSE. SQL NULL matches a field only when
its annotation is nullable. Invalid values and failed constraints do not raise
from the SQL expression; they produce a non-match. `notwhere()` therefore
selects each row that fails one or more rules, including NULL and invalid
values.

## Supported declarations

Scalar annotations: `bool`, `int`, `float`, `Decimal`, `str`, `date`,
`datetime`, `time`, and `UUID`; homogeneous `Literal` and `Enum` domains; and
nullable forms. Lists and dictionaries are accepted only with a supported
dialect marker. Collection item validation, general unions, nested JSON
schemas, and custom Python validators are outside the 2.0 subset.

Supported constraints include `gt`, `ge`, `lt`, `le`, `multiple_of`, string
`min_length` / `max_length`, `pattern` where the provider registers a
translator, and compatible Literal/Enum membership. Existing JSON, array,
range, and full-text markers remain provider-specific.

Pydantic `Field`, `ConfigDict`, strict aliases, supported constrained aliases,
`annotated_types` constraints, and compatible `Annotated` metadata can be
imported directly. SQLRules `Field(column=...)` adds an optional database
column binding. Class creation rejects unsupported metadata, invalid bounds,
duplicate constraints, custom validators/serializers, computed fields, and
custom schema hooks.

## Type and conversion behavior

Lax mode uses the versioned SQLRules conversion profile in
[TYPE_SUPPORT](TYPE_SUPPORT.md). Strict mode checks the logical type observable
in the database. An explicit field strict setting overrides a reusable type
setting, which overrides model `ConfigDict(strict=...)`; lax is the default.
SQLite relies on runtime `typeof()` because column affinity cannot prove the
stored type of each row.

A backend mismatch that can be established safely is a non-match. If a backend
cannot safely inspect or convert a source representation, compilation raises
`CapabilityError`. Retained rules are never skipped by a warning or ignore
policy.

## Column binding

For each rule field, resolution order is:

1. `column_map[field_name]`
2. `sqlrules.Field(column="database_name")`
3. the Python field name

Pydantic validation and serialization aliases keep their normal model
behavior; they do not select database columns automatically. Every schema
field must bind to a column, including fields with only a type annotation.

## Plugins

Constraint plugins register translators through `TranslatorRegistry`.
Backend providers additionally prepare source values and expose a capability
profile. The plugin API version is exported as
`sqlrules.PLUGIN_API_VERSION` and currently equals `"2"`. See
[PLUGIN_SYSTEM](PLUGIN_SYSTEM.md) and [DIALECT_SUPPORT](DIALECT_SUPPORT.md).
