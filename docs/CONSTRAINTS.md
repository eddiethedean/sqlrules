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
| `pattern` | IR (`PatternSpec`); translators via plugins / custom registry |
| `type_check` | IR (`TypeSpec`) when `emit_type_checks=True`; translators via plugins |

## Dialect markers (`sqlrules.markers`)

| Marker | IR operator | Typical plugin translation |
|---|---|---|
| `JsonContains` | `json_contains` | JSONB / JSON containment |
| `JsonHasKey` | `json_has_key` | JSON key existence |
| `ArrayContains` | `array_contains` | PostgreSQL array containment |
| `ArrayOverlap` | `array_overlap` | PostgreSQL array overlap |
| `RangeContains` | `range_contains` | PostgreSQL range `@>` |
| `RangeOverlap` | `range_overlap` | PostgreSQL range `&&` |
| `FullTextMatch` | `fulltext_match` | MySQL `MATCH ... AGAINST` |

Accepted input forms for portable constraints include `Field(...)`,
`annotated_types` primitives, `Interval`, `Len`, `conint`/`constr`, and
`StringConstraints` (length attributes; `pattern` becomes `PatternSpec` IR).

Constraints without a deterministic SQL equivalent are rejected by default.
See [TYPE_SUPPORT.md](TYPE_SUPPORT.md) and [ERRORS.md](ERRORS.md).

To translate `pattern`, `type_check`, or markers, use a dialect plugin:

```python
from sqlrules import Compiler, JsonContains
from sqlrules_postgresql import PostgresPlugin

compiler = Compiler(
    plugins=[PostgresPlugin()],
    dialect="postgresql",
    emit_type_checks=True,
)
```

```python
from sqlrules.constraints import pattern_text
from sqlrules.translators import default_registry

registry = default_registry()
registry.register_constraint(
    "pattern",
    lambda c, col, ctx: col.op("~")(pattern_text(c.value)[0]),
    on_conflict="replace",
)
compiler = sqlrules.Compiler(registry=registry)
```
