# SQLRules

[![CI](https://github.com/eddiethedean/sqlrules/actions/workflows/ci.yml/badge.svg)](https://github.com/eddiethedean/sqlrules/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/sqlrules.svg)](https://pypi.org/project/sqlrules/)
[![Documentation](https://readthedocs.org/projects/sqlrules/badge/?version=latest)](https://sqlrules.readthedocs.io/en/latest/)
[![License](https://img.shields.io/pypi/l/sqlrules.svg)](https://github.com/eddiethedean/sqlrules/blob/main/LICENSE)

**Compile Pydantic Field constraint metadata into SQLAlchemy WHERE expressions.**

SQLRules reads constraints declared on a model (`Field(ge=18)`, `min_length`,
`Literal`, …) and turns them into SQLAlchemy boolean expressions. It depends on
Pydantic v2 and SQLAlchemy 2.x, performs **no database I/O**, and needs a
dialect plugin only for non-portable operators (regex, JSON, arrays, …).

```text
SQLRules does THIS (constraint metadata → expressions):
  Field(ge=18)           →  column >= 18

It does NOT do this (instance values → predicates):
  UserFilter(age=25)     →  column == 25   # not what sqlrules.compile does
```

Not an ORM, validator, or query builder: **constraint metadata → expressions**,
nothing else.

**In 30 seconds:**

```bash
pip install "sqlrules>=1,<2"
```

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

rules = sqlrules.compile(UserFilter, users)
# {
#     "age": [users.c.age >= 18, users.c.age <= 65],
#     "name": [length(users.c.name) >= 2],
# }

stmt = users.select().where(*sqlrules.where(rules))
```

> **`pattern` needs a plugin.** Core compiles comparisons, lengths, `Literal`,
> and `Enum`. Regex / JSON / arrays require a dialect package (see below).
> Prefer static patterns; untrusted regex can be expensive (see
> [SECURITY](https://sqlrules.readthedocs.io/en/latest/SECURITY.html)).

Full walkthrough: [Getting started](https://sqlrules.readthedocs.io/en/latest/guides/getting-started.html) · Runnable scripts: [`examples/`](examples/).

| | |
|---|---|
| **Latest** | [sqlrules on PyPI](https://pypi.org/project/sqlrules/) · [Changelog](https://sqlrules.readthedocs.io/en/latest/project/changelog.html) |
| **Docs** | [sqlrules.readthedocs.io](https://sqlrules.readthedocs.io/en/latest/) |
| **Python** | 3.10+ (Pydantic v2, SQLAlchemy 2.x) |

---

## Choose your path

| Path | Start here |
|---|---|
| **Not sure?** | [Start here](https://sqlrules.readthedocs.io/en/latest/guides/start-here.html) |
| **Compile constraints** | [Getting started](https://sqlrules.readthedocs.io/en/latest/guides/getting-started.html) |
| **Dialect plugins** | [Plugin system](https://sqlrules.readthedocs.io/en/latest/PLUGIN_SYSTEM.html) |
| **Evaluate fit** | [Design philosophy](https://sqlrules.readthedocs.io/en/latest/guides/design-philosophy.html) |
| **Contribute** | [Contributing](https://sqlrules.readthedocs.io/en/latest/project/contributing.html) |

---

## Install

**Requires** Python 3.10+, Pydantic v2, and SQLAlchemy 2.x (pulled in
transitively).

### From PyPI

```bash
pip install "sqlrules>=1,<2"
# or: uv add "sqlrules>=1,<2"
```

Optional dialect plugins (same major line as core):

```bash
pip install "sqlrules-postgresql>=1,<2"   # ~ / ~*, JSONB, ARRAY, range
pip install "sqlrules-sqlite>=1,<2"       # REGEXP helper + JSON
pip install "sqlrules-mysql>=1,<2"        # REGEXP, JSON, full-text
pip install "sqlrules-mssql>=1,<2"        # JSON + LEN string ops
```

Extras are equivalent shortcuts (pull the matching plugin package):

```bash
pip install "sqlrules[postgresql]"
pip install "sqlrules[dialects]"   # all four
```

SQLite `pattern` emits `REGEXP` — call `sqlrules_sqlite.register_regexp(connection)`
on each connection before executing queries.

### From source (contributors)

```bash
git clone https://github.com/eddiethedean/sqlrules.git
cd sqlrules
python -m venv .venv && source .venv/bin/activate
make install   # editable core + all four dialect plugins
```

**End users** should install from PyPI. You do not need to clone this repo or
install from `packages/` for normal application use.

### Plugin example

```python
from typing import Annotated, Any

from pydantic import BaseModel, Field
from sqlalchemy import Column, MetaData, String, Table
from sqlalchemy.dialects.postgresql import JSONB

import sqlrules
from sqlrules import Compiler, JsonContains
from sqlrules_postgresql import PostgresPlugin

table = Table(
    "rows",
    MetaData(),
    Column("name", String),
    Column("meta", JSONB),
)

class RowFilter(BaseModel):
    name: Annotated[str, Field(pattern=r"^A")]
    meta: Annotated[dict[str, Any], JsonContains({"active": True})]

# dialect= is a hint for custom translators only — it does not load plugins.
compiler = Compiler(plugins=[PostgresPlugin()], dialect="postgresql")
rules = compiler.compile(RowFilter, table)
stmt = table.select().where(*sqlrules.where(rules))
```

See [`examples/postgresql_pattern.py`](examples/postgresql_pattern.py).

### Common failures

| Symptom | Fix |
|---|---|
| `UnsupportedConstraintError` on `pattern` | Install a dialect plugin and pass it to `Compiler(plugins=[...])` |
| `NameError: sqlrules` after `from sqlrules import Compiler` | Also `import sqlrules` (or import `where`) |
| SQLite `REGEXP` errors at execute time | Call `register_regexp(connection)` |

More: [Troubleshooting](https://sqlrules.readthedocs.io/en/latest/guides/troubleshooting.html).

## Supported constraints (1.0)

| Constraint | SQLAlchemy expression |
|---|---|
| `gt` / `ge` / `lt` / `le` | `column > / >= / < / <= value` |
| `multiple_of` | `column % value == 0` |
| `min_length` / `max_length` | `func.length(column) >= / <= value` |
| `Literal[...]` | `column.in_(...)` |
| `Enum` | `column.in_(...)` |

`pattern` is extracted into IR (`PatternSpec`) but has **no portable core
translator**. Install a dialect plugin or register a custom translator.

With `emit_type_checks=True`, supported scalar annotations also emit
`type_check` (`TypeSpec`) IR — likewise plugin-translated only.

Dialect markers (`JsonContains`, `ArrayContains`, `RangeContains`,
`FullTextMatch`, …) are re-exported from `sqlrules` (and live in
`sqlrules.markers`); they require a dialect plugin.

Unsupported constraints raise `UnsupportedConstraintError` by default.
Use `on_unsupported="warn"` or `"ignore"` for unknown **operators**.
Unconstrained fields with **supported** types are omitted from the rules
dict. Fields with **unsupported** type annotations always raise — even if
unconstrained.

## When *not* to use SQLRules

Skip SQLRules when:

- You need **request/instance values** as WHERE predicates
  (`UserFilter(age=25)` → `age = 25`). That is a query/filter library, not
  this compiler.
- You have a few static expressions and will never share constraint metadata
  with a Pydantic model — write SQLAlchemy clauses directly.
- You need **portable regex** with core alone — `pattern` requires a dialect
  plugin or custom translator.
- You expect `dialect="postgresql"` to **load plugins** — it is a hint only;
  pass `plugins=[...]` explicitly.
- You want a general-purpose **query builder**, ORM, or SQL string generator.

SQLRules pays off when the Pydantic model *is* the shared source of truth for
constraint metadata across many fields or dialects.

## Public API

```python
sqlrules.compile(model, table, *, column_map=None, on_unsupported="raise", cache=True, emit_type_checks=False)
sqlrules.where(rules)           # prefer this to flatten expressions
sqlrules.flatten(rules)         # alias of where()
sqlrules.clear_model_cache()    # drop process-wide Phase-1 IR cache

compiler = sqlrules.Compiler(
    plugins=[...],           # optional SQLRulesPlugin instances
    on_conflict="raise",     # raise | replace | ignore
    dialect=None,            # hint only — does not load plugins
    on_unsupported="raise",
    cache=True,
    emit_type_checks=False,  # opt-in type_check IR (needs plugin translator)
)
```

## Non-goals

SQLRules is not an ORM, validator, query builder, SQL string generator,
migration tool, or database client. It only compiles supported Pydantic
constraints into SQLAlchemy expressions. See
[design philosophy](https://sqlrules.readthedocs.io/en/latest/guides/design-philosophy.html)
and [non-goals](https://sqlrules.readthedocs.io/en/latest/NON_GOALS.html).

## Documentation

Full site: **[sqlrules.readthedocs.io](https://sqlrules.readthedocs.io/en/latest/)**

| Topic | Link |
|---|---|
| Getting started | [Guide](https://sqlrules.readthedocs.io/en/latest/guides/getting-started.html) |
| How-to guides | [ORM binding](https://sqlrules.readthedocs.io/en/latest/guides/orm-column-map.html) · [Markers](https://sqlrules.readthedocs.io/en/latest/guides/markers.html) · [Examples](https://sqlrules.readthedocs.io/en/latest/guides/examples.html) |
| Upgrade | [0.x → 1.0](https://sqlrules.readthedocs.io/en/latest/guides/upgrade-0x.html) |
| Examples | [`examples/`](examples/) |
| Spec & constraints | [SPEC](https://sqlrules.readthedocs.io/en/latest/SPEC.html) · [CONSTRAINTS](https://sqlrules.readthedocs.io/en/latest/CONSTRAINTS.html) |
| Plugins | [Plugin system](https://sqlrules.readthedocs.io/en/latest/PLUGIN_SYSTEM.html) |
| API reference | [Reference hub](https://sqlrules.readthedocs.io/en/latest/reference/index.html) |
| FAQ | [FAQ](https://sqlrules.readthedocs.io/en/latest/guides/faq.html) |
| Support | [Support & compatibility](https://sqlrules.readthedocs.io/en/latest/project/support.html) |
| Roadmap | [Roadmap](https://sqlrules.readthedocs.io/en/latest/project/roadmap.html) |
| Changelog | [Changelog](https://sqlrules.readthedocs.io/en/latest/project/changelog.html) |

```bash
pip install -e ".[docs]"
make docs
```

## Repo map

| Path | Who cares |
|---|---|
| PyPI `sqlrules` / `sqlrules-*` | **Application users** — install these |
| [`examples/`](examples/) | Copy-paste runnable scripts |
| [`docs/`](docs/) | Spec, guides, architecture (also on Read the Docs) |
| [`packages/`](packages/) | **Contributors** — official dialect plugin sources |
| [`src/sqlrules/`](src/sqlrules/) | Core library source |
| [`benchmarks/`](benchmarks/) | Optional local compile benchmarks |

## Development (contributors)

```bash
make install
make check    # lint, types, tests, docs (matches most of CI)
make dist     # packaging smoke — required before release / to match full CI
```

See [CONTRIBUTING.md](CONTRIBUTING.md). Maintainers: [RELEASING.md](RELEASING.md).

## License

MIT
