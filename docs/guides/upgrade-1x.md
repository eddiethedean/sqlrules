# Upgrade from SQLRules 1.x

SQLRules 2.0 changes the model declaration, compiler result, and plugin
contracts. Core and all four official dialect packages must use the same 2.x
line.

:::{dropdown} Setup: install 2.x packages and prepare an existing Pydantic model

~~~bash
pip install "sqlrules>=2,<3" "sqlrules-postgresql>=2,<3"
~~~

~~~python
import sqlrules
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, MetaData, Table

from sqlrules import Compiler
from sqlrules_postgresql import PostgresPlugin

users = Table("users", MetaData(), Column("age", Integer))


class ApiFilter(BaseModel):
    age: int = Field(ge=18)


compiler = Compiler(plugins=[PostgresPlugin(server_version=(16, 0))])
~~~
:::

## Use RuleSchema or convert a Pydantic model

Replace a model compiled directly in 1.x:

~~~python
from sqlrules import RuleSchema


class UserRules(RuleSchema):
    age: int


print("model fields:", list(UserRules.model_fields))
~~~

Output:

~~~text
model fields: ['age']
~~~

An unrestricted application model remains a normal Pydantic model, but it
must be converted before compilation:

~~~python
from sqlrules.integrations.pydantic import from_pydantic

conversion = from_pydantic(ApiFilter, on_incompatible="warn")
RulesModel = conversion.model
print("rules model:", RulesModel.__name__)
print("fields:", list(RulesModel.model_fields))
print("report outcomes:", [(entry.feature, entry.outcome) for entry in conversion.report.entries])
~~~

Output:

~~~text
rules model: ApiFilterRules
fields: ['age']
report outcomes: [('ge=18', 'preserved'), ('field type and supported constraints', 'preserved')]
~~~

The generated class is still a Pydantic model. Review the conversion report
for validators, serializers, fields, metadata, or behavior that was removed or
changed.

## Select a backend explicitly

The dialect string hint no longer selects a provider. Supply one backend
plugin:

~~~python
compiler = Compiler(plugins=[PostgresPlugin(server_version=(16, 0))])
compiled = compiler.compile(UserRules, users)
print("backend:", compiled.backend)
print("compiled fields:", [field.name for field in compiled.fields])
~~~

Output:

~~~text
backend: postgresql
compiled fields: ['age']
~~~

The server version is required for version-dependent coercions. Core still
performs no connection discovery or database I/O.

## Consume CompiledRules

Version 1 returned a field-to-expression dictionary. Version 2 returns one
complete predicate with field details and an explain plan:

~~~python
compiled = compiler.compile(UserRules, users)
matching = users.select().where(*sqlrules.where(compiled))
failing = users.select().where(*sqlrules.notwhere(compiled))
print("compiled fields:", [field.name for field in compiled.fields])
print("match/failure predicates:", len(sqlrules.where(compiled)), len(sqlrules.notwhere(compiled)))
~~~

Output:

~~~text
compiled fields: ['age']
match/failure predicates: 1 1
~~~

where() and flatten() keep the list return shape and now return a one-element
list containing the complete root predicate. notwhere() returns its total
complement. A lone scalar annotation now checks the bound column type even
without a Field constraint.

## Strictness and unsupported rules

Annotations now always create type rules. Lax mode applies the published
SQLRules conversion table; field strictness, strict aliases, and model
ConfigDict(strict=True) require matching observable database types. Optional
fields explicitly allow SQL NULL.

The 1.x on_unsupported warn/ignore options could omit a constraint. Version 2
requires retained constraints to translate or raises a capability error.
Convert unsupported Python-only features before compilation and inspect the
report instead.

## Column binding

Aliases no longer choose database columns implicitly. Use column_map keyed by
the Python field name or SQLRules Field(column="database_name"). Pydantic
aliases keep their normal validation and serialization behavior.

## Plugin API

Plugin API v2 adds source preparation and capability reporting. Existing API
v1 translators must be adapted so they operate on a prepared SQL expression.
Backend providers must report supported source types, server versions, and
storage assumptions. See [PLUGIN_SYSTEM](../PLUGIN_SYSTEM.md) and the
[support matrix](../TYPE_SUPPORT.md).
