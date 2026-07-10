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

## Supported constraints (v1.0)

- `gt`
- `ge`
- `lt`
- `le`
- `min_length`
- `max_length`
- `multiple_of`
- `Literal`
- `Enum`

`pattern` is extracted into IR as `PatternSpec` but has no portable core
translator. It raises by default; use `on_unsupported="warn"` / `"ignore"`,
register a custom translator, or install a dialect plugin. Treat untrusted
patterns as a CPU/ReDoS cost risk (see [SECURITY.md](SECURITY.md)).

Dialect markers (`JsonContains`, `ArrayContains`, `RangeContains`,
`FullTextMatch`, …) are extracted into IR and require a dialect plugin.

`max_digits` and `decimal_places` are rejected at extract time (no portable
SQL mapping in 1.0).

## Supported types (v1.0)

- `bool`, `int`, `float`, `Decimal`, `str`
- `date`, `datetime`, `time`
- `UUID` (Literal / Enum only)
- `Literal[...]`, `Enum`
- `list` / `dict` (allowed annotations; portable constraints raise;
  unconstrained containers are skipped like unconstrained scalars;
  dialect markers require a plugin)

**Whole-model rule:** every field annotation must be in this matrix, including
fields with no constraints. Unsupported types (for example `timedelta`) always
raise. Split filter models from DTOs that carry unsupported types.

## `where` / `flatten`

Both names are supported aliases of the same function.

## Unsupported constraints

Unsupported **constraint operators** raise `UnsupportedConstraintError` by
default.

Policies (`on_unsupported`):

| Mode | Behavior |
|---|---|
| `raise` | Raise immediately (default) |
| `warn` | Emit a `SQLRulesWarning`, record a diagnostic, and skip |
| `ignore` | Record a diagnostic and silently skip |

`on_unsupported` applies only to unknown constraint operators. Unsupported
**types** (for example containers and `timedelta`) always raise.

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

## Two-phase compilation

```python
compiler = sqlrules.Compiler()
model_ir = compiler.compile_model(MyModel)  # cached by default
rules = compiler.bind(model_ir, table)
```

Phase 1 caches immutable model IR. Phase 2 binds columns and translates.

## Plugins

```python
compiler = sqlrules.Compiler(
    plugins=[PostgresPlugin()],
    dialect="postgresql",
    on_conflict="raise",
)
```

Plugins must declare `api_version == PLUGIN_API_VERSION`. See
[PLUGIN_SYSTEM.md](PLUGIN_SYSTEM.md).

## Compatibility

- Python 3.10+
- Pydantic v2
- SQLAlchemy 2.x
