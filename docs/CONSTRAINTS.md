# Supported Constraint Mapping

| Constraint | SQLAlchemy expression |
|---|---|
| `gt` | `column > value` |
| `ge` | `column >= value` |
| `lt` | `column < value` |
| `le` | `column <= value` |
| `min_length` | `func.length(column) >= value` |
| `max_length` | `func.length(column) <= value` |
| `multiple_of` | `column % value == 0` |
| `Literal[...]` | `column.in_(...)` |
| `Enum` | `column.in_(member values)` |
| `pattern` | IR in core; translators via plugins / custom registry |

Accepted input forms for the same semantics include `Field(...)`,
`annotated_types` primitives, `Interval`, `Len`, `conint`/`constr`, and
`StringConstraints` (length attributes; `pattern` becomes IR).

Constraints without a deterministic SQL equivalent are rejected by default.
See [TYPE_SUPPORT.md](TYPE_SUPPORT.md) and [ERRORS.md](ERRORS.md).

To translate `pattern`, use a dialect plugin or register a custom translator:

```python
from sqlrules import Compiler
from sqlrules_postgresql import PostgresPlugin

compiler = Compiler(plugins=[PostgresPlugin()], dialect="postgresql")
```

```python
from sqlrules.translators import default_registry

registry = default_registry()
registry.register_constraint(
    "pattern",
    lambda c, col, ctx: col.op("~")(c.value),
    on_conflict="replace",
)
compiler = sqlrules.Compiler(registry=registry)
```
