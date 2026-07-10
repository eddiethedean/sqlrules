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
| `pattern` | IR only in 0.2 (no portable core translator) |

Accepted input forms for the same semantics include `Field(...)`,
`annotated_types` primitives, `Interval`, `Len`, `conint`/`constr`, and
`StringConstraints` (length attributes; `pattern` becomes IR).

Constraints without a deterministic SQL equivalent are rejected by default.
See [TYPE_SUPPORT.md](TYPE_SUPPORT.md) and [ERRORS.md](ERRORS.md).

To translate `pattern`, register a custom translator:

```python
from sqlrules.translators import default_registry

registry = default_registry()
registry.register("pattern", lambda c, col, ctx: col.op("~")(c.value))
compiler = sqlrules.Compiler(registry=registry)
```
