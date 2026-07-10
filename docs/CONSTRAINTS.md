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

Accepted input forms for the same semantics include `Field(...)`,
`annotated_types` primitives, `Interval`, `Len`, `conint`/`constr`, and
`StringConstraints` (length attributes only).

Constraints without a deterministic SQL equivalent are rejected by default.
See [TYPE_SUPPORT.md](TYPE_SUPPORT.md) and [ERRORS.md](ERRORS.md).
