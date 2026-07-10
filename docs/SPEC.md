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

Unsupported constraints raise `UnsupportedConstraintError` by default.

Policies:

| Mode | Behavior |
|---|---|
| `raise` | Raise immediately (default) |
| `warn` | Emit a `SQLRulesWarning` and skip |
| `ignore` | Silently skip |

## Compatibility

- Python 3.10+
- Pydantic v2
- SQLAlchemy 2.x
