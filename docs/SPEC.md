# Specification

## Primary API

```python
rules = sqlrules.compile(MyModel, table)
```

## Returns

```python
dict[str, list[ColumnElement[bool]]]
```

Ordering is deterministic and follows model field declaration order.
Within a field, expressions follow constraint extraction order.
Fields that produce no expressions are omitted from the dictionary.

## Supported constraints (v0.1)

- `gt`
- `ge`
- `lt`
- `le`
- `min_length`
- `max_length`
- `multiple_of`
- `Literal`
- `Enum`

## Unsupported constraints

Unsupported **constraint operators** raise `UnsupportedConstraintError` by
default.

Policies (`on_unsupported`):

| Mode | Behavior |
|---|---|
| `raise` | Raise immediately (default) |
| `warn` | Emit a `SQLRulesWarning` and skip |
| `ignore` | Silently skip |

`on_unsupported` applies only to unknown constraint operators. Unsupported
**types** (for example `UUID`, containers, `time`, `timedelta`) always raise.

## Column binding

Each constrained field is bound to a SQLAlchemy column via, in order:

1. `column_map` (keys may be the field name or a string alias)
2. `table.c`
3. ORM / attribute lookup, only when the attribute is a `ColumnElement` or
   exposes `__clause_element__()`

String `Field(alias=...)`, `validation_alias`, and `serialization_alias` are
tried before the Python field name. Non-column table attributes (for example
`Table.name` or `Table.is_selectable`) are never treated as columns.

Unconstrained fields are skipped and do not require a matching column.

## Compatibility

- Python 3.10+
- Pydantic v2
- SQLAlchemy 2.x
