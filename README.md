# SQLRules

[![CI](https://github.com/eddiethedean/sqlrules/actions/workflows/ci.yml/badge.svg)](https://github.com/eddiethedean/sqlrules/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/sqlrules.svg)](https://pypi.org/project/sqlrules/)
[![Documentation](https://readthedocs.org/projects/sqlrules/badge/?version=latest)](https://sqlrules.readthedocs.io/en/latest/)
[![License](https://img.shields.io/pypi/l/sqlrules.svg)](https://github.com/eddiethedean/sqlrules/blob/main/LICENSE)

**Compile constrained Pydantic models into SQLAlchemy WHERE-rule dictionaries.**

One package. One job. Deterministic output. Zero database dependency.

SQLRules solves: *"Our filter models already declare constraints—don't make us rewrite them as SQLAlchemy clauses."*

Not an ORM, validator, or query builder: **constraint metadata → expressions**, nothing else.

**In 30 seconds:**

```bash
pip install sqlrules
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
stmt = users.select().where(*sqlrules.where(rules))
```

> **`pattern` needs a plugin.** Core compiles comparisons, lengths, `Literal`, and `Enum`. Regex / JSON / arrays require a dialect package (see below).

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
| **Compile filters** | [Getting started](https://sqlrules.readthedocs.io/en/latest/guides/getting-started.html) |
| **Dialect plugins** | [Plugin system](https://sqlrules.readthedocs.io/en/latest/PLUGIN_SYSTEM.html) |
| **Evaluate fit** | [Design philosophy](https://sqlrules.readthedocs.io/en/latest/guides/design-philosophy.html) |
| **Contribute** | [Contributing](https://sqlrules.readthedocs.io/en/latest/project/contributing.html) |

---

## Example

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

Prefer `sqlrules.where(rules)` to flatten expressions for `.where(...)`.
`flatten` is an identical alias.

More: [`examples/basic_compile.py`](examples/basic_compile.py),
[`examples/select_usage.py`](examples/select_usage.py).

## Install

```bash
pip install sqlrules
# or: uv add sqlrules
```

**End users:** install from PyPI only. You do not need to clone this repo or
install from `packages/`.

Optional dialect plugins (same major line as core):

```bash
pip install sqlrules-postgresql   # ~ / ~*, JSONB, ARRAY, range
pip install sqlrules-sqlite       # REGEXP helper + JSON
pip install sqlrules-mysql        # REGEXP, JSON, full-text
pip install sqlrules-mssql        # JSON + LEN string ops
```

Extras are equivalent shortcuts (pull the matching plugin package):

```bash
pip install "sqlrules[postgresql]"
pip install "sqlrules[dialects]"   # all four
```

```python
from typing import Annotated, Any

from pydantic import BaseModel, Field
from sqlalchemy import Column, MetaData, String, Table
from sqlalchemy.dialects.postgresql import JSONB

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

Dialect markers (`JsonContains`, `ArrayContains`, `RangeContains`,
`FullTextMatch`, …) are re-exported from `sqlrules` (and live in
`sqlrules.markers`); they require a dialect plugin.

Unsupported constraints raise `UnsupportedConstraintError` by default.
Use `on_unsupported="warn"` or `"ignore"` for unknown **operators**
(unsupported **types** always raise, including unconstrained fields).

## When *not* to use SQLRules

If you have two static filters and will never share constraint metadata with
a Pydantic model, write the SQLAlchemy expressions directly. SQLRules pays
off when the model *is* the source of truth for many fields or dialects.

## Public API

```python
sqlrules.compile(model, table, *, column_map=None, on_unsupported="raise", cache=True)
sqlrules.where(rules)           # prefer this to flatten expressions
sqlrules.flatten(rules)         # alias of where()
sqlrules.clear_model_cache()    # drop process-wide Phase-1 IR cache

compiler = sqlrules.Compiler(
    plugins=[...],           # optional SQLRulesPlugin instances
    on_conflict="raise",     # raise | replace | ignore
    dialect=None,            # hint only — does not load plugins
    on_unsupported="raise",
    cache=True,
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
| Examples | [`examples/`](examples/) |
| Spec & constraints | [SPEC](https://sqlrules.readthedocs.io/en/latest/SPEC.html) · [CONSTRAINTS](https://sqlrules.readthedocs.io/en/latest/CONSTRAINTS.html) |
| Plugins | [Plugin system](https://sqlrules.readthedocs.io/en/latest/PLUGIN_SYSTEM.html) |
| API reference | [Reference hub](https://sqlrules.readthedocs.io/en/latest/reference/index.html) |
| FAQ | [FAQ](https://sqlrules.readthedocs.io/en/latest/guides/faq.html) |
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

## Development

```bash
make install
make test
make docs
```

See [CONTRIBUTING.md](CONTRIBUTING.md). Maintainers: [RELEASING.md](RELEASING.md).

## License

MIT
