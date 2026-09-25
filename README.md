# SQLRules

[![CI](https://github.com/eddiethedean/sqlrules/actions/workflows/ci.yml/badge.svg)](https://github.com/eddiethedean/sqlrules/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/sqlrules.svg)](https://pypi.org/project/sqlrules/)
[![Documentation](https://readthedocs.org/projects/sqlrules/badge/?version=latest)](https://sqlrules.readthedocs.io/en/latest/)
[![License](https://img.shields.io/pypi/l/sqlrules.svg)](https://github.com/eddiethedean/sqlrules/blob/main/LICENSE)

**Compile SQLRules-owned Pydantic models into safe SQLAlchemy predicates.**

RuleSchema is a Pydantic v2 model. It validates Python data with normal
Pydantic APIs and can be used as a FastAPI request or response model. SQLRules
accepts only declarations that have a defined SQL meaning. The compiler
requires one explicit database backend and returns a complete predicate for
matching rows plus a notwhere() complement for rows that fail any rule.

SQLRules performs no database I/O and never changes stored values.

## Quick start

Install SQLRules and the dialect provider for your database:

~~~bash
pip install "sqlrules>=2,<3" "sqlrules-postgresql>=2,<3"
~~~

~~~python
from typing import Annotated

from pydantic import ConfigDict, Field as PydanticField, StringConstraints
from sqlalchemy import Column, Integer, MetaData, String, Table

from sqlrules import Compiler, RuleSchema, notwhere, where
from sqlrules_postgresql import PostgresPlugin

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
    age: int | None = PydanticField(ge=18)
    name: Annotated[str, StringConstraints(min_length=2)]


# RuleSchema remains a normal Pydantic model.
request = UserRules.model_validate({"id": "12", "age": "21", "name": "Ada"})
assert request.id == 12

compiler = Compiler(plugins=[PostgresPlugin(server_version=(16, 0))])
compiled = compiler.compile(UserRules, users)

matching = users.select().where(*where(compiled))
failing = users.select().where(*notwhere(compiled))
~~~

A lone scalar annotation is a rule too: id: int requires the bound column to
contain a compatible integer. Lax mode applies the documented SQLRules
conversions; Field(strict=True), a strict Pydantic alias, or
ConfigDict(strict=True) requires the database's observable logical type to
match. Optional annotations accept SQL NULL.

compiled.predicate is the complete root expression. compiled.explain() shows
bindings, coercions, backend assumptions, and diagnostics without executing a
database EXPLAIN.

## Convert an existing Pydantic model

Unrestricted Pydantic models remain usable in application code. Convert one
explicitly before compiling it:

~~~python
from pydantic import BaseModel, Field
from sqlrules.integrations.pydantic import from_pydantic


class ApiFilter(BaseModel):
    age: int = Field(ge=18)
    name: str


conversion = from_pydantic(ApiFilter, on_incompatible="warn")
RulesModel = conversion.model
report = conversion.report
~~~

The converter returns a usable RuleSchema class and a deterministic report.
It preserves supported types, constraints, defaults, aliases, and descriptive
metadata. It reports Python validators, serializers, computed fields,
unsupported metadata, and other behavior it removes or changes. Conversion
policies are warn (default), drop (return the report without warnings), and
raise (reject any semantic loss). Default factories and Python callbacks are
never executed to infer SQL rules.

## Supported declarations

The scalar vocabulary is bool, int, float, Decimal, str, date, datetime, time,
and UUID, plus homogeneous Literal and Enum domains, and nullable forms.
Supported constraints include numeric bounds, multiple_of, string lengths,
patterns, literal/enum membership, and the existing dialect markers. Use
Pydantic Field, ConfigDict, strict aliases, constrained aliases, and supported
Annotated metadata directly.

Unsupported declarations fail when a RuleSchema class is created. Custom
validators, serializers, computed fields, arbitrary annotation metadata,
string normalization, general unions, nested item validation, and arbitrary
Python transforms do not have a 2.0 SQL representation.

The [type and backend support matrix](docs/TYPE_SUPPORT.md) lists supported
source types, conversions, database versions, collation assumptions, and
compile-time capability errors. Unsupported backend behavior is never skipped
by a warning or ignore policy.

## Dialect providers

The four official packages are versioned with the core package:

~~~bash
pip install "sqlrules-postgresql>=2,<3"
pip install "sqlrules-sqlite>=2,<3"
pip install "sqlrules-mysql>=2,<3"
pip install "sqlrules-mssql>=2,<3"
pip install "sqlrules[dialects]"  # all four
~~~

Select exactly one backend provider when compiling. PostgreSQL text-to-scalar
coercion requires PostgresPlugin(server_version=(16, 0)); MySQL text-to-int
coercion requires MySQL 8.0+; SQL Server safe text conversions require SQL
Server 2012+. SQLite text checks use runtime typeof() and need the bundled
register_regexp() helper on each connection when text coercion or patterns
are used. Unsupported combinations raise CapabilityError during compilation.

## Project links

- [Getting started](https://sqlrules.readthedocs.io/en/latest/guides/getting-started.html)
- [API reference](https://sqlrules.readthedocs.io/en/latest/API.html)
- [Plugin API v2](https://sqlrules.readthedocs.io/en/latest/PLUGIN_SYSTEM.html)
- [Migration from 1.x](https://sqlrules.readthedocs.io/en/latest/guides/upgrade-1x.html)
- [Security](https://sqlrules.readthedocs.io/en/latest/SECURITY.html)
- [Runnable examples](examples/)

Requires Python 3.10+, Pydantic v2, and SQLAlchemy 2.x.
